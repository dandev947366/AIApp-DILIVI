from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from src.database import Base


class TranscriptImportModel(Base):
    __tablename__ = "transcript_imports"

    transcript_id = Column(Integer, primary_key=True, autoincrement=True)

    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False, default="pdf")
    file_hash = Column(String(64), nullable=False)

    # processing | completed | failed
    status = Column(String(20), nullable=False, default="processing")

    # Validated extraction, without retaining the original PDF text.
    extracted_data = Column(JSON, nullable=True)

    error_message = Column(Text, nullable=True)
    model_id = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index(
            "idx_transcript_student_created",
            "student_id",
            "created_at",
        ),
    )


class StudentCourseModel(Base):
    __tablename__ = "student_courses"

    student_course_id = Column(Integer, primary_key=True, autoincrement=True)

    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to the shared course catalogue.
    course_id = Column(
        Integer,
        ForeignKey("courses.course_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Snapshot of the transcript's course details.
    course_code = Column(String(50), nullable=True)
    course_name = Column(String(255), nullable=False)

    transcript_id = Column(
        Integer,
        ForeignKey("transcript_imports.transcript_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    grade = Column(String(30), nullable=True)
    credits = Column(Float, nullable=True)
    completion_status = Column(String(30), nullable=True)
    completed_at = Column(DateTime, nullable=True)

    source = Column(String(30), nullable=False, default="transcript")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        # Multiple NULL course codes are permitted by SQLite.
        UniqueConstraint(
            "student_id",
            "course_code",
            name="uq_student_course_code",
        ),
        Index(
            "idx_student_courses_student_name",
            "student_id",
            "course_name",
        ),
    )
