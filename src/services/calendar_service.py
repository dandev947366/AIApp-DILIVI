from datetime import datetime, time, timedelta
from urllib.request import urlopen

from icalendar import Calendar

from src.config import ICAL_URL
from src.schemas.assignment import Assignment

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


def upcoming_assignments(days=None):
    if not ICAL_URL:
        return {
            "status": "error",
            "message": "Error, ical link is not set",
        }

    result = fetch_calendar(ICAL_URL)

    if result["status"] == "error":
        return result

    first_day = datetime.now().date()

    assignments = [
        item for item in result["assignments"]
        if item.deadline.date() >= first_day
    ]

    if days is not None:
        last_day = first_day + timedelta(days=days)

        assignments = [
            item for item in assignments
            if item.deadline.date() <= last_day
        ]

    return {"status": "ok", "assignments": assignments}
