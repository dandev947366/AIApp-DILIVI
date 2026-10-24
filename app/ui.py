"""
DAIA — AI Study Path & Career Assistant
---------------------------------------
Features:
- Separate account section for login, registration, and logout
- First-time Moodle iCal registration and calendar synchronization
- Persistent student profile and skills
- Transcript extraction using a local Ollama model
- Student-aware chat
- System and job-market status panels

Note:
Moodle ID + full name is basic identity matching, not secure
authentication. Use proper authentication before deploying with
real student data to multiple users.
"""

import os
import re
import time
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from src.rag.ingest import init_rag_db
import gradio as gr
import httpx
import pymupdf
from dotenv import load_dotenv
from ollama import Client
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.database import SessionLocal, init_db
from src.services.agent_service import agent_service
from src.services.moodle_sync_service import sync_calendar_to_db
from src.models.calendar_models import StudentModel, CourseModel
from src.tools.profile import get_student_profile, update_student_profile
from src.tools.skills import get_student_skills, add_or_update_skill
from src.collectors.health import get_collection_health

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

MODEL_ID = (os.getenv("MODEL_ID") or os.getenv("MODEL_NAME") or "llama3.2:3b").strip()

OLLAMA_BASE_URL = (
    (os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://ollama:11434")
    .strip()
    .rstrip("/")
)

OLLAMA_TIMEOUT = max(30, int(os.getenv("OLLAMA_TIMEOUT", "900")))
TRANSCRIPT_CHUNK_SIZE = max(
    500,
    int(os.getenv("TRANSCRIPT_CHUNK_SIZE", "2200")),
)
OLLAMA_MAX_RETRIES = max(0, int(os.getenv("OLLAMA_MAX_RETRIES", "2")))
OLLAMA_RETRY_BASE_SECONDS = 2

init_db()
init_rag_db()

# ============================================================
# STRUCTURED TRANSCRIPT SCHEMAS
# ============================================================


class ExtractedSkill(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    proficiency: int | None = Field(default=None, ge=1, le=5)
    evidence: str = ""


class ExtractedCourse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str = ""
    name: str = ""


class TranscriptData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    degree_program: str = ""
    interests: list[str] = Field(default_factory=list)
    skills: list[ExtractedSkill] = Field(default_factory=list)
    courses: list[ExtractedCourse] = Field(default_factory=list)


# ============================================================
# GENERAL HELPERS
# ============================================================


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _dedupe_strings(values: list[str]) -> list[str]:
    results = []
    seen = set()

    for value in values:
        value = _normalise_text(value)
        key = value.casefold()

        if value and key not in seen:
            seen.add(key)
            results.append(value)

    return results


def _student_name_for(student) -> str:
    """Get the full name from StudentModel."""
    if student is None:
        return ""

    return _normalise_text(getattr(student, "full_name", "") or "")


def _parse_moodle_user_id(ical_url: str) -> int | None:
    """Extract userid from the Moodle calendar export URL."""
    try:
        query = parse_qs(urlparse(ical_url).query)
        return int(query["userid"][0])
    except (KeyError, ValueError, IndexError, TypeError):
        return None


def _get_student_session(moodle_user_id: int) -> dict:
    """Build the session data from an existing student record."""
    with SessionLocal() as db:
        student = (
            db.query(StudentModel).filter_by(moodle_user_id=moodle_user_id).first()
        )

        if student is None:
            return {}

        return {
            "moodle_user_id": int(student.moodle_user_id),
            "student_db_id": int(student.student_id),
            "student_name": _student_name_for(student),
        }


# ============================================================
# ACCOUNT: LOGIN
# ============================================================


def login_student(moodle_id: str, student_name: str):
    """
    Match the supplied Moodle ID and full name to a stored student.
    Returns (message, session_state).
    """
    moodle_id = (moodle_id or "").strip()
    student_name = _normalise_text(student_name)

    if not moodle_id.isdigit():
        return "Enter a valid numeric Moodle student ID.", {}

    if not student_name:
        return "Enter your full name.", {}

    try:
        with SessionLocal() as db:
            student = (
                db.query(StudentModel)
                .filter(StudentModel.moodle_user_id == int(moodle_id))
                .first()
            )

            if student is None:
                return (
                    "Account not found. Select **Create account** "
                    "to register using your Moodle calendar URL.",
                    {},
                )

            stored_name = _student_name_for(student)

            if not stored_name:
                return (
                    "The stored student record has no full name. "
                    "Please check the database record.",
                    {},
                )

            if stored_name.casefold() != student_name.casefold():
                return (
                    "The Moodle ID and full name do not match "
                    "the registered account.",
                    {},
                )

            session = {
                "moodle_user_id": int(student.moodle_user_id),
                "student_db_id": int(student.student_id),
                "student_name": stored_name,
            }

        return f"Welcome back, **{stored_name}**!", session

    except Exception as exc:
        traceback.print_exc()
        return (
            f"Login failed: `{type(exc).__name__}: {exc}`",
            {},
        )


# ============================================================
# ACCOUNT: CREATE ACCOUNT / MOODLE ONBOARDING
# ============================================================


def onboard_student(ical_url: str, student_name: str):
    """
    Register a student using their Moodle iCal export URL and name.

    The Moodle userid is read from the URL. The existing calendar
    synchronization service creates or updates the student record.
    """
    ical_url = (ical_url or "").strip()
    student_name = _normalise_text(student_name)

    if not student_name:
        return "Enter your full name.", {}

    if not ical_url.startswith(("http://", "https://")):
        return (
            "Enter a valid Moodle calendar export URL starting with " "`https://`.",
            {},
        )

    if "/calendar/export_execute.php" not in ical_url:
        return (
            "That URL does not look like a Moodle calendar export URL.\n\n"
            "In Moodle, open **Calendar → Export calendar → "
            "Get URL for this calendar**.",
            {},
        )

    moodle_user_id = _parse_moodle_user_id(ical_url)

    if moodle_user_id is None:
        return (
            "Could not find `userid=` in the URL. Copy the calendar "
            "export URL again from Moodle.",
            {},
        )

    try:
        # Sync the Moodle calendar and create/update the student record.
        with SessionLocal() as db:
            stats = sync_calendar_to_db(
                ical_url,
                moodle_user_id,
                student_name,
                db,
            )

        # Re-query after synchronization so the session contains the
        # actual database student_id and stored full_name.
        session = _get_student_session(moodle_user_id)

        if not session.get("student_db_id"):
            return (
                "Calendar synchronization returned, but the student "
                "record could not be found. Check the backend logs.",
                {},
            )

        stored_name = session.get("student_name") or student_name

        # If the sync service created the record with a fallback name,
        # update the full name supplied by the student.
        with SessionLocal() as db:
            student = (
                db.query(StudentModel).filter_by(moodle_user_id=moodle_user_id).first()
            )

            if student is not None and student_name:
                student.full_name = student_name
                student.ical_url = ical_url
                db.commit()
                stored_name = student_name

        session["student_name"] = stored_name

        events_added = stats.get("events_added", 0) if isinstance(stats, dict) else 0
        events_updated = (
            stats.get("events_updated", 0) if isinstance(stats, dict) else 0
        )
        courses_added = stats.get("courses_added", 0) if isinstance(stats, dict) else 0

        message = f"""## Account created successfully!

Welcome, **{stored_name}**.

Your Moodle calendar has been synchronized.

- **Moodle student ID:** `{moodle_user_id}`
- **Calendar events added:** {events_added}
- **Calendar events updated:** {events_updated}
- **Courses added:** {courses_added}

You are now logged in. Your dashboard is ready to use.
"""

        return message, session

    except Exception as exc:
        traceback.print_exc()
        return (
            f"Account creation or calendar synchronization failed: "
            f"`{type(exc).__name__}: {exc}`",
            {},
        )


# ============================================================
# ACCOUNT: IDENTITY AND SESSION STATE
# ============================================================


def refresh_student_identity(session_state):
    session = session_state or {}

    if not session.get("student_db_id"):
        return (
            "No student is currently logged in. "
            "Create an account or log in to access your personal data."
        )

    return (
        f"**Student:** {session.get('student_name', 'Student')}\n\n"
        f"**Moodle ID:** `{session.get('moodle_user_id', '')}`"
    )


def account_status_text(session_state):
    session = session_state or {}

    if session.get("student_db_id"):
        return "**Status:** Logged in"

    return "**Status:** Not logged in"


def switch_account_mode(mode, session_state):
    """
    Show the appropriate form inside the Account box.
    The dashboard itself is never hidden.
    """
    logged_in = bool((session_state or {}).get("student_db_id"))

    return (
        gr.update(visible=(mode == "login" and not logged_in)),
        gr.update(visible=(mode == "create" and not logged_in)),
        gr.update(visible=logged_in),
    )


def logout_student():
    """
    Clear the active browser session and chat history.
    Do not delete the student's database record or calendar events.
    """
    return (
        {},  # session_state
        [],  # chatbot history
        "**Status:** Not logged in",
        "Create an account or log in to access your personal data.",
        "You have logged out. Your saved account and calendar data remain intact.",
        gr.update(visible=True),  # login form
        gr.update(visible=False),  # create form
        gr.update(visible=False),  # logout button
        "login",  # account mode
    )


def on_app_load(session_state):
    """Validate cached session on page load and refresh the UI."""
    session = session_state or {}

    # Nothing cached — plain logged-out view.
    if not session.get("student_db_id"):
        return (
            {},
            account_status_text({}),
            refresh_student_identity({}),
            refresh_profile({}),
            refresh_system_status({}),
            refresh_job_health(),
            gr.update(visible=True),  # login_form
            gr.update(visible=False),  # create_form
            gr.update(visible=False),  # logout_btn
        )

    # Verify the student still exists (guards against stale cache
    # after a DB reset or a deleted account).
    from src.database import SessionLocal
    from src.models.calendar_models import StudentModel

    with SessionLocal() as db:
        student = (
            db.query(StudentModel)
            .filter_by(
                student_id=session.get("student_db_id"),
                moodle_user_id=session.get("moodle_user_id"),
            )
            .first()
        )

    if student is None:
        # Cache points at a student that no longer exists — clear it.
        return (
            {},
            account_status_text({}),
            refresh_student_identity({}),
            refresh_profile({}),
            refresh_system_status({}),
            refresh_job_health(),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    # Keep the stored session and render the logged-in view.
    return (
        session,
        account_status_text(session),
        refresh_student_identity(session),
        refresh_profile(session),
        refresh_system_status(session),
        refresh_job_health(),
        gr.update(visible=False),  # login_form
        gr.update(visible=False),  # create_form
        gr.update(visible=True),  # logout_btn
    )


# ============================================================
# PDF AND TEXT EXTRACTION
# ============================================================


def extract_pdf_text(file_path: Path) -> tuple[list[str], dict]:
    """Extract PDF text page by page and flag pages that may need OCR."""
    page_texts = []
    page_stats = []

    with pymupdf.open(str(file_path)) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text", sort=True).strip()

            page_stats.append(
                {
                    "page": page_number,
                    "characters": len(text),
                    "needs_ocr": len(text) < 40,
                }
            )

            if text:
                page_texts.append(f"--- PAGE {page_number} ---\n{text}")

    combined_text = "\n\n".join(page_texts).strip()

    report = {
        "page_count": len(page_stats),
        "character_count": len(combined_text),
        "pages": page_stats,
        "ocr_candidates": [item["page"] for item in page_stats if item["needs_ocr"]],
    }

    return page_texts, report


def extract_text_file(file_path: Path) -> list[str]:
    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    text = text.strip()
    return [text] if text else []


def split_long_text(text: str, max_chars: int) -> list[str]:
    """Split long text using paragraph, line, sentence, or word boundaries."""
    text = (text or "").strip()

    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        cut = window.rfind("\n\n")

        if cut < max_chars // 2:
            cut = window.rfind("\n")

        if cut < max_chars // 2:
            cut = max(
                window.rfind(". "),
                window.rfind("? "),
                window.rfind("! "),
            )

        if cut < max_chars // 2:
            cut = window.rfind(" ")

        if cut <= 0:
            cut = max_chars

        part = remaining[:cut].strip()

        if part:
            chunks.append(part)

        remaining = remaining[cut:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def build_transcript_chunks(
    page_texts: list[str],
    max_chars: int = TRANSCRIPT_CHUNK_SIZE,
) -> list[str]:
    """Create bounded chunks while preserving page boundaries when possible."""
    chunks = []
    current_parts = []
    current_length = 0

    for page_text in page_texts:
        for part in split_long_text(page_text, max_chars):
            separator_length = 2 if current_parts else 0

            if (
                current_parts
                and current_length + separator_length + len(part) > max_chars
            ):
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_length = 0

            if current_parts:
                current_length += 2

            current_parts.append(part)
            current_length += len(part)

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return [chunk for chunk in chunks if chunk.strip()]


# ============================================================
# OLLAMA AND STRUCTURED EXTRACTION
# ============================================================


def create_ollama_client() -> Client:
    return Client(
        host=OLLAMA_BASE_URL,
        timeout=float(OLLAMA_TIMEOUT),
    )


def check_ollama_connection(client: Client) -> None:
    try:
        response = httpx.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=10.0,
        )
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_BASE_URL}. "
            "Check the Docker Compose service and network."
        ) from exc


def _strip_json_fence(raw_output: str) -> str:
    value = (raw_output or "").strip()

    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, count=1)

    if value.endswith("```"):
        value = value[:-3].strip()

    return value


