from datetime import datetime
from urllib.request import urlopen

from icalendar import Calendar


def to_local_date(value):
    if isinstance(value, datetime):
        return value.astimezone().date()

    return value


def fetch_calendar(url: str):
    try:
        with urlopen(url, timeout=15) as response:
            calendar = Calendar.from_ical(response.read())

        events = [
            {
                "date": to_local_date(event["DTSTART"].dt),
                "summary": str(event.get("SUMMARY", "")),
            }
            for event in calendar.walk("VEVENT")
            if event.get("DTSTART")
        ]
        events.sort(key=lambda item: item["date"])

        return {"status": "ok", "events": events}
    except Exception:
        return {
            "status": "error",
            "message": "Could not read the calendar. Please check ICAL_URL and your connection.",
        }
