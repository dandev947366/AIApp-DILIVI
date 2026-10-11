from datetime import datetime, timezone
from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base

class StudentContextDB(Base):
    """
    SQLAlchemy model representing the student context information.
    """

    __tablename__ = "student_context"
    # The primary key for the student context table is the student_id, which uniquely identifies each student.
    student_id: Mapped[str] = mapped_column(String, primary_key=True, default="default")
    # Stores the validated context data as JSON
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    