def extract_transcript_chunk(
    client: Client,
    model: str,
    chunk_text: str,
) -> TranscriptData:
    """Extract validated structured information from a transcript chunk."""
    system_prompt = """
You extract student information from academic transcript text.

Rules:
1. Extract only information explicitly supported by the text.
2. Never invent courses, course codes, skills, interests, or degrees.
3. Include a skill only when there is evidence in the text.
4. Proficiency must be from 1 to 5 only when supported by evidence;
   otherwise return null.
5. Do not infer advanced proficiency from a course title alone.
6. Use empty strings for missing textual fields.
7. Return only the requested JSON object.
""".strip()

    last_error = None

    for attempt in range(OLLAMA_MAX_RETRIES + 1):
        try:
            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Extract the student information from this text:\n\n"
                            + chunk_text
                        ),
                    },
                ],
                format=TranscriptData.model_json_schema(),
                options={
                    "temperature": 0,
                    "num_predict": 1200,
                },
            )

            raw_output = response["message"]["content"]
            cleaned = _strip_json_fence(raw_output)

            try:
                return TranscriptData.model_validate_json(cleaned)
            except ValidationError as exc:
                raise ValueError(f"Invalid structured model output: {exc}") from exc

        except Exception as exc:
            last_error = exc

            if attempt >= OLLAMA_MAX_RETRIES:
                break

            wait_seconds = OLLAMA_RETRY_BASE_SECONDS * (2**attempt)

            print(
                f"[OLLAMA] Attempt {attempt + 1} failed: {exc}. "
                f"Retrying in {wait_seconds}s.",
                flush=True,
            )
            time.sleep(wait_seconds)

    raise RuntimeError(
        f"Transcript extraction failed after "
        f"{OLLAMA_MAX_RETRIES + 1} attempts: {last_error}"
    ) from last_error


