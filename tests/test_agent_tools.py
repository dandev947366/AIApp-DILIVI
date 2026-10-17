import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.calendar_models import (
    Base,
    StudentModel,
    CalendarEventModel,
    CourseModel,
)
from src.models.student_models import StudentProfileModel, StudentSkillModel


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


class TestAssignmentTools:
    def test_upcoming_sorted(self, test_db, monkeypatch):
        from src.tools.assignments import get_upcoming_assignments

        student = StudentModel(moodle_user_id=1, full_name="T")
        test_db.add(student)
        test_db.flush()

        for i, d in enumerate([5, 2]):
            test_db.add(
                CalendarEventModel(
                    student_id=student.student_id,
                    uid=f"e{i}",
                    summary=f"A{i}",
                    dtstart=datetime.utcnow() + timedelta(days=d),
                )
            )
        test_db.commit()

        import src.tools.assignments as mod

        monkeypatch.setattr(mod, "SessionLocal", lambda: test_db)

        result = get_upcoming_assignments(student.student_id, days=14)
        assert result[0]["title"] == "A1"  # 2 days (sooner)


class TestProfileTools:
    def test_merge_interests(self, test_db, monkeypatch):
        from src.tools.profile import update_student_profile, get_student_profile

        student = StudentModel(moodle_user_id=1, full_name="T")
        test_db.add(student)
        test_db.commit()

        import src.tools.profile as mod

        monkeypatch.setattr(mod, "SessionLocal", lambda: test_db)

        update_student_profile(student.student_id, interests=["Python"])
        update_student_profile(student.student_id, interests=["AI"])

        profile = get_student_profile(student.student_id)
        assert "Python" in profile["interests"]
        assert "AI" in profile["interests"]

    def test_career_goals_merge(self, test_db, monkeypatch):
        from src.tools.profile import update_student_profile, get_student_profile

        student = StudentModel(moodle_user_id=1, full_name="T")
        test_db.add(student)
        test_db.commit()

        import src.tools.profile as mod

        monkeypatch.setattr(mod, "SessionLocal", lambda: test_db)

        update_student_profile(
            student.student_id, career_goals={"long_term": "ML Engineer"}
        )
        update_student_profile(
            student.student_id, career_goals={"short_term": "Internship"}
        )

        profile = get_student_profile(student.student_id)
        assert profile["career_goals"]["long_term"] == "ML Engineer"
        assert profile["career_goals"]["short_term"] == "Internship"
