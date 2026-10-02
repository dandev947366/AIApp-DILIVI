from src.config import MODEL_ID
from src.models.model_client import model_client

SYSTEM_MESSAGE = (
    "You are a study assistant for university students. "
    "Answer the user's study or course-related question in a few sentences. "
    "If you are unsure about an official rule or deadline, say that it should be "
    "checked in Moodle or with the course teacher."
)


def build_messages(question: str, history=None):
    history = history or []

    selected_history = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-4:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]

    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        *selected_history,
        {"role": "user", "content": question},
    ]


def ai_service(question: str, history=None) -> str:
    cleaned_question = (question or "").strip()

    if not cleaned_question:
        return "Please enter a question."

    try:
        response = model_client.chat(
            model=MODEL_ID,
            messages=build_messages(cleaned_question, history),
            stream=False,
        )
        return response.message.content
    except Exception:
        return "The AI service could not complete the request. Please try again."
