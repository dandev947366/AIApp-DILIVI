"""Main entry point. Connects questions to LangGraph with memory extraction."""

import traceback
from typing import Iterator

from langchain_core.messages import HumanMessage

from src.agents.graph import agent_graph
from src.agents.state import AgentState
from src.models.calendar_models import StudentModel
from src.database import SessionLocal
from src.memory.conversation_memory import save_message
from src.memory.preferences import (
    FORGET_VALUES,
    detect_forgets,
    extract_student_preferences,
)
from src.tools.profile import update_student_profile

# ─────────────────────────────────────────────────────────────
# Friendly labels for LangGraph nodes (shown in the chatbox).
# Unknown nodes fall back to "⚙️ Running <pretty node name>…"
# ─────────────────────────────────────────────────────────────
NODE_LABELS: dict[str, str] = {
    # context / routing
    "memory": "🧠 Loading your profile and history…",
    "router": "🧭 Deciding what to do…",
    "task_router": "🧭 Understanding your request…",
    "task_extractor": "🧭 Understanding your request…",
    # domain nodes
    "job_search": "🔌 Searching jobs on Jobicy…",
    "skills": "🧩 Comparing with your skills…",
    "skill_analysis": "🧩 Analysing your skills…",
    "study_plan": "📚 Building your study plan…",
    "moodle": "📅 Checking your Moodle calendar…",
    "general_chat": "💬 Thinking about your question…",
    # synthesis
    "assistant": "✍️ Writing the answer…",
    "synthesizer": "✍️ Writing the answer…",
    "responder": "✍️ Writing the answer…",
}


def _label_for(node_name: str) -> str:
    if node_name in NODE_LABELS:
        return NODE_LABELS[node_name]
    pretty = (node_name or "node").replace("_", " ").strip()
    return f"⚙️ Running {pretty or node_name}…"


def get_student_db_id(moodle_user_id: int) -> int | None:
    with SessionLocal() as db:
        student = (
            db.query(StudentModel).filter_by(moodle_user_id=moodle_user_id).first()
        )
        return student.student_id if student else None


def _persist_preferences(student_db_id: int, question: str) -> None:
    """Extract + persist. Never raises — chat must keep working."""
    # 1. Handle explicit "forget" requests with replace=True so collections
    #    actually reset instead of union-merging.
    for field in detect_forgets(question):
        try:
            update_student_profile(
                student_db_id,
                replace=True,
                **{field: FORGET_VALUES[field]},
            )
            print(f"[PREFERENCES] forgot: {field}")
        except Exception as exc:
            print(
                f"[PREFERENCES] forget({field}) failed: " f"{type(exc).__name__}: {exc}"
            )

    # 2. Extract and merge new preferences.
    try:
        incoming = extract_student_preferences(question)
        if not incoming:
            return
        update_student_profile(student_db_id, **incoming)
        print(f"[PREFERENCES] saved: {sorted(incoming.keys())}")
    except Exception as exc:
        print(f"[PREFERENCES] persist failed: {type(exc).__name__}: {exc}")


def _build_initial_state(question: str, student_db_id: int) -> AgentState:
    return {
        "messages": [HumanMessage(content=question)],
        "student_id": student_db_id,
        "student_context": {},
        "tasks": [],
        "study_plan_result": "",
        "skill_analysis_result": "",
        "general_chat_result": "",
        "final_response": "",
    }


# ─────────────────────────────────────────────────────────────
# Non-streaming (kept for backward compatibility).
# ─────────────────────────────────────────────────────────────
def agent_service(question: str, moodle_user_id: int) -> str:
    student_db_id = get_student_db_id(moodle_user_id)
    if student_db_id is None:
        return f"Student {moodle_user_id} not found. Sync calendar first."

    conversation_id = save_message(student_db_id, "user", question)

    # ─────────────────────────────────────────────────────────
    # Extract + persist BEFORE the graph runs, so memory_node
    # loads the updated profile and the chat reply reflects
    # what was just saved.
    # ─────────────────────────────────────────────────────────
    _persist_preferences(student_db_id, question)

    initial_state = _build_initial_state(question, student_db_id)

    try:
        final_state = agent_graph.invoke(initial_state)
        response = final_state.get("final_response", "I couldn't generate a response.")
    except Exception as exc:
        print(f"[CHAT] graph failed: {type(exc).__name__}: {exc}")
        response = "I ran into an issue answering that. Please try again."

    save_message(student_db_id, "assistant", response, conversation_id)
    return response


# ─────────────────────────────────────────────────────────────
# Streaming version.
#
# Yields (text, is_final) tuples:
#   (status_label, False)  – intermediate progress for the chat bubble
#   (final_response, True) – the actual answer, exactly once
#
# The final answer is only emitted AFTER it has been saved to
# conversation memory, so callers can safely stop iterating when
# they receive the True tuple.
# ─────────────────────────────────────────────────────────────
def agent_service_stream(
    question: str,
    moodle_user_id: int,
) -> Iterator[tuple[str, bool]]:
    """Stream progress + final answer for a chat question."""

    student_db_id = get_student_db_id(moodle_user_id)
    if student_db_id is None:
        yield (f"Student {moodle_user_id} not found. Sync calendar first.", True)
        return

    conversation_id = save_message(student_db_id, "user", question)

    # Preference extraction is itself an LLM call — tell the user
    # something is happening before it runs.
    yield ("🧠 Extracting preferences…", False)
    _persist_preferences(student_db_id, question)

    initial_state = _build_initial_state(question, student_db_id)

    final_response = ""

    try:
        # stream_mode="updates" yields {node_name: partial_state} per node.
        for chunk in agent_graph.stream(initial_state, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue
            for node_name, node_output in chunk.items():
                yield (_label_for(node_name), False)

                # Capture final_response whichever node produces it.
                if isinstance(node_output, dict):
                    candidate = node_output.get("final_response")
                    if candidate:
                        final_response = candidate

    except Exception as exc:
        print(f"[CHAT] graph stream failed: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        yield (
            f"I ran into an issue answering that. " f"(`{type(exc).__name__}: {exc}`)",
            True,
        )
        return

    if not final_response:
        final_response = "I couldn't generate a response."

    save_message(student_db_id, "assistant", final_response, conversation_id)
    yield (final_response, True)
