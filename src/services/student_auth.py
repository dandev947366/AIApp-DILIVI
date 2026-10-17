from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.calendar_models import StudentModel


def authenticate_student(
    db: Session,
    student_id: str,
    student_name: str,
):
    """Look up an existing student by ID and stored name.

    This is a prototype identity check, not secure authentication.
    """
    student_id = student_id.strip()
    student_name = student_name.strip()

    if not student_id or not student_name:
        return None

    # Assumes StudentModel.student_id is the Moodle student ID
    # and StudentModel.name stores the student's name.
    if not student_id.isdigit():
        return None

    student = (
        db.query(StudentModel)
        .filter(StudentModel.student_id == int(student_id))
        .first()
    )

    if student is None:
        return None

    stored_name = (student.name or "").strip()

    if stored_name.casefold() != student_name.casefold():
        return None

    return student
