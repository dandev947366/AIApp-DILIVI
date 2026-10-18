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
        Literal[
            "study_planning",
            "skill_analysis",
            "job_search",
            "general_chat",
            "tutor_agent",
            "assignment_sync",
        ]
    ] = Field(default_factory=list)


SUPERVISOR_PROMPT = """You are a smart routing agent for an AI assistant.
Your job is to read the user's question and decide which specialized
AI agent should handle it.

Available Agents:
1. "study_planning": Handles time management, schedules, deadlines, and 
   creating a plan for *when* to study (e.g., "make a schedule", "what's due this week?").
2. "skill_analysis": Handles questions about the user's technical skills,
   career goals, skill gaps, resume, or how to improve abilities.
3. "job_search": Handles questions about job opportunities, applications,
   interviews, or career advice.
4. "tutor_agent": Handles active learning, practicing concepts, taking quizzes, 
   understanding assignments, or tracking learning progress.
5. "assignment_sync": Handles queries specifically about checking, listing, or 
   syncing the student's Moodle assignments and homework.
6. "general_chat": Handles general knowledge, course information,
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
- Choose "assignment_sync" if the user asks to check, show, list, or update 
  their assignments (e.g., "check my assignments", "what homework do I have?").
- Choose "tutor_agent" if the user asks for help learning, studying, 
  or practicing a specific topic, OR if they ask for help understanding 
  or completing a specific assignment.
- If the message does not clearly ask for planning, skill analysis, 
  or tutoring, return {"tasks": ["general_chat"]}.
- When in doubt, choose "general_chat".

Return ONLY a valid JSON object with this exact shape:
{"tasks": ["agent_name"]}

Examples:
User: "When is my database exam?" -> {"tasks": ["study_planning"]}
User: "Make a schedule for my assignments" -> {"tasks": ["study_planning"]}
User: "Check my upcoming assignments" -> {"tasks": ["assignment_sync"]}
User: "What homework do I have?" -> {"tasks": ["assignment_sync"]}
User: "What skills do I need for a data science job?" -> {"tasks": ["skill_analysis"]}
User: "Help me study for my Deep Learning assignment" -> {"tasks": ["tutor_agent"]}
User: "I need help with Deep learning class" -> {"tasks": ["tutor_agent"]}
User: "I want to learn Python" -> {"tasks": ["tutor_agent"]}
User: "Quiz me on Machine Learning" -> {"tasks": ["tutor_agent"]}
User: "What courses am I taking this semester?" -> {"tasks": ["general_chat"]}
User: "Update my degree to Business IT" -> {"tasks": ["general_chat"]}
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
    rf"\b(?:update|change|set|correct|edit|fix|adjust)\s+(?:my\s+|the\s+)?{_PROFILE_FIELDS}\b",
    rf"\bi\s+(?:want|need|would like)\s+to\s+(?:update|change|set|correct)\s+(?:my\s+|the\s+)?{_PROFILE_FIELDS}\b",
    rf"\bmy\s+{_PROFILE_FIELDS}\s+(?:is|are|should be|will be|equals?)\b",
    rf"\bmy\s+new\s+{_PROFILE_FIELDS}\s+(?:is|are)\b",
    rf"\bforget\s+(?:about\s+)?my\s+{_PROFILE_FIELDS}\b",
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

    if _is_profile_update(question):
        print(f"[SUPERVISOR] profile-update shortcut -> general_chat: {question!r}")
        return {"tasks": ["general_chat"]}

    # ─────────────────────────────────────────────────────────
    # Deterministic shortcut: obvious assignment queries route
    # to assignment_sync without asking the LLM.
    # ─────────────────────────────────────────────────────────
    sync_keywords = ["assignment", "homework", "task", "deadline"]
    if any(kw in question.lower() for kw in sync_keywords):
        print(
            f"[SUPERVISOR] Assignment query shortcut -> assignment_sync: {question!r}"
        )
        return {"tasks": ["assignment_sync"]}

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
