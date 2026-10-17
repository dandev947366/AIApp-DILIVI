# scripts/migrate_add_ical_url.py
import sqlite3
from pathlib import Path

DB = Path("/app/data/student_context.db")

with sqlite3.connect(DB) as c:
    cols = {r[1] for r in c.execute("PRAGMA table_info(students)")}
    if "ical_url" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN ical_url TEXT")
        print("✅ added students.ical_url")
    if "last_synced_at" not in cols:
        c.execute("ALTER TABLE students ADD COLUMN last_synced_at TEXT")
        print("✅ added students.last_synced_at")
    c.commit()
