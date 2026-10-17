"""Hashed remember-me tokens. Raw tokens never touch the DB."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from src.database import SessionLocal
from src.models.calendar_models import StudentModel

TOKEN_TTL_DAYS = 30


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(student_id: int) -> str:
    """Generate a fresh token, store its hash, return the raw token."""
    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)

    with SessionLocal() as db:
        student = db.query(StudentModel).filter_by(student_id=student_id).first()
        if student is None:
            raise ValueError(f"student {student_id} not found")
        student.session_token_hash = _hash(raw)
        student.session_token_expires = expires
        db.commit()

    return raw


def verify_token(raw: str) -> dict | None:
    """Return {student_db_id, moodle_user_id, student_name} or None."""
    if not raw:
        return None

    token_hash = _hash(raw)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        student = (
            db.query(StudentModel).filter_by(session_token_hash=token_hash).first()
        )
        if student is None:
            return None
        if student.session_token_expires and student.session_token_expires < now:
            return None

        # Best-effort name (column may or may not exist)
        name = (
            getattr(student, "full_name", None) or getattr(student, "name", None) or ""
        )
        return {
            "student_db_id": student.student_id,
            "moodle_user_id": student.moodle_user_id,
            "student_name": str(name).strip(),
        }


def revoke_token(student_id: int) -> None:
    with SessionLocal() as db:
        student = db.query(StudentModel).filter_by(student_id=student_id).first()
        if student:
            student.session_token_hash = None
            student.session_token_expires = None
            db.commit()
