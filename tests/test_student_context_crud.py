import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from src.database import Base
from src.models.student_context import StudentContextDB
from src.schemas.student_context import StudentContext
from src.services.student_context_service import (
    create_student_context,
    get_student_context,
    update_student_context,
    delete_student_context
)

@pytest.fixture
def db_engine():
    return create_engine("sqlite:///:memory:", poolclass=StaticPool)

@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    return SessionLocal()