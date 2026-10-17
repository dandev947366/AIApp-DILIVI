"""Deterministic tests for preference extraction and persistence."""

import json
from unittest.mock import patch

from src.memory.preferences import (
    detect_forgets,
    extract_student_preferences,
)
from src.database import SessionLocal
from src.tools.profile import get_student_profile, update_student_profile


def _mock_chat(payload: dict):
    def _fake(self, *args, **kwargs):
        return {"message": {"content": json.dumps(payload)}}

    return patch("src.memory.preferences.Client.chat", _fake)


# ---- extraction ----------------------------------------------


def test_extracts_all_four_fields():
    payload = {
        "preferred_study_time": "evening",
        "study_hours_per_week": 12,
        "career_goals": {"short_term": "machine learning engineer"},
        "interests": ["AI agents", "deep learning", "quantitative finance"],
    }
    with _mock_chat(payload):
        r = extract_student_preferences(
            "I prefer studying in the evening. I can study 12 hours per week. "
            "My career goal is to become a machine learning engineer, "
            "and I am interested in AI agents, deep learning, and "
            "quantitative finance."
        )
    assert r["preferred_study_time"] == "evening"
    assert r["study_hours_per_week"] == 12
    assert r["career_goals"] == {"short_term": "machine learning engineer"}
    assert r["interests"] == ["AI agents", "deep learning", "quantitative finance"]


def test_invalid_study_time_dropped():
    with _mock_chat({"preferred_study_time": "whenever"}):
        r = extract_student_preferences("I study whenever.")
    assert "preferred_study_time" not in r


def test_study_hours_out_of_range_rejected():
    with _mock_chat({"study_hours_per_week": 200}):
        r = extract_student_preferences("I study 200 hours a week.")
    assert r == {}


def test_greeting_short_circuits():
    with _mock_chat({"preferred_study_time": "evening"}):
        r = extract_student_preferences("Hi")
    assert r == {}


def test_llm_failure_returns_empty():
    with patch(
        "src.memory.preferences.Client.chat",
        side_effect=RuntimeError("connection refused"),
    ):
        r = extract_student_preferences("I prefer mornings.")
    assert r == {}


def test_degree_program_still_extracted():
    with _mock_chat({"degree_program": "Business IT"}):
        r = extract_student_preferences("I'm in Business IT.")
    assert r == {"degree_program": "Business IT"}


# ---- forget --------------------------------------------------


def test_detect_forgets_interests():
    assert detect_forgets("Please forget my interests.") == ["interests"]


def test_detect_forgets_multiple():
    f = detect_forgets("Forget my study hours and forget my preferred study time.")
    assert set(f) == {"study_hours_per_week", "preferred_study_time"}


def test_detect_forgets_none():
    assert detect_forgets("I prefer mornings.") == []


# ---- persistence ---------------------------------------------


def test_partial_update_preserves_other_fields(test_student_id):
    """Setting one field must not clear the others."""
    update_student_profile(
        test_student_id,
        preferred_study_time="morning",
        study_hours_per_week=8,
        interests=["AI"],
    )
    update_student_profile(test_student_id, study_hours_per_week=12)
    p = get_student_profile(test_student_id)
    assert p["study_hours_per_week"] == 12
    assert p["preferred_study_time"] == "morning"
    assert p["interests"] == ["AI"]


def test_interests_merge_and_dedupe(test_student_id):
    update_student_profile(test_student_id, replace=True, interests=["AI", "ML"])
    update_student_profile(test_student_id, interests=["ai", "deep learning"])
    p = get_student_profile(test_student_id)
    assert set(p["interests"]) == {"AI", "ML", "ai", "deep learning"}


def test_correction_overwrites_scalar(test_student_id):
    update_student_profile(test_student_id, preferred_study_time="morning")
    update_student_profile(test_student_id, preferred_study_time="evening")
    assert get_student_profile(test_student_id)["preferred_study_time"] == "evening"


def test_forget_with_replace(test_student_id):
    update_student_profile(test_student_id, interests=["AI", "ML"])
    update_student_profile(test_student_id, replace=True, interests=[])
    assert get_student_profile(test_student_id)["interests"] == []


def test_forget_scalar_with_none(test_student_id):
    update_student_profile(test_student_id, preferred_study_time="evening")
    update_student_profile(test_student_id, replace=True, preferred_study_time=None)
    assert get_student_profile(test_student_id)["preferred_study_time"] is None


def test_new_session_reloads(test_student_id):
    update_student_profile(test_student_id, study_hours_per_week=15)
    with SessionLocal() as _db:  # force a new session
        pass
    assert get_student_profile(test_student_id)["study_hours_per_week"] == 15
