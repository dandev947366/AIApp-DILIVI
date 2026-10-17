"""Profile tools with intelligent merge behavior."""

from src.database import SessionLocal
from src.models.student_models import StudentProfileModel


def get_student_profile(student_id: int) -> dict:
    with SessionLocal() as db:
        profile = db.query(StudentProfileModel).filter_by(student_id=student_id).first()

        if not profile:
            return {
                "degree_program": None,
                "current_semester": None,
                "career_goals": {},
                "interests": [],
                "study_hours_per_week": None,
                "preferred_study_time": None,
            }

        return {
            "degree_program": profile.degree_program,
            "current_semester": profile.current_semester,
            "career_goals": profile.career_goals or {},
            "interests": profile.interests or [],
            "study_hours_per_week": profile.study_hours_per_week,
            "preferred_study_time": profile.preferred_study_time,
        }


def update_student_profile(student_id: int, replace: bool = False, **kwargs) -> dict:
    """
    Update profile with intelligent merge:
    - interests: MERGED (union) by default; REPLACED if replace=True
    - career_goals: MERGED (keys updated) by default; REPLACED if replace=True
    - scalars: REPLACED
    """
    with SessionLocal() as db:
        profile = db.query(StudentProfileModel).filter_by(student_id=student_id).first()

        if not profile:
            profile = StudentProfileModel(student_id=student_id)
            db.add(profile)

        for key, value in kwargs.items():
            if not hasattr(profile, key):
                continue

            if key == "interests":
                if replace:
                    profile.interests = list(value) if isinstance(value, list) else []
                else:
                    existing = set(profile.interests or [])
                    new = set(value) if isinstance(value, list) else set()
                    profile.interests = sorted(existing | new)

            elif key == "career_goals":
                if replace:
                    profile.career_goals = (
                        dict(value) if isinstance(value, dict) else {}
                    )
                else:
                    existing = dict(profile.career_goals or {})
                    if isinstance(value, dict):
                        existing.update(value)
                    profile.career_goals = existing

            else:
                setattr(profile, key, value)

        db.commit()
        db.refresh(profile)

    return get_student_profile(student_id)
