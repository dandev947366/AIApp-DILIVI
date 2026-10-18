"""
Relational ORM models for Moodle calendar data.
Tables: students, courses, calendar_events.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base


class StudentModel(Base):
    __tablename__ = "students"
    student_id = Column(Integer, primary_key=True, autoincrement=True)
    moodle_user_id = Column(Integer, nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    ical_url = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_token_hash = Column(String(128), nullable=True)
    session_token_expires = Column(DateTime, nullable=True)
    events = relationship(
        "CalendarEventModel", back_populates="student", cascade="all, delete-orphan"
    )


class CourseModel(Base):
    __tablename__ = "courses"
    course_id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(50), nullable=False, unique=True, index=True)
    course_name = Column(String(255), nullable=False)
    moodle_course_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    events = relationship("CalendarEventModel", back_populates="course")


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    course_id = Column(
        Integer, ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True
    )
    uid = Column(String(255), nullable=False, unique=True, index=True)
    summary = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    dtstart = Column(DateTime, nullable=False, index=True)
    dtend = Column(DateTime, nullable=True)
    class_visibility = Column(String(20), default="PUBLIC")
    last_modified = Column(DateTime, nullable=True)
    dtstamp = Column(DateTime, nullable=True)

    # ✅ NEW: Flag to identify homework/deadlines vs lectures/maintenance
    is_assignment = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = relationship("StudentModel", back_populates="events")
    course = relationship("CourseModel", back_populates="events")
    __table_args__ = (Index("idx_student_date", "student_id", "dtstart"),)