def merge_transcript_data(
    merged: TranscriptData,
    incoming: TranscriptData,
) -> TranscriptData:
    """Merge extraction results and deduplicate skills and courses."""
    if incoming.degree_program and not merged.degree_program:
        merged.degree_program = _normalise_text(incoming.degree_program)

    merged.interests = _dedupe_strings(merged.interests + incoming.interests)

    known_skills = {
        _normalise_text(skill.name).casefold(): index
        for index, skill in enumerate(merged.skills)
        if _normalise_text(skill.name)
    }

    for skill in incoming.skills:
        name = _normalise_text(skill.name)

        if not name:
            continue

        key = name.casefold()

        if key not in known_skills:
            merged.skills.append(skill.model_copy(update={"name": name}))
            known_skills[key] = len(merged.skills) - 1
            continue

        existing = merged.skills[known_skills[key]]

        if existing.proficiency is None and skill.proficiency is not None:
            existing.proficiency = skill.proficiency

        if skill.evidence and not existing.evidence:
            existing.evidence = skill.evidence

    known_courses = {
        (_normalise_text(course.code) or _normalise_text(course.name)).casefold(): index
        for index, course in enumerate(merged.courses)
        if _normalise_text(course.code) or _normalise_text(course.name)
    }

    for course in incoming.courses:
        code = _normalise_text(course.code)
        name = _normalise_text(course.name)

        if not code and not name:
            continue

        key = (code or name).casefold()

        if key not in known_courses:
            merged.courses.append(ExtractedCourse(code=code, name=name))
            known_courses[key] = len(merged.courses) - 1
            continue

        existing = merged.courses[known_courses[key]]

        if not existing.code and code:
            existing.code = code

        if not existing.name and name:
            existing.name = name

    return merged


