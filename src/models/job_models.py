from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from src.database import Base


class JobModel(Base):
    __tablename__ = "jobs"

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    country = Column(
        String(100), nullable=True, index=True
    )  # Used for "Jobs by country"
    url = Column(String(500), nullable=False, unique=True, index=True)
    industry = Column(String(255), nullable=True)  # The "Stack" from Jobicy
    salary = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)


class JobCollectionRunModel(Base):
    """Tracks the health and history of job data collection."""

    __tablename__ = "job_collection_runs"

    run_id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False, default="success")
    jobs_added = Column(Integer, default=0)
    run_at = Column(DateTime, default=datetime.utcnow, nullable=False)
