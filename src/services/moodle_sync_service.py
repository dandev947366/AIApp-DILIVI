"""
Syncs Moodle iCal data into the local relational database.
Idempotent: running twice updates records without duplicates.
"""

import requests
from icalendar import Calendar
from datetime import datetime
from sqlalchemy.orm import Session
from src.models.calendar_models import StudentModel, CourseModel, CalendarEventModel


def fetch_ical(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DAIA-CalendarSync/1.0)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.content


def parse_ical_events(ical_data: bytes) -> list[dict]:
    cal = Calendar.from_ical(ical_data)
    events = []
    for component in cal.walk("VEVENT"):
        uid = str(component.get("UID", "")).strip()
        summary = str(component.get("SUMMARY", "")).strip()
        if not uid or not summary:
            continue

        def to_datetime(ical_prop):
            if not ical_prop:
                return None
            val = ical_prop.dt
            if isinstance(val, datetime):
                return val
            return datetime.combine(val, datetime.min.time())

        events.append(
            {
                "uid": uid,
                "summary": summary,
                "description": str(component.get("DESCRIPTION", "")),
                "location": str(component.get("LOCATION", "")),
                "dtstart": to_datetime(component.get("DTSTART")),
                "dtend": to_datetime(component.get("DTEND")),
                "class_visibility": str(component.get("CLASS", "PUBLIC")),
                "last_modified": to_datetime(component.get("LAST-MODIFIED")),
                "dtstamp": to_datetime(component.get("DTSTAMP")),
                "categories": component.get("CATEGORIES"),
            }
        )
    return events


def sync_calendar_to_db(
    url: str, moodle_user_id: int, student_name: str, db: Session
) -> dict:
    raw_data = fetch_ical(url)
    parsed_events = parse_ical_events(raw_data)

    student = db.query(StudentModel).filter_by(moodle_user_id=moodle_user_id).first()
    if not student:
        student = StudentModel(
            moodle_user_id=moodle_user_id,
            full_name=student_name,
            ical_url=url,
            last_synced_at=datetime.utcnow(),
        )
        db.add(student)
        db.flush()
    else:
        student.ical_url = url
        student.last_synced_at = datetime.utcnow()

    stats = {
        "events_processed": len(parsed_events),
        "events_added": 0,
        "events_updated": 0,
        "courses_added": 0,
        "skipped": 0,
    }

    # ✅ Keywords that identify homework/deadlines
    assignment_keywords = [
        "due",
        "submission",
        "quiz",
        "exam",
        "closes",
        "deadline",
        "homework",
        "project",
        "assignment",
    ]

    for ev in parsed_events:
        if not ev["dtstart"]:
            stats["skipped"] += 1
            continue

        # ✅ Determine if it's an assignment based on summary/description
        search_text = f"{ev['summary']} {ev['description']}".lower()
        is_assignment = any(kw in search_text for kw in assignment_keywords)

        course_code, course_name = "Unknown", "Unknown Course"
        if ev["categories"]:
            cats = ev["categories"]
            cat_str = str(cats.cats[0] if hasattr(cats, "cats") else cats)
            if ":" in cat_str:
                course_name, course_code = [x.strip() for x in cat_str.split(":", 1)]
            else:
                course_code = cat_str
                course_name = cat_str

        course = db.query(CourseModel).filter_by(course_code=course_code).first()
        if not course:
            course = CourseModel(course_code=course_code, course_name=course_name)
            db.add(course)
            db.flush()
            stats["courses_added"] += 1

        existing = db.query(CalendarEventModel).filter_by(uid=ev["uid"]).first()
        if existing:
            existing.summary = ev["summary"]
            existing.description = ev["description"]
            existing.dtstart = ev["dtstart"]
            existing.dtend = ev["dtend"]
            existing.last_modified = ev["last_modified"]
            existing.is_assignment = is_assignment  # ✅ Update flag
            stats["events_updated"] += 1
        else:
            new_event = CalendarEventModel(
                student_id=student.student_id,
                course_id=course.course_id,
                uid=ev["uid"],
                summary=ev["summary"],
                description=ev["description"],
                location=ev["location"],
                dtstart=ev["dtstart"],
                dtend=ev["dtend"],
                class_visibility=ev["class_visibility"],
                last_modified=ev["last_modified"],
                dtstamp=ev["dtstamp"],
                is_assignment=is_assignment,  # ✅ Save flag
            )
            db.add(new_event)
            stats["events_added"] += 1

    db.commit()
    return stats