# ============================================================
# TRANSCRIPT PIPELINE
# ============================================================


def process_transcript(file, session_state):
    if not file:
        yield "No file selected."
        return

    student_db_id = (session_state or {}).get("student_db_id")

    if not student_db_id:
        yield "Please log in before importing a transcript."
        return

    file_path = Path(file)

    if not file_path.exists():
        yield f"File not found: `{file_path}`"
        return

    suffix = file_path.suffix.lower()

    if suffix not in {".pdf", ".txt"}:
        yield "Upload a PDF or TXT file."
        return

    yield "⏳ **Step 1/3:** Reading the document..."

    extraction_report = {
        "page_count": 0,
        "character_count": 0,
        "ocr_candidates": [],
    }

    try:
        if suffix == ".pdf":
            page_texts, extraction_report = extract_pdf_text(file_path)
        else:
            page_texts = extract_text_file(file_path)
            extraction_report["character_count"] = sum(len(part) for part in page_texts)
    except Exception as exc:
        yield f"Failed to read the document: `{type(exc).__name__}: {exc}`"
        return

    if not page_texts or not any(part.strip() for part in page_texts):
        yield (
            "No usable text was extracted. This may be a scanned PDF " "that needs OCR."
        )
        return

    chunks = build_transcript_chunks(
        page_texts,
        max_chars=TRANSCRIPT_CHUNK_SIZE,
    )

    if not chunks:
        yield "No usable transcript chunks could be created."
        return

    yield (
        f"⏳ **Step 2/3:** Extracting structured information using "
        f"`{MODEL_ID}` across {len(chunks)} chunks..."
    )

    try:
        client = create_ollama_client()
        check_ollama_connection(client)

        tag_response = httpx.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=10.0,
        )
        tag_response.raise_for_status()

        available_models = {
            item.get("name", "") for item in tag_response.json().get("models", [])
        }

        if (
            available_models
            and MODEL_ID not in available_models
            and f"{MODEL_ID}:latest" not in available_models
        ):
            raise RuntimeError(
                f"Configured model `{MODEL_ID}` was not found. "
                f"Available models: {', '.join(sorted(available_models))}"
            )

        merged_data = TranscriptData()

        for index, chunk in enumerate(chunks, start=1):
            print(
                f"[TRANSCRIPT] Processing chunk {index}/{len(chunks)}",
                flush=True,
            )

            chunk_data = extract_transcript_chunk(
                client,
                MODEL_ID,
                chunk,
            )

            merged_data = merge_transcript_data(
                merged_data,
                chunk_data,
            )

    except Exception as exc:
        traceback.print_exc()
        yield (
            "Transcript extraction failed. No transcript data was saved.\n\n"
            f"Error: `{type(exc).__name__}: {exc}`\n\n"
            "Check the Ollama service, model name, timeout, and logs."
        )
        return

    yield "⏳ **Step 3/3:** Saving skills, courses, and profile information..."

    saved_stats = {"skills": 0, "courses": 0}

    try:
        profile_updates = {}

        if merged_data.degree_program:
            profile_updates["degree_program"] = merged_data.degree_program

        if merged_data.interests:
            profile_updates["interests"] = merged_data.interests

        if profile_updates:
            update_student_profile(
                student_db_id,
                **profile_updates,
            )

        seen_skills = set()

        for skill in merged_data.skills:
            skill_name = _normalise_text(skill.name)

            if not skill_name or skill_name.casefold() in seen_skills:
                continue

            proficiency = skill.proficiency if skill.proficiency is not None else 3
            proficiency = max(1, min(5, int(proficiency)))

            add_or_update_skill(
                student_db_id,
                skill_name,
                proficiency,
                evidence=skill.evidence or "Imported from transcript",
                source="transcript",
            )

            seen_skills.add(skill_name.casefold())
            saved_stats["skills"] += 1

        # CourseModel currently has a globally unique course_code.
        # This preserves the existing project schema.
        with SessionLocal() as db:
            seen_course_codes = set()

            for course in merged_data.courses:
                code = _normalise_text(course.code)
                name = _normalise_text(course.name)

                if not code or code.casefold() in seen_course_codes:
                    continue

                seen_course_codes.add(code.casefold())

                existing = db.query(CourseModel).filter_by(course_code=code).first()

                if existing is None:
                    db.add(
                        CourseModel(
                            course_code=code,
                            course_name=name or code,
                        )
                    )
                    saved_stats["courses"] += 1

            db.commit()

    except Exception as exc:
        traceback.print_exc()
        yield ("Database save failed: " f"`{type(exc).__name__}: {exc}`")
        return

    warnings = []

    if extraction_report.get("ocr_candidates"):
        pages = ", ".join(str(page) for page in extraction_report["ocr_candidates"])
        warnings.append(
            f"Pages {pages} may require OCR because little text was extracted."
        )

    warning_text = (
        "\n\n**Warnings:**\n" + "\n".join(f"- {w}" for w in warnings)
        if warnings
        else ""
    )

    yield f"""## Transcript processed successfully

- **Degree:** {merged_data.degree_program or "Not found"}
- **Interests:** {", ".join(merged_data.interests) or "Not found"}
- **Skills extracted:** {len(merged_data.skills)}
- **Skills saved:** {saved_stats["skills"]}
- **Courses extracted:** {len(merged_data.courses)}
- **New courses saved:** {saved_stats["courses"]}
- **Text characters:** {extraction_report.get("character_count", 0)}
- **Chunks processed:** {len(chunks)}

{warning_text}
"""


