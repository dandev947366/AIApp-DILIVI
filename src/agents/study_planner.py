"""Study Planner: Creates prioritized plans from assignment data."""

import os
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from src.config import MODEL_ID, OLLAMA_TIMEOUT
from src.agents.state import AgentState

# ✅ Bulletproof Docker network fix
if "OLLAMA_HOST" in os.environ:
    del os.environ["OLLAMA_HOST"]
if "OLLAMA_BASE_URL" in os.environ:
    del os.environ["OLLAMA_BASE_URL"]

OLLAMA_HOST_DOCKER = "http://ollama:11434"

llm = ChatOllama(
    model=MODEL_ID, base_url=OLLAMA_HOST_DOCKER, timeout=OLLAMA_TIMEOUT, temperature=0.3
)

SYSTEM_PROMPT = """You are a Study Planner agent for a university student.
Use ONLY the provided data. Be specific with dates and hours.
If a preferred study time is stored, prioritize scheduling during that period when practical.
Do not force every session into that period if deadlines make it unrealistic.
Keep response under 300 words."""


def study_planner_node(state: AgentState) -> dict:
    context = state.get("student_context", {})
    upcoming = context.get("upcoming_assignments", [])
    overdue = context.get("overdue_assignments", [])
    profile = context.get("profile", {})

    upcoming_text = (
        "\n".join(
            f"- {a['title']} ({a['course']}) | Due: {a['deadline'][:10]} | {a['days_until']}d left"
            for a in upcoming
        )
        or "None."
    )
    overdue_text = (
        "\n".join(f"- ⚠️ {a['title']} | {a['days_overdue']}d OVERDUE" for a in overdue)
        or "None."
    )

    user_prompt = f"""Study hours/week: {profile.get('study_hours_per_week', 'Unknown')}
Preferred time: {profile.get('preferred_study_time', 'No preference')}
OVERDUE:\n{overdue_text}\n\nUPCOMING:\n{upcoming_text}\n\nToday: {datetime.now().strftime('%A, %B %d, %Y')}\n\nCreate a prioritized study plan."""

    response = llm.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )

    return {
        "study_plan_result": response.content,
        "messages": [AIMessage(content=f"[Study Planner]\n{response.content}")],
    }
