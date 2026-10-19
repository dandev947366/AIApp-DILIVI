from datetime import datetime
from typing import Optional

from src.config import MODEL_ID
from src.models.model_client import (
    OllamaModelClient,
    ModelClientError,
    OllamaConnectionError,
    ModelNotFoundError,
    model_client,
)
from src.schemas.responses import UserRequest, AIResponse
from src.services.calendar_service import upcoming_assignments


class AIService:
    """
    Application service layer responsible for validating user input,
    orchestrating model client requests, and catching exceptions gracefully.
    """

    def __init__(self, model_client: Optional[OllamaModelClient] = None):
        # Allow injecting custom/mock model_client for simple testing
        self.model_client = model_client

    def _get_client(self) -> OllamaModelClient:
        """Returns active model client, initializing default client if none provided."""
        if self.model_client is None:
            self.model_client = OllamaModelClient()
        return self.model_client

    def process_message(self, user_message: str) -> AIResponse:
        """
        Processes a raw user message string and returns a structured AIResponse.
        Catches technical failures and converts them to friendly user-facing messages.
        """
        # 1. Validate empty input
        if not user_message or not user_message.strip():
            return AIResponse(
                content="Please enter a message before sending.",
                success=False,
                error_message="User message was empty.",
            )

        try:
            # 2. Schema validation
            request = UserRequest(message=user_message.strip())

            # 3. Call model client
            client = self._get_client()
            response_text = client.generate(request.message)

            return AIResponse(
                content=response_text,
                success=True,
            )

        except OllamaConnectionError as err:
            return AIResponse(
                content=(
                    "[Error] Could not connect to Ollama.\n\n"
                    "Please verify that Ollama is installed and running locally on your machine."
                ),
                success=False,
                error_message=str(err),
            )

        except ModelNotFoundError as err:
            return AIResponse(
                content=(
                    f"[Error] The configured AI model is unavailable in Ollama.\n\n"
                    f"Please verify your MODEL_NAME setting or run 'ollama run <model_name>'."
                ),
                success=False,
                error_message=str(err),
            )

        except ModelClientError as err:
            return AIResponse(
                content="[Error] An unexpected communication error occurred with the AI model.",
                success=False,
                error_message=str(err),
            )

        except Exception as err:
            return AIResponse(
                content="[Error] An unexpected application error occurred.",
                success=False,
                error_message=str(err),
            )


def generate_response(user_message: str, service: Optional[AIService] = None) -> str:
    """
    Main reusable service entry point used by the UI layer.
    
    Accepts user input message, passes it to the AI service, and returns
    the generated text response (or a friendly error message).
    """
    active_service = service or AIService()
    response = active_service.process_message(user_message)
    return response.content


MAX_DESCRIPTION_LENGTH = 500

SYSTEM_MESSAGE = (
    "You are a study assistant for university students. "
    "Answer the user's study or course-related question in a few sentences. "
    "For questions about the student's assignments or deadlines, use only the supplied assignments. "
    "Do not invent assignments or deadlines that are missing from the supplied assignments. "
    "If you are unsure about an official rule or deadline, say that it should be "
    "checked in Moodle or with the course teacher."
)


def date_label(title: str):
    if title.endswith("opens"):
        return "Opens"

    return "Deadline"


def build_messages(question: str, evidence, history=None):
    history = history or []

    selected_history = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-4:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]

    evidence_text = "\n\n".join(
        f"[{number}] {item.title}\n"
        f"Course: {item.course}\n"
        f"{date_label(item.title)}: {item.deadline:%A %d.%m.%Y %H:%M}\n"
        f"Description: {item.description[:MAX_DESCRIPTION_LENGTH]}"
        for number, item in enumerate(evidence, start=1)
    )

    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        *selected_history,
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"Today: {datetime.now():%A %d.%m.%Y}\n\n"
                f"Upcoming assignments:\n{evidence_text or 'No upcoming assignments.'}"
            ),
        },
    ]


def ai_service(question: str, history=None) -> str:
    cleaned_question = (question or "").strip()

    if not cleaned_question:
        return "Please enter a question."

    evidence = upcoming_assignments().get("assignments", [])

    try:
        response = model_client.chat(
            model=MODEL_ID,
            messages=build_messages(cleaned_question, evidence, history),
            stream=False,
        )
        return response.message.content
    except Exception:
        return "The AI service could not complete the request. Please try again."