# ============================================================
# CHAT
# ============================================================


def chat(message, history, session_state):
    session = session_state or {}
    moodle_user_id = session.get("moodle_user_id")

    if not moodle_user_id:
        return (
            "Please create an account or log in using the **Account** "
            "section before asking questions about personal student data."
        )

    if not message or not message.strip():
        return "Enter a message first."

    return agent_service(message, moodle_user_id)


def user_submit(message, history, session):
    """Handle chat using Gradio's messages format (streaming)."""

    history = list(history or [])

    if not message or not message.strip():
        yield "", history
        return

    # Normalize any old tuple-based history.
    normalized_history = []

    for item in history:
        if isinstance(item, dict):
            if "role" in item and "content" in item:
                normalized_history.append(item)
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            user_message, assistant_message = item

            if user_message:
                normalized_history.append(
                    {
                        "role": "user",
                        "content": str(user_message),
                    }
                )

            if assistant_message:
                normalized_history.append(
                    {
                        "role": "assistant",
                        "content": str(assistant_message),
                    }
                )

    history = normalized_history
    message = message.strip()

    # Show the user's message immediately.
    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    # Login guard — the agent needs a moodle_user_id.
    moodle_user_id = (session or {}).get("moodle_user_id")
    if not moodle_user_id:
        history.append(
            {
                "role": "assistant",
                "content": (
                    "Please create an account or log in using the **Account** "
                    "section before asking questions about personal student data."
                ),
            }
        )
        yield "", history
        return

    # Placeholder assistant bubble that gets rewritten on every update.
    history.append(
        {
            "role": "assistant",
            "content": "🔍 Starting…",
        }
    )
    yield "", history

    # Lazy import to avoid circular imports at module load time.
    from src.services.agent_service import agent_service_stream

    try:
        for text, is_final in agent_service_stream(message, moodle_user_id):
            history[-1]["content"] = text
            yield "", history

            if is_final:
                return

    except Exception as exc:
        traceback.print_exc()
        history[-1]["content"] = f"An error occurred: `{type(exc).__name__}: {exc}`"
        yield "", history
        return
    if not history[-1]["content"] or history[-1]["content"] == "🔍 Starting…":
        history[-1]["content"] = (
            "The assistant finished without producing an answer. " "Please try again."
        )
        yield "", history


