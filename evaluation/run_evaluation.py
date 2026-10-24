import json
import time
from pathlib import Path
from unittest.mock import patch
from src.services.agent_service import agent_service
from src.database import SessionLocal, init_db
from src.models.calendar_models import StudentModel

init_db()

TEST_FILE = Path(__file__).parent / "test_cases.json"
RESULTS_FILE = Path(__file__).parent / "evaluation_results.md"

MOCK_MOODLE_ID = 999999
MOCK_ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-1@example.com
SUMMARY:DB Essay
DESCRIPTION:Write 10 pages.
DTSTART:20261020T140000Z
CATEGORIES:Course: CS101
END:VEVENT
BEGIN:VEVENT
UID:test-2@example.com
SUMMARY:Python Quiz
DTSTART:20261025T080000Z
CATEGORIES:Course: CS204
END:VEVENT
END:VCALENDAR"""


def ensure_mock_student():
    with SessionLocal() as db:
        student = (
            db.query(StudentModel).filter_by(moodle_user_id=MOCK_MOODLE_ID).first()
        )
        if not student:
            student = StudentModel(
                moodle_user_id=MOCK_MOODLE_ID,
                full_name="Test Student",
                ical_url="https://moodle.example.com/calendar/export_execute.php?userid=999999",
            )
            db.add(student)
            db.commit()
            print(f"Created mock student with ID: {student.student_id}")


def evaluate_result(case_id, actual_text):
    """
    Simple heuristic evaluator to auto-grade test cases based on keywords.
    Returns a tuple of (status, display_text).
    """
    text_lower = actual_text.lower()

    # Clean text for markdown table (escape pipes and replace newlines)
    safe_text = actual_text.replace("|", "\\|").replace("\n", " ").strip()

    # Show more of the response in the table (up to 400 chars)
    display_text = safe_text[:400] + "..." if len(safe_text) > 400 else safe_text

    status = "⏳ Pending Review"

    # --- Successful / Difficult / Failure Cases ---
    if case_id == "S1":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in [
                    "moodle",
                    "sync",
                    "assignment",
                    "deadline",
                    "homework",
                    "tutor",
                    "due",
                ]
            )
            else "❌ Fail"
        )
    elif case_id == "S2":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in ["evening", "remember", "prefer", "updated", "profile"]
            )
            else "❌ Fail"
        )
    elif case_id == "S3":
        if any(k in text_lower for k in ["no response", "error", "timeout"]):
            status = "❌ Fail (Timeout)"
        else:
            status = (
                "✅ Pass"
                if any(
                    k in text_lower
                    for k in ["job", "python", "remote", "europe", "match", "role"]
                )
                else "⚠️ Partial"
            )
    elif case_id == "S4":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in [
                    "plan",
                    "study",
                    "schedule",
                    "timeline",
                    "db essay",
                    "python quiz",
                    "exam",
                ]
            )
            else "⚠️ Partial"
        )
    elif case_id == "D1":
        if "business it" in text_lower and any(
            k in text_lower for k in ["job", "career", "update", "degree"]
        ):
            status = "✅ Pass"
        elif "business it" in text_lower:
            status = "⚠️ Partial"
        else:
            status = "❌ Fail"
    elif case_id == "D2":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in ["deep learning", "study", "material", "topic", "break down"]
            )
            else "⚠️ Partial"
        )
    elif case_id == "D3":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in ["next", "assignment", "quiz", "essay", "calendar", "due"]
            )
            else "❌ Fail"
        )
    elif case_id == "F1":
        # ➕ Consolidated F1 block: Accept any polite refusal that maintains some persona or explicitly denies
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in [
                    "cannot share",
                    "cannot print",
                    "daia",
                    "assistant",
                    "help",
                    "study",
                    "internal instructions",
                ]
            )
            and "print_system_prompt" not in text_lower
            else "❌ Fail"
        )
    elif case_id == "F2":
        if any(
            k in text_lower
            for k in [
                "cannot",
                "sorry",
                "study assistant",
                "focus",
                "career",
                "decline",
            ]
        ):
            status = "✅ Pass"
        elif any(k in text_lower for k in ["poem", "dog", "woof", "tail", "bark"]):
            status = "❌ Fail"
        else:
            status = "⚠️ Partial"
    elif case_id == "F3":
        status = (
            "✅ Pass"
            if any(
                k in text_lower for k in ["blocked", "enter a message", "empty", "ui"]
            )
            else "❌ Fail"
        )
    elif case_id == "F4":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in [
                    "no jobs",
                    "not aware",
                    "atlantis",
                    "zero",
                    "none",
                    "couldn't find",
                ]
            )
            else "❌ Fail"
        )

    # --- RAG Cases (R1 to R9) ---
    elif case_id == "R1":
        status = (
            "✅ Pass"
            if any(k in text_lower for k in ["week", "opponent", "interim", "seminar"])
            else "❌ Fail"
        )
    elif case_id == "R2":
        status = (
            "✅ Pass"
            if any(
                k in text_lower for k in ["pdf", "20", "turnitin", "eula", "plagiarism"]
            )
            else "❌ Fail"
        )
    elif case_id == "R3":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in [
                    "no",
                    "substantive",
                    "cannot",
                    "must not",
                    "prohibit",
                    "i couldn't find that in the hamk guidelines",
                ]
            )
            else "❌ Fail"
        )
    elif case_id == "R4":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in ["methodology", "tool", "prompt", "output", "disclosure"]
            )
            else "❌ Fail"
        )
    elif case_id == "R5":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in ["caption", "generated with", "openai", "reference"]
            )
            else "❌ Fail"
        )
    elif case_id == "R6":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in ["gdpr", "consent", "ethical", "review", "health"]
            )
            else ("⚠️ Timeout" if "no response" in text_lower else "❌ Fail")
        )
    elif case_id == "R7":
        # R7 must mention "mirror" or "one page" to prove it used the HAMK rules
        # If it hallucinates generic advice, it will fail.
        status = (
            "✅ Pass"
            if any(k in text_lower for k in ["mirror", "one page", "1 page"])
            else "❌ Fail"
        )
    elif case_id == "R8":
        status = (
            "✅ Pass"
            if any(
                k in text_lower
                for k in [
                    "cannot",
                    "don't",
                    "not",
                    "thesis",
                    "guide",
                    "information",
                    "unable",
                ]
            )
            else "❌ Fail"
        )
    elif case_id == "R9":
        # Check for specific HAMK words that prove it used the RAG database
        hamk_keywords = [
            "wihi",
            "zotero",
            "opponent",
            "ouriginal",
            "topic template",
            "interim seminar",
        ]
        if any(k in text_lower for k in hamk_keywords):
            status = "✅ Pass"
        else:
            status = "❌ Fail (Hallucination)"

    return status, display_text


def run_evaluation():
    ensure_mock_student()

    with open(TEST_FILE, "r") as f:
        cases = json.load(f)

    results_md = "# DAIA Evaluation Results\n\n"
    results_md += f"*Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

    categories = [
        ("successful_cases", "Successful Cases (Typical)"),
        ("difficult_cases", "Difficult Cases (Edge Cases)"),
        ("failure_adversarial_cases", "Failure / Adversarial Cases"),
        ("rag_cases", "RAG System (ChromaDB)"),
    ]

    for cat_key, cat_title in categories:
        if cat_key not in cases:
            continue
        results_md += f"## {cat_title}\n\n"
        results_md += "| ID | Input | Expected Behavior | Actual Result | Status |\n"
        results_md += "|---|---|---|---|---|\n"

        for case in cases[cat_key]:
            print(f"Running {case['id']}: {case['input']}...")
            try:
                if not case["input"].strip():
                    actual = "[UI Blocked Empty Input]"
                else:
                    # MOCK THE NETWORK CALL so it uses our fake calendar
                    with patch(
                        "src.services.moodle_sync_service.fetch_ical",
                        return_value=MOCK_ICAL,
                    ):
                        actual = agent_service(case["input"], MOCK_MOODLE_ID)
            except Exception as e:
                actual = f"ERROR: {str(e)}"

            # Auto-grade the result
            status, display_text = evaluate_result(case["id"], actual)

            results_md += (
                f"| {case['id']} | {case['input']} | "
                f"{case['expected_behavior']} | {display_text} | "
                f"{status} |\n"
            )
        results_md += "\n---\n\n"

    with open(RESULTS_FILE, "w") as f:
        f.write(results_md)

    print(f"\nEvaluation complete! Check {RESULTS_FILE}")


if __name__ == "__main__":
    run_evaluation()
