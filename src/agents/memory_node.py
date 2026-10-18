"""Memory Node: Loads ALL student context once at graph start."""

from langchain_core.messages import AIMessage
from src.tools.assignments import get_upcoming_assignments, get_overdue_assignments
from src.tools.profile import get_student_profile
from src.tools.skills import get_student_skills
from src.memory.conversation_memory import get_recent_messages
from src.agents.state import AgentState
from src.database import SessionLocal
from src.models.calendar_models import CourseModel


def memory_node(state: AgentState) -> dict:
    student_id = state["student_id"]
    profile = get_student_profile(student_id)
    skills = get_student_skills(student_id)
    upcoming = get_upcoming_assignments(student_id, days=14)
    overdue = get_overdue_assignments(student_id)
    recent_messages = get_recent_messages(student_id, limit=5)

    # ✅ Fetch courses from the database
    courses = []
    try:
        with SessionLocal() as db:
            db_courses = db.query(CourseModel).all()
            courses = [
                {"course_code": c.course_code, "course_name": c.course_name}
                for c in db_courses
            ]
    except Exception as e:
        print(f"Warning: Could not fetch courses: {e}")

    context = {
        "profile": profile,
        "skills": skills,
        "courses": courses,  # ✅ Added courses to context
        "upcoming_assignments": upcoming,
        "overdue_assignments": overdue,
        "recent_conversation": recent_messages,
    }

    # Build summary
    summary_parts = []
    if profile.get("degree_program") or profile.get("career_goals"):
        summary_parts.append(
            f"Degree: {profile.get('degree_program', 'N/A')} | "
            f"Goals: {profile.get('career_goals', {})} | "
            f"Hours/week: {profile.get('study_hours_per_week', 'N/A')} | "
            f"Preferred time: {profile.get('preferred_study_time', 'N/A')}"
        )
    if skills:
        summary_parts.append(
            "Skills: "
            + ", ".join(
                f"{s['skill_name']} ({s['proficiency'] or '?'}/5)" for s in skills[:8]
            )
        )
    if courses:
        summary_parts.append(f"Courses: {len(courses)} total recorded.")
    if upcoming:
        summary_parts.append(
            "Upcoming: "
            + "; ".join(f"{a['title']} ({a['days_until']}d)" for a in upcoming[:5])
        )
    if overdue:
        summary_parts.append(
            "OVERDUE: "
            + "; ".join(f"⚠️ {a['title']} ({a['days_overdue']}d)" for a in overdue[:3])
        )
    if recent_messages:
        summary_parts.append(
            "Recent: "
            + " → ".join(
                f"{m['role']}: {m['content'][:50]}" for m in recent_messages[-3:]
            )
        )

    return {
        "student_context": {
            **context,
            "summary": "\n".join(summary_parts),
        },
    }
