"""Assignment tools. Read directly from SQLite."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from src.database import SessionLocal
from src.models.calendar_models import CalendarEventModel, CourseModel


def get_upcoming_assignments(student_id: int, days: int = 14) -> list[dict]:
    with SessionLocal() as db:
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days)
        events = (
            db.query(CalendarEventModel)
            .options(joinedload(CalendarEventModel.course))
            .filter(
                CalendarEventModel.student_id == student_id,
                CalendarEventModel.is_assignment == True,  # ✅ ONLY FETCH HOMEWORK
                CalendarEventModel.dtstart >= now,
                CalendarEventModel.dtstart <= cutoff,
            )
            .order_by(CalendarEventModel.dtstart.asc())
            .all()
        )
        return [
            {
                "title": ev.summary,
                "course": ev.course.course_name if ev.course else "Unknown",
                "course_code": ev.course.course_code if ev.course else "",
                "deadline": ev.dtstart.isoformat(),
                "days_until": (ev.dtstart - now).days,
                "description": (ev.description or "")[:500],
            }
            for ev in events
        ]


def get_overdue_assignments(student_id: int) -> list[dict]:
    with SessionLocal() as db:
        now = datetime.utcnow()
        events = (
            db.query(CalendarEventModel)
            .options(joinedload(CalendarEventModel.course))
            .filter(
                CalendarEventModel.student_id == student_id,
                CalendarEventModel.is_assignment == True,  # ✅ ONLY FETCH HOMEWORK
                CalendarEventModel.dtstart < now,
                CalendarEventModel.dtstart >= now - timedelta(days=30),
            )
            .order_by(CalendarEventModel.dtstart.desc())
            .all()
        )
        return [
            {
                "title": ev.summary,
                "course": ev.course.course_name if ev.course else "Unknown",
                "deadline": ev.dtstart.isoformat(),
                "days_overdue": (now - ev.dtstart).days,
            }
            for ev in events
        ]


def get_assignments_by_course(student_id: int, course_code: str) -> list[dict]:
    with SessionLocal() as db:
        events = (
            db.query(CalendarEventModel)
            .join(CourseModel)
            .filter(
                CalendarEventModel.student_id == student_id,
                CourseModel.course_code == course_code,
            )
            .order_by(CalendarEventModel.dtstart.asc())
            .all()
        )
        return [
            {
                "title": ev.summary,
                "deadline": ev.dtstart.isoformat(),
                "description": (ev.description or "")[:300],
            }
            for ev in events
        ]
