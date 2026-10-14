
from src.config import MODEL_ID
from src.models.model_client import model_client
from src.capabilities.tools import (
    UPCOMING_ASSIGNMENTS_TOOL,
    get_upcoming_assignments,
)


def answer_with_tools(question: str) -> str:
    """Answer a student question using Ollama tool calling."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a university study assistant. "
                "Use the available tool when the student asks about "
                "upcoming assignments or deadlines. "
                "Never invent assignments or deadlines. "
                "If calendar data is unavailable, explain that clearly. "
                "For general questions, give a short, direct answer. "
                "Do not include reasoning, planning, or analysis in your response. "
                "Start immediately with the answer."
            ),

        },
        {"role": "user", "content": question},
    ]

    response = model_client.chat(
        model=MODEL_ID,
        messages=messages,
        tools=[UPCOMING_ASSIGNMENTS_TOOL],
        think=False,
        options={"temperature": 0, "num_predict": 512},
        stream=False,
    )

    for tool_call in response.message.tool_calls or []:
        if tool_call.function.name != "get_upcoming_assignments":
            continue

        arguments = tool_call.function.arguments or {}
        result = get_upcoming_assignments(
            days=arguments.get("days", 7)
        )

        if result["status"] == "error":
            return (
                "I couldn't retrieve your assignments because "
                "the calendar is not configured or is unavailable. "
                "Please check the calendar connection."
            )

        assignments = result["assignments"]

        if not assignments:
            return "You have no upcoming assignments in the requested period."

        lines = ["Your upcoming assignments:"]

        for assignment in assignments:
            lines.append(
                f"- {assignment['title']} "
                f"({assignment['course']}) — "
                f"Deadline: {assignment['deadline']}"
            )

        return "\n".join(lines)

    if not response.message.tool_calls:
        content = response.message.content or ""

        if "</think>" in content:
            content = content.split("</think>", 1)[1].strip()

        return content or "No final answer generated."

    return "The requested tool is not supported."

    
