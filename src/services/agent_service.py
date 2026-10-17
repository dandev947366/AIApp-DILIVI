"""Main entry point. Connects questions to LangGraph with memory extraction."""

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

    initial_state: AgentState = {
        "messages": [HumanMessage(content=question)],
        "student_id": student_db_id,
        "student_context": {},
        "tasks": [],
        "study_plan_result": "",
        "skill_analysis_result": "",
        "general_chat_result": "",
        "final_response": "",
    }

    try:
        final_state = agent_graph.invoke(initial_state)
        response = final_state.get("final_response", "I couldn't generate a response.")
    except Exception as exc:
        print(f"[CHAT] graph failed: {type(exc).__name__}: {exc}")
        response = "I ran into an issue answering that. Please try again."

    save_message(student_db_id, "assistant", response, conversation_id)
    return response
