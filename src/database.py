import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config import DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    os.makedirs(
        os.path.dirname(DATABASE_URL.replace("sqlite:///", "")) or ".", exist_ok=True
    )

engine = create_engine(DATABASE_URL, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call on startup."""
    from src.models.calendar_models import StudentModel, CourseModel, CalendarEventModel
    from src.models.student_models import (
        StudentProfileModel,
        StudentSkillModel,
        ConversationMessageModel,
    )
    from src.models.transcript_models import (
        TranscriptImportModel,
        StudentCourseModel,
    )

    Base.metadata.create_all(bind=engine)

    def _ensure_auth_columns():
        with engine.connect() as conn:
            cols = {c["name"] for c in inspect(engine).get_columns("students")}
            if "session_token_hash" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE students ADD COLUMN session_token_hash VARCHAR(128)"
                    )
                )
            if "session_token_expires" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE students ADD COLUMN session_token_expires DATETIME"
                    )
                )
            conn.commit()

    _ensure_auth_columns()
