from datetime import datetime, time, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from icalendar import Calendar

from src.config import ICAL_URL
from src.database import SessionLocal
from src.models.calendar_models import CalendarEventModel, StudentModel
from src.schemas.assignment import Assignment
from src.services.moodle_sync_service import sync_calendar_to_db

SITE_EVENTS = "Site events"


def to_local_datetime(value):
    if isinstance(value, datetime):
        return value.astimezone()

    return datetime.combine(value, time(23, 59)).astimezone()


def event_course(event):
    categories = event.get("CATEGORIES")

    if categories is None:
        return ""

    return str(categories.cats[0])


def fetch_calendar(url: str):
    try:
        with urlopen(url, timeout=15) as response:
            calendar = Calendar.from_ical(response.read())

        assignments = [
            Assignment(
                title=str(event.get("SUMMARY", "")),
                course=event_course(event),
                deadline=to_local_datetime(event["DTSTART"].dt),
                description=str(event.get("DESCRIPTION", "")),
            )
            for event in calendar.walk("VEVENT")
            if event.get("DTSTART") and event_course(event) != SITE_EVENTS
        ]
        assignments.sort(key=lambda item: item.deadline)

        return {"status": "ok", "assignments": assignments}
    except Exception:
        return {
            "status": "error",
            "message": "Could not read the calendar",
        }


def filter_upcoming(assignments, days=None):
    first_day = datetime.now().date()

    assignments = [
        item for item in assignments
        if item.deadline.date() >= first_day
    ]

    if days is not None:
        last_day = first_day + timedelta(days=days)

        assignments = [
            item for item in assignments
            if item.deadline.date() <= last_day
        ]

    return assignments


def upcoming_assignments(days=None):
    if not ICAL_URL:
        return {
            "status": "error",
            "message": "Error, ical link is not set",
        }

    result = fetch_calendar(ICAL_URL)

    if result["status"] == "error":
        return result

    return {"status": "ok", "assignments": filter_upcoming(result["assignments"], days)}


def connect_student(ical_url: str, full_name: str):
    try:
        moodle_user_id = int(parse_qs(urlparse(ical_url).query)["userid"][0])

        with SessionLocal() as db:
            stats = sync_calendar_to_db(ical_url, moodle_user_id, full_name, db)
            student = db.query(StudentModel).filter_by(moodle_user_id=moodle_user_id).first()

            return {
                "status": "ok",
                "student_id": student.student_id,
                "events": stats["events_processed"],
            }
    except Exception:
        return {
            "status": "error",
            "message": "Could not connect the calendar. Check the link and try again.",
        }


def sync_student(student_id: int):
    try:
        with SessionLocal() as db:
            student = db.get(StudentModel, student_id)
            stats = sync_calendar_to_db(
                student.ical_url,
                student.moodle_user_id,
                student.full_name,
                db,
            )

            return {"status": "ok", "events": stats["events_processed"]}
    except Exception:
        return {
            "status": "error",
            "message": "Could not update the calendar from Moodle.",
        }


def student_assignments(student_id: int, days=None):
    try:
        with SessionLocal() as db:
            events = (
                db.query(CalendarEventModel)
                .filter_by(student_id=student_id)
                .order_by(CalendarEventModel.dtstart)
                .all()
            )

            assignments = [
                Assignment(
                    title=event.summary,
                    course=event.course.course_code if event.course else "",
                    deadline=event.dtstart.replace(tzinfo=timezone.utc).astimezone(),
                    description=event.description or "",
                )
                for event in events
                if not event.course or event.course.course_code != SITE_EVENTS
            ]
    except Exception:
        return {
            "status": "error",
            "message": "Could not read the assignments from the database.",
        }

    return {"status": "ok", "assignments": filter_upcoming(assignments, days)}
