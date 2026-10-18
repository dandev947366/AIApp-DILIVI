"""
Models for student profile, skills, and conversation history.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base


class StudentProfileModel(Base):
    __tablename__ = "student_profiles"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    degree_program = Column(String(255), nullable=True)
    current_semester = Column(Integer, nullable=True)
    career_goals = Column(JSON, nullable=True, default=dict)
    interests = Column(JSON, nullable=True, default=list)
    study_hours_per_week = Column(Float, nullable=True)
    preferred_study_time = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("StudentModel", backref="profile")


class StudentSkillModel(Base):
    __tablename__ = "student_skills"

    skill_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )

    skill_name = Column(String(100), nullable=False)
    proficiency = Column(Integer, nullable=True)  # 1-5
    evidence = Column(Text, nullable=True)
    source = Column(String(50), default="self_reported")

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("StudentModel", backref="skills")


class ConversationMessageModel(Base):
    __tablename__ = "conversation_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    conversation_id = Column(String(100), nullable=False)

    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentModel", backref="messages")