# ============================================================
# SIDEBAR: STUDENT PROFILE
# ============================================================


def refresh_profile(session_state):
    session = session_state or {}
    student_id = session.get("student_db_id")

    if not student_id:
        return "### Student Profile\n\n" "Log in to view your saved profile and skills."

    try:
        profile = get_student_profile(student_id) or {}
        skills = get_student_skills(student_id) or []
    except Exception as exc:
        traceback.print_exc()
        return (
            "### Student Profile\n\n"
            f"Unable to load profile: `{type(exc).__name__}: {exc}`"
        )

    if not profile and not skills:
        return (
            "### Student Profile\n\n"
            "No profile data yet. Import a transcript or update your profile."
        )

    goals = profile.get("career_goals") or {}

    goals_text = (
        "\n".join(
            f"- **{key.replace('_', ' ').title()}:** {value}"
            for key, value in goals.items()
        )
        if goals
        else "Not specified"
    )

    interests = ", ".join(profile.get("interests") or []) or "None recorded"

    skills_text = (
        "\n".join(
            f"- {item.get('skill_name', 'Unknown').title()}: "
            f"{item.get('proficiency', '?')}/5"
            for item in skills
        )
        if skills
        else "None recorded"
    )

    return f"""### Student Profile

**Name:** {session.get("student_name", "Student")}

**Degree:** {profile.get("degree_program") or "Unknown"}

**Preferred study time:** {profile.get("preferred_study_time") or "Unknown"}

**Study hours/week:** {profile.get("study_hours_per_week") or "Unknown"}

**Career goals:**
{goals_text}

**Interests:** {interests}

**Skills:**
{skills_text}
"""


# ============================================================
# SIDEBAR: JOB MARKET HEALTH
# ============================================================


def refresh_job_health():
    try:
        health = get_collection_health() or {}
    except Exception as exc:
        traceback.print_exc()
        return (
            "### Job Market Data\n\n"
            f"Unable to load job data: `{type(exc).__name__}: {exc}`"
        )

    by_country = health.get("by_country") or {}

    countries_text = (
        "\n".join(f"- {country}: {count}" for country, count in by_country.items())
        if by_country
        else "No country data available"
    )

    return f"""### Job Market Data

**Status:** {health.get("health", "unknown").upper()}

**Active jobs:** {health.get("active_jobs", 0)}

**Last successful run:** {health.get("last_successful_run_at", "Never")}

**Jobs by country:**
{countries_text}
"""


# ============================================================
# SIDEBAR: TUTOR PROGRESS
# ============================================================


async def refresh_tutor_state(session_state):
    session = session_state or {}
    if not session.get("student_db_id"):
        return (
            "### 🎓 Tutor Progress\n\nLog in to view your adaptive learning progress."
        )

    try:
        # Lazy import to avoid circular dependencies and heavy startup costs
        from src.mcp.tutor_mcp import call_tutor_tool

        async def _fetch():
            # Fetch alerts and the next recommended activity
            alerts = await call_tutor_tool("get_pending_alerts", {})
            next_activity = await call_tutor_tool("get_next_activity", {})
            return alerts, next_activity

        alerts, next_activity = await _fetch()

        def _format_response(resp):
            """Helper to extract text from MCP content objects."""
            if not resp:
                return "None"
            if isinstance(resp, str):
                return resp
            if isinstance(resp, list):
                return "\n".join(
                    getattr(item, "text", str(item))
                    for item in resp
                    if getattr(item, "type", "") == "text"
                )
            return str(resp)

        alerts_text = _format_response(alerts)
        next_act_text = _format_response(next_activity)

        return f"""### 🎓 Tutor Progress

**Pending Alerts:**
{alerts_text}

**Next Activity:**
{next_act_text}
"""
    except Exception as exc:
        traceback.print_exc()
        return f"### 🎓 Tutor Progress\n\nUnable to load data: `{type(exc).__name__}: {exc}`"


