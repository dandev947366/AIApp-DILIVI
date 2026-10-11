from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config import DATABASE_URL

# Create the SQLAlchemy engine
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create reusable session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Provide a database session to FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
