"""Persistent student preference extraction.

Extraction is side-effect free. Persistence goes through
update_student_profile() so there is one write path.
"""

import os
import re

from ollama import Client
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ============================================================
# SCHEMA
# ============================================================


class ProfileUpdates(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preferred_study_time: str | None = (
        None  # post-validated against the study-time enum
    )
    study_hours_per_week: int | None = Field(default=None, ge=0, le=168)
    career_goals: dict[str, str] | None = None
    interests: list[str] | None = None
    degree_program: str | None = None
    current_semester: int | None = Field(default=None, ge=1, le=20)


_VALID_STUDY_TIMES = {"morning", "afternoon", "evening", "night"}


# ============================================================
# PROMPT
# ============================================================


EXTRACTION_SYSTEM_PROMPT = """You extract durable student preferences from one message.

Return a JSON object. Only include keys the student explicitly mentioned.
Omitted keys MUST be absent, not null.

Allowed keys:
- "preferred_study_time": "morning" | "afternoon" | "evening" | "night"
- "study_hours_per_week": integer from 0 to 168
- "career_goals": object like {"short_term": "...", "long_term": "..."}
- "interests": list of short interest labels (1-4 words each)
- "degree_program": string
- "current_semester": integer from 1 to 20

Rules:
1. Extract only durable facts the student states about themselves.
2. Never extract from hypotheticals ("if I studied...") or the assistant's suggestions.
3. If the student corrects a previous value, extract the new one.
4. Deduplicate interests; keep each short.
5. If nothing durable is stated, return {}.

Examples:
"Hi" -> {}
"What is 2+2?" -> {}
"I prefer studying in the evening." -> {"preferred_study_time": "evening"}
"I can study about 12 hours per week." -> {"study_hours_per_week": 12}
"My goal is to become a machine learning engineer." -> {"career_goals": {"short_term": "machine learning engineer"}}
"I'm interested in AI agents and deep learning." -> {"interests": ["AI agents", "deep learning"]}
"Actually make that 15 hours per week." -> {"study_hours_per_week": 15}
"""


# ============================================================
# HELPERS
# ============================================================


_GREETING_ONLY = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "bye",
    "goodbye",
    "yes",
    "no",
    "cool",
    "nice",
}


def _should_extract(message: str) -> bool:
    msg = (message or "").strip().lower()
    if not msg:
        return False
    # Only extract if the user talks about themselves
    triggers = ["i ", "my ", "me ", "prefer", "goal", "study", "degree", "hour"]
    if not any(t in msg for t in triggers):
        return False
    return msg not in _GREETING_ONLY


_FORGET_PATTERNS = {
    "preferred_study_time": [
        r"\bforget (?:about |)my (?:preferred |)study time\b",
        r"\bforget when i (?:like to |)study\b",
    ],
    "study_hours_per_week": [
        r"\bforget (?:about |)my study hours\b",
        r"\bforget how many hours i study\b",
    ],
    "career_goals": [
        r"\bforget (?:about |)my (?:career |)goals?\b",
    ],
    "interests": [
        r"\bforget (?:about |)my interests\b",
    ],
    "degree_program": [
        r"\bforget (?:about |)my degree program\b",
    ],
    "current_semester": [
        r"\bforget (?:about |)my (?:current |)semester\b",
    ],
}

# Values that clear each field when passed with replace=True.
FORGET_VALUES = {
    "preferred_study_time": None,
    "study_hours_per_week": None,
    "career_goals": {},
    "interests": [],
    "degree_program": None,
    "current_semester": None,
}


def detect_forgets(message: str) -> list[str]:
    """Return fields the student explicitly asked DAIA to forget."""
    msg = (message or "").lower()
    return [
        field
        for field, patterns in _FORGET_PATTERNS.items()
        if any(re.search(pat, msg) for pat in patterns)
    ]


def _strip_fence(raw: str) -> str:
    value = (raw or "").strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, count=1)
    if value.endswith("```"):
        value = value[:-3].strip()
    return value


def _clean_interests(items: list[str]) -> list[str]:
    results, seen = [], set()
    for raw in items:
        item = (raw or "").strip()
        if not item:
            continue
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            results.append(item)
    return results


# ============================================================
# EXTRACTION
# ============================================================


def extract_student_preferences(
    message: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> dict:
    """Return validated updates. Never raises — returns {} on failure.

    Returned dict contains ONLY fields the student actually mentioned.
    Safe to pass directly as **kwargs to update_student_profile().
    """
    if not _should_extract(message):
        return {}

    message = (message or "").strip()
    model = model or os.getenv("MODEL_ID") or "llama3.2:3b"
    base_url = base_url or "http://ollama:11434"
    timeout = timeout or float(os.getenv("OLLAMA_TIMEOUT", "900"))

    client = Client(host=base_url, timeout=timeout)

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            format=ProfileUpdates.model_json_schema(),
            options={"temperature": 0},
        )
        cleaned = _strip_fence(response["message"]["content"])
        parsed = ProfileUpdates.model_validate_json(cleaned)
    except ValidationError as exc:
        print(f"[PREFERENCES] schema mismatch: {exc}")
        return {}
    except Exception as exc:
        print(f"[PREFERENCES] LLM failure: {type(exc).__name__}: {exc}")
        return {}

    updates: dict = {}

    if parsed.preferred_study_time:
        normalized = parsed.preferred_study_time.strip().lower()
        if normalized in _VALID_STUDY_TIMES:
            updates["preferred_study_time"] = normalized

    if parsed.study_hours_per_week is not None:
        updates["study_hours_per_week"] = int(parsed.study_hours_per_week)

    if parsed.career_goals:
        cleaned_goals = {
            str(k).strip(): str(v).strip()
            for k, v in parsed.career_goals.items()
            if k and v and str(v).strip()
        }
        if cleaned_goals:
            updates["career_goals"] = cleaned_goals

    if parsed.interests:
        cleaned_interests = _clean_interests(parsed.interests)
        if cleaned_interests:
            updates["interests"] = cleaned_interests

    if parsed.degree_program:
        updates["degree_program"] = parsed.degree_program.strip()

    if parsed.current_semester is not None:
        updates["current_semester"] = int(parsed.current_semester)

    return updates


# ============================================================
# BACKWARD COMPAT
# ============================================================


def extract_memory_updates(message: str) -> dict:
    """Legacy alias. Preserved so existing imports don't break."""
    return extract_student_preferences(message)
