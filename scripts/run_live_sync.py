"""Sync real Moodle calendar into local database."""

import os
import sys

from src.database import SessionLocal, init_db
from src.services.moodle_sync_service import sync_calendar_to_db

init_db()

ICAL_URL = (os.getenv("ICAL_URL") or "").strip()
MOODLE_USER_ID = int(os.getenv("MOODLE_USER_ID", "66944"))
STUDENT_NAME = os.getenv("STUDENT_NAME", "Unknown")

if not ICAL_URL or ICAL_URL == "YOUR_MOODLE_ICAL_URL_HERE":
    print(
        "❌ ICAL_URL is not set in .env.\n"
        "   Expected: ICAL_URL=https://<moodle>/calendar/export_execute.php?...",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"🔄 Starting live Moodle sync for user {MOODLE_USER_ID} ({STUDENT_NAME})...")
print(f"   Host: {ICAL_URL.split('/')[2]}")
with SessionLocal() as db:
    stats = sync_calendar_to_db(ICAL_URL, MOODLE_USER_ID, STUDENT_NAME, db)
    print(
        f"✅ Added: {stats['events_added']}, "
        f"Updated: {stats['events_updated']}, "
        f"Courses: {stats['courses_added']}"
    )
