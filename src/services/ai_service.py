from datetime import datetime

from src.config import MODEL_ID
from src.models.model_client import model_client
from src.services.calendar_service import upcoming_assignments

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
