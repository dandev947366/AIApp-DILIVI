from typing import Any
from src.models.student_context import StudentContextDB
from src.schemas.student_context import StudentContext

# CRUD operations for the StudentContextDB model

def create_student_context(
    db: Any, 
        student_id: str,
        student_context: StudentContext) -> StudentContextDB:
    """
    Create a new student context entry in the database.

    Args:
        db (Session): The SQLAlchemy database session.
        student_context (StudentContext): The student context data to be stored.

    Returns:
        StudentContextDB: The created student context database model instance.
    """
    student_id = student_id.strip()
    if not student_id:
        raise ValueError("Student ID cannot be empty or whitespace.")
    
    existing = db.get(StudentContextDB, student_id)
    if existing is not None :
        raise ValueError(f"Student context for student_id '{student_id}' already exists.")

    context_data = student_context.model_dump(mode="json")  # Convert Pydantic model to dictionary
    context_data["student_info"]["student_id"] = student_id  # Ensure student_id is included in the context data
    db_student_context = StudentContextDB(
        student_id=student_id,
        payload=context_data
    )
    db.add(db_student_context)
    db.commit()
    db.refresh(db_student_context)
    return db_student_context

def get_student_context(db: Any, student_id: str) -> StudentContextDB | None:
    """
    Retrieve a student context entry from the database by student ID.

    Args:
        db (Session): The SQLAlchemy database session.
        student_id (str): The unique identifier for the student.

    Returns:
        StudentContextDB | None: The retrieved student context database model instance, or None if not found.
    """
    return db.get(StudentContextDB, student_id)

def update_student_context(
    db: Any, 
        student_id: str, 
        updated_context: StudentContext) -> StudentContextDB:
    """
    Update an existing student context entry in the database.

    Args:
        db (Session): The SQLAlchemy database session.
        student_id (str): The unique identifier for the student.
        updated_context (StudentContext): The updated student context data.

    Returns:
        StudentContextDB: The updated student context database model instance.
    """
    db_student_context = db.get(StudentContextDB, student_id)
    if db_student_context is None:
        raise ValueError(f"Student context for student_id '{student_id}' does not exist.")

    updated_data = updated_context.model_dump(model="json")  # Convert Pydantic model to dictionary
    updated_data["student_info"]["student_id"] = student_id  # Ensure student_id is included in the context data
    db_student_context.payload = updated_data
    db.commit()
    db.refresh(db_student_context)
    return db_student_context

def delete_student_context(db: Any, student_id: str) -> None:
    """
    Delete a student context entry from the database by student ID.

    Args:
        db (Session): The SQLAlchemy database session.
        student_id (str): The unique identifier for the student.

    Returns:
        None
    """
    db_student_context = db.get(StudentContextDB, student_id)
    if db_student_context is None:
        raise ValueError(f"Student context for student_id '{student_id}' does not exist.")

    db.delete(db_student_context)
    db.commit()



    
    