# ============================================================
# SIDEBAR: SYSTEM STATUS
# ============================================================


def refresh_system_status(session_state):
    session = session_state or {}

    moodle_id = session.get("moodle_user_id", "Not logged in")
    student_id = session.get("student_db_id", "—")

    return f"""### Local AI Configuration

**Account:** {"Logged in" if session.get("student_db_id") else "Not logged in"}

**Moodle ID:** `{moodle_id}`

**Internal student DB ID:** `{student_id}`

**Model:** `{MODEL_ID}`

**Ollama endpoint:** `{OLLAMA_BASE_URL}`

**Request timeout:** {OLLAMA_TIMEOUT} seconds

**Transcript chunk size:** {TRANSCRIPT_CHUNK_SIZE} characters
"""


# ============================================================
# SESSION SECRET
# ============================================================


def _get_or_create_session_secret() -> str:
    """Return a stable secret, generating one on first boot."""
    # 1. Explicit env var wins.
    env_secret = os.getenv("SESSION_SECRET")
    if env_secret:
        return env_secret

    # 2. Otherwise, use/create a local file (stable across restarts).
    #    __file__ is /app/app/ui.py -> /app is the working directory root,
    #    and /app/data is the persistent volume that also holds SQLite.
    secret_path = Path(__file__).resolve().parent.parent / "data" / ".session_secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)

    if secret_path.exists():
        return secret_path.read_text().strip()

    import secrets

    new_secret = secrets.token_urlsafe(48)
    secret_path.write_text(new_secret)
    try:
        secret_path.chmod(0o600)  # owner-only on POSIX
    except OSError:
        pass
    print(f"[AUTH] generated new session secret at {secret_path}")
    return new_secret


SESSION_SECRET = _get_or_create_session_secret()


# ============================================================
# GRADIO UI
# ============================================================

