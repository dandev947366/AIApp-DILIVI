"""One-time migration: Add preferred_study_time column."""

import sqlite3
import os

db_file = os.getenv("DATABASE_URL", "sqlite:///./data/student_context.db").replace(
    "sqlite:///", ""
)
print(f"Migrating: {db_file}")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(student_profiles)")
columns = [col[1] for col in cursor.fetchall()]

if "preferred_study_time" not in columns:
    cursor.execute(
        "ALTER TABLE student_profiles ADD COLUMN preferred_study_time VARCHAR(50)"
    )
    conn.commit()
    print("✅ Added column.")
else:
    print("ℹ️  Column already exists.")

conn.close()
