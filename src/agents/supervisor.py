import os
import re
from typing import Literal

from ollama import Client
from pydantic import BaseModel, Field, ValidationError

from src.agents.state import AgentState

# ------------------------------------------------------------
# Routing schema
# ------------------------------------------------------------


class RoutingDecision(BaseModel):
    tasks: list[
        Literal["study_planning", "skill_analysis", "job_search", "general_chat"]
    ] = Field(default_factory=list)


SUPERVISOR_PROMPT = """You are a smart routing agent for an AI assistant.
Your job is to read the user's question and decide which specialized
AI agent should handle it.

Available Agents:
1. "study_planning": Handles deadlines, schedules, assignments,
   homework, exams, quizzes, time management, study plans, labs, and projects.
2. "skill_analysis": Handles questions about the user's technical skills,
   career goals, skill gaps, resume, or how to improve abilities.
3. "job_search": Handles questions about job opportunities, applications,
   interviews, or career advice.
4. "general_chat": Handles general knowledge, course information,
   transcripts, greetings, profile updates, or anything else.

Rules:
- Greetings ("hi", "hello", "hey", "good morning", "thanks"),
  small talk, or one-word openers -> {"tasks": ["general_chat"]}.
- Profile update requests -> {"tasks": ["general_chat"]}.
  This includes any message that changes, sets, or updates:
  degree program, interests, career goals, study hours per week,
  preferred study time, or semester. These are NOT study planning.
- Only choose "study_planning" when the user explicitly asks for
  a plan, schedule, time management, or to check deadlines, exams,
  or assignments.
- Only choose "skill_analysis" when the user explicitly asks about
  their skills, strengths, weaknesses, gaps, resume, or career readiness.
- If the message does not clearly ask for planning or skill analysis,
  return {"tasks": ["general_chat"]}.
- When in doubt, choose "general_chat".

Return ONLY a valid JSON object with this exact shape:
{"tasks": ["agent_name"]}

Examples:
User: "When is my database exam?" -> {"tasks": ["study_planning"]}
User: "Do I have any homework upcoming?" -> {"tasks": ["study_planning"]}
User: "Plan my study week" -> {"tasks": ["study_planning"]}
User: "What skills do I need for a data science job?" -> {"tasks": ["skill_analysis"]}
User: "What courses am I taking this semester?" -> {"tasks": ["general_chat"]}
User: "Update my degree to Business IT" -> {"tasks": ["general_chat"]}
User: "Change my preferred study time to evening" -> {"tasks": ["general_chat"]}
User: "My new study hours are 15" -> {"tasks": ["general_chat"]}
User: "Update my degree based on my courses" -> {"tasks": ["general_chat"]}
User: "Set my interests to AI and deep learning" -> {"tasks": ["general_chat"]}
User: "Hi" -> {"tasks": ["general_chat"]}
"""


# ------------------------------------------------------------
# Deterministic profile-update pre-check
# ------------------------------------------------------------


_PROFILE_FIELDS = (
    r"(?:degree|degree program|program|major|"
    r"interests?|career goals?|goals?|"
    r"study hours?(?: per week)?|weekly study hours?|"
    r"preferred study time|study time|semester)"
)

_PROFILE_UPDATE_PATTERNS = [
    # "update/change/set/correct/edit my <field> ..."
    rf"\b(?:update|change|set|correct|edit|fix|adjust)\s+(?:my\s+|the\s+)?{_PROFILE_FIELDS}\b",
    # "I want to update/change my <field>"
    rf"\bi\s+(?:want|need|would like)\s+to\s+(?:update|change|set|correct)\s+(?:my\s+|the\s+)?{_PROFILE_FIELDS}\b",
    # "my <field> is/are/should be <value>"
    rf"\bmy\s+{_PROFILE_FIELDS}\s+(?:is|are|should be|will be|equals?)\b",
    # "my new <field> is <value>"
    rf"\bmy\s+new\s+{_PROFILE_FIELDS}\s+(?:is|are)\b",
    # "forget my <field>"
    rf"\bforget\s+(?:about\s+)?my\s+{_PROFILE_FIELDS}\b",
    # "make my <field> <value>"
    rf"\bmake\s+my\s+{_PROFILE_FIELDS}\s+\S+",
]

_PROFILE_UPDATE_RE = re.compile(
    "|".join(_PROFILE_UPDATE_PATTERNS),
    re.IGNORECASE,
)


def _is_profile_update(question: str) -> bool:
    return bool(_PROFILE_UPDATE_RE.search(question or ""))


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def _strip_json_fence(raw: str) -> str:
    value = (raw or "").strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, count=1)
    if value.endswith("```"):
        value = value[:-3].strip()
    return value


def _fallback_to_general_chat(reason: str) -> dict:
    print(f"⚠️ Supervisor routing fallback to general_chat: {reason}")
    return {"tasks": ["general_chat"]}


# ------------------------------------------------------------
# Supervisor node
# ------------------------------------------------------------


def supervisor_node(state: AgentState) -> dict:
    messages = state.get("messages", [])

    user_messages = [m for m in messages if getattr(m, "type", None) == "human"]
    question = (
        user_messages[-1].content
        if user_messages
        else (messages[-1].content if messages else "")
    )
    question = (question or "").strip()

    if not question:
        return _fallback_to_general_chat("empty question")

    # ─────────────────────────────────────────────────────────
    # Deterministic shortcut: obvious profile updates route to
    # general_chat without asking the 3B model. This stops
    # "update my degree based on my courses" from being parsed
    # as study planning.
    # ─────────────────────────────────────────────────────────
    if _is_profile_update(question):
        print(f"[SUPERVISOR] profile-update shortcut -> general_chat: {question!r}")
        return {"tasks": ["general_chat"]}

    if "OLLAMA_HOST" in os.environ:
        del os.environ["OLLAMA_HOST"]
    if "OLLAMA_BASE_URL" in os.environ:
        del os.environ["OLLAMA_BASE_URL"]

    host = "http://ollama:11434"
    model = os.getenv("MODEL_ID", "llama3.2:3b")
    client = Client(host=host)

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SUPERVISOR_PROMPT},
                {"role": "user", "content": question},
            ],
            format=RoutingDecision.model_json_schema(),
            options={"temperature": 0},
        )

        raw_output = response["message"]["content"]
        cleaned = _strip_json_fence(raw_output)

        try:
            decision = RoutingDecision.model_validate_json(cleaned)
        except ValidationError as exc:
            return _fallback_to_general_chat(f"schema mismatch: {exc}")

        specific = [t for t in decision.tasks if t != "general_chat"]
        tasks = specific or ["general_chat"]

    except Exception as exc:
        return _fallback_to_general_chat(f"LLM call failed: {exc}")

    return {"tasks": tasks}
