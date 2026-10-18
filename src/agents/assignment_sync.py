import traceback
from src.agents.state import AgentState
from src.database import SessionLocal
from src.models.calendar_models import StudentModel
from src.services.moodle_sync_service import sync_calendar_to_db
from src.tools.assignments import get_upcoming_assignments, get_overdue_assignments
from langchain_core.messages import AIMessage


def assignment_sync_node(state: AgentState) -> dict:
    """Checks, syncs, and updates Moodle assignments in the context."""
    student_id = state.get("student_id")
    if not student_id:
        return {
            "messages": [AIMessage(content="[Assignment Sync] No student ID found.")]
        }

    print(f"[ASSIGNMENT SYNC] Checking Moodle data for student {student_id}...")

    # 1. Trigger the sync (this will update the DB)
    try:
        with SessionLocal() as db:
            student = db.query(StudentModel).filter_by(student_id=student_id).first()
            if student and student.ical_url and student.moodle_user_id:
                sync_calendar_to_db(
                    student.ical_url,
                    student.moodle_user_id,
                    student.full_name,
                    db,
                )
                print("[ASSIGNMENT SYNC] Moodle sync successful.")
            else:
                print("[ASSIGNMENT SYNC] Student has no iCal URL saved. Skipping sync.")
    except Exception as e:
        print(f"[ASSIGNMENT SYNC] Auto-sync failed: {e}")
        traceback.print_exc()

    # 2. Fetch the fresh data
    upcoming = get_upcoming_assignments(student_id, days=45)
    overdue = get_overdue_assignments(student_id)

    # 3. Update the student_context
    context = state.get("student_context", {})
    context["upcoming_assignments"] = upcoming
    context["overdue_assignments"] = overdue

    return {
        "student_context": context,
        "messages": [AIMessage(content="[Assignment Sync] Moodle data updated.")],
    }
