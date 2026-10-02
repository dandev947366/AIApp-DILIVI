import gradio as gr

from src.config import MODEL_ID
from src.services.ai_service import ai_service


def content_to_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )

    return ""


def history_for_service(history):
    converted = []

    for message in history:
        role = message.get("role")
        text = content_to_text(message.get("content"))

        if role in {"user", "assistant"} and text:
            converted.append({"role": role, "content": text})

    return converted


def chat_reply(message, history):
    return ai_service(message, history_for_service(history))


demo = gr.ChatInterface(
    fn=chat_reply,
    title="AI Study Path and Career Assistant",
    description=(
        f"Running with local model: {MODEL_ID}. "
        "Answers may be incorrect; check deadlines in Moodle."
    ),
)