with gr.Blocks(title="DAIA - AI Study & Career Assistant") as demo:
    # Single session state shared by account controls and dashboard.
    session_state = gr.BrowserState(
        default_value={},
        storage_key="daia_student_session",
        secret=SESSION_SECRET,
    )

    gr.Markdown("# 🎓 DAIA: AI Study Path & Career Assistant")
    gr.Markdown(
        "Your personalized study planner, student profile, " "and AI career assistant."
    )

    with gr.Row():
        # ----------------------------------------------------
        # MAIN DASHBOARD: ALWAYS VISIBLE
        # ----------------------------------------------------
        with gr.Column(scale=3):
            gr.Markdown("## 💬 Study & Career Dashboard")

            chatbot = gr.Chatbot(
                label="Chat with DAIA",
                height=750,
            )

            msg = gr.Textbox(
                label="Ask DAIA",
                placeholder=("Ask about your courses, deadlines, skills, or career..."),
            )

            submit_btn = gr.Button("Send", variant="primary")

            with gr.Accordion("📄 Import Transcript", open=False):
                gr.Markdown(
                    "Upload a transcript to extract degree information, "
                    "skills, interests, and courses using your local model."
                )

                transcript_file = gr.File(
                    label="Upload transcript",
                    file_types=[".pdf", ".txt"],
                    type="filepath",
                )

                transcript_btn = gr.Button("Extract Data")
                transcript_output = gr.Markdown()

        # ----------------------------------------------------
        # RIGHT SIDEBAR: ACCOUNT IS A SEPARATE BOX
        # ----------------------------------------------------
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("## 👤 Account")

                account_status = gr.Markdown(value="**Status:** Not logged in")

                identity_box = gr.Markdown(
                    value=(
                        "Create an account or log in to access " "your personal data."
                    )
                )

                account_mode = gr.Radio(
                    choices=[
                        ("Log in", "login"),
                        ("Create account", "create"),
                    ],
                    value="login",
                    label="Account action",
                )

                # Returning students
                with gr.Column(visible=True) as login_form:
                    login_id = gr.Textbox(
                        label="Moodle student ID",
                        placeholder="Enter your Moodle ID",
                    )

                    login_name = gr.Textbox(
                        label="Full name",
                        placeholder="Enter your registered full name",
                    )

                    login_btn = gr.Button(
                        "Log in",
                        variant="primary",
                    )

                # New students
                with gr.Column(visible=False) as create_form:
                    create_name = gr.Textbox(
                        label="Full name",
                        placeholder="Enter your full name",
                    )

                    create_ical = gr.Textbox(
                        label="Moodle calendar export URL",
                        placeholder="Paste your Moodle iCal URL",
                        type="password",
                    )

                    gr.Markdown(
                        "Your iCal URL contains a private token. " "Keep it secret."
                    )

                    create_btn = gr.Button(
                        "Create account & sync calendar",
                        variant="primary",
                    )

                account_output = gr.Markdown()

                logout_btn = gr.Button(
                    "Log out",
                    visible=False,
                )

            # ------------------------------------------------
            # STUDENT PROFILE
            # ------------------------------------------------
            with gr.Accordion("🧠 Student Profile", open=True):
                profile_box = gr.Markdown(value=refresh_profile({}))

                refresh_profile_btn = gr.Button("Refresh Profile")

            # ------------------------------------------------
            # SYSTEM STATUS
            # ------------------------------------------------
            with gr.Accordion("⚙️ System Status", open=False):
                system_box = gr.Markdown(value=refresh_system_status({}))

                refresh_system_btn = gr.Button("Refresh Status")

            # ------------------------------------------------
            # JOB DATA
            # ------------------------------------------------
            with gr.Accordion("💼 Job Market Data", open=False):
                job_box = gr.Markdown(value=refresh_job_health())

                refresh_job_btn = gr.Button("Refresh Job Data")

            # ------------------------------------------------
            # TUTOR PROGRESS
            # ------------------------------------------------
            with gr.Accordion("🎓 Tutor Progress", open=False):
                tutor_box = gr.Markdown(
                    value="Click refresh to load your learning progress."
                )
                refresh_tutor_btn = gr.Button("Refresh Tutor State")

    # ========================================================
    # ACCOUNT MODE SWITCHING
    # ========================================================

    account_mode.change(
        switch_account_mode,
        inputs=[account_mode, session_state],
        outputs=[login_form, create_form, logout_btn],
    )

    # ========================================================
    # LOAD (restore cached session)
    # ========================================================
    demo.load(
        on_app_load,
        inputs=[session_state],
        outputs=[
            session_state,
            account_status,
            identity_box,
            profile_box,
            system_box,
            job_box,
            login_form,
            create_form,
            logout_btn,
        ],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    # ========================================================
    # LOGIN
    # ========================================================
    login_btn.click(
        login_student,
        inputs=[login_id, login_name],
        outputs=[account_output, session_state],
    ).then(
        account_status_text,
        inputs=[session_state],
        outputs=[account_status],
    ).then(
        refresh_student_identity,
        inputs=[session_state],
        outputs=[identity_box],
    ).then(
        switch_account_mode,
        inputs=[account_mode, session_state],
        outputs=[login_form, create_form, logout_btn],
    ).then(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    ).then(
        refresh_system_status,
        inputs=[session_state],
        outputs=[system_box],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    create_btn.click(
        onboard_student,
        inputs=[create_ical, create_name],
        outputs=[account_output, session_state],
    ).then(
        account_status_text,
        inputs=[session_state],
        outputs=[account_status],
    ).then(
        refresh_student_identity,
        inputs=[session_state],
        outputs=[identity_box],
    ).then(
        switch_account_mode,
        inputs=[account_mode, session_state],
        outputs=[login_form, create_form, logout_btn],
    ).then(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    ).then(
        refresh_system_status,
        inputs=[session_state],
        outputs=[system_box],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    # ========================================================
    # LOGOUT
    # ========================================================

    logout_btn.click(
        logout_student,
        inputs=[],
        outputs=[
            session_state,
            chatbot,
            account_status,
            identity_box,
            account_output,
            login_form,
            create_form,
            logout_btn,
            account_mode,
        ],
    ).then(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    ).then(
        refresh_system_status,
        inputs=[session_state],
        outputs=[system_box],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    # ========================================================
    # CHAT
    # ========================================================

    submit_btn.click(
        user_submit,
        inputs=[msg, chatbot, session_state],
        outputs=[msg, chatbot],
    ).then(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    ).then(
        refresh_job_health,
        inputs=[],
        outputs=[job_box],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    msg.submit(
        user_submit,
        inputs=[msg, chatbot, session_state],
        outputs=[msg, chatbot],
    ).then(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    ).then(
        refresh_job_health,
        inputs=[],
        outputs=[job_box],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    # ========================================================
    # TRANSCRIPT IMPORT
    # ========================================================

    transcript_btn.click(
        process_transcript,
        inputs=[transcript_file, session_state],
        outputs=[transcript_output],
    ).then(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    ).then(
        refresh_job_health,
        inputs=[],
        outputs=[job_box],
    ).then(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )

    # ========================================================
    # SIDEBAR REFRESH
    # ========================================================

    refresh_profile_btn.click(
        refresh_profile,
        inputs=[session_state],
        outputs=[profile_box],
    )

    refresh_system_btn.click(
        refresh_system_status,
        inputs=[session_state],
        outputs=[system_box],
    )

    refresh_job_btn.click(
        refresh_job_health,
        inputs=[],
        outputs=[job_box],
    )

    refresh_tutor_btn.click(
        refresh_tutor_state,
        inputs=[session_state],
        outputs=[tutor_box],
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
    )
