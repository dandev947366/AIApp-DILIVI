"""Skill tools. Read/write student skills from SQLite."""

from src.database import SessionLocal
from src.models.student_models import StudentSkillModel


def get_student_skills(student_id: int) -> list[dict]:
    with SessionLocal() as db:
        skills = (
            db.query(StudentSkillModel)
            .filter_by(student_id=student_id)
            .order_by(StudentSkillModel.proficiency.desc().nullslast())
            .all()
        )

        return [
            {
                "skill_name": s.skill_name,
                "proficiency": s.proficiency,
                "evidence": s.evidence,
                "source": s.source,
            }
            for s in skills
        ]


def add_or_update_skill(
    student_id: int,
    skill_name: str,
    proficiency: int = None,
    evidence: str = None,
    source: str = "self_reported",
) -> dict:
    with SessionLocal() as db:
        normalized = skill_name.lower().strip()
        skill = (
            db.query(StudentSkillModel)
            .filter_by(student_id=student_id, skill_name=normalized)
            .first()
        )

        if skill:
            if proficiency is not None:
                skill.proficiency = proficiency
            if evidence:
                skill.evidence = evidence
            skill.source = source
        else:
            skill = StudentSkillModel(
                student_id=student_id,
                skill_name=normalized,
                proficiency=proficiency,
                evidence=evidence,
                source=source,
            )
            db.add(skill)

        db.commit()
        db.refresh(skill)

        return {
            "skill_name": skill.skill_name,
            "proficiency": skill.proficiency,
            "evidence": skill.evidence,
            "source": skill.source,
        }
