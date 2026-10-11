from src.database import Base, engine
from src.models.student_context import StudentContextDB

def test_create_student_context_table():
    # Create the tables in the database
    Base.metadata.create_all(bind=engine)

    assert "student_context" in Base.metadata.tables, "student_context table should be created in the database"

    print("Databse tables created:", list(Base.metadata.tables.keys()))


   