
import json
from datetime import datetime, timezone
from pathlib import Path

from src.schemas.assignment import Assignment
from src.services.assignment_analysis_service import analyze_assignment


TEST_FILE = Path("evaluation/assignment_analysis_test_cases.json")
OUTPUT_FILE = Path("evaluation/assignment_analysis_results.json")


def normalize(value):
    text = str(value).strip().lower()
    return text.replace("_", " ").replace("-", " ")


def evaluate_case(case):
    assignment = Assignment(
        title=case["title"],
        course="Evaluation Test Course",
        deadline=datetime(2026, 12, 1, tzinfo=timezone.utc),
        description=case["description"],
    )

    analysis = analyze_assignment(assignment)
    result = analysis.model_dump()

    if case["category"] != "successful_case":
        # Difficult/failure cases require manual review for invented facts.
        status = "pending"
    else:
        checks = []

        checks.append(
            normalize(result["task_type"])
            == normalize(case["expected_task_type"])
        )

        checks.append(
            normalize(result["difficulty"])
            == normalize(case["expected_difficulty"])
        )

        hours = result["estimated_workload_hours"]
        minimum, maximum = case["expected_workload_hours_range"]
        checks.append(minimum <= hours <= maximum)

        skills = [normalize(x) for x in result["skills"]]
        checks.append(
            all(
                any(expected.lower() in actual for actual in skills)
                for expected in case["expected_skills"]
            )
        )

        topics = [normalize(x) for x in result["topics"]]
        checks.append(
            all(
                any(expected.lower() in actual for actual in topics)
                for expected in case["expected_topics"]
            )
        )

        print("  Checks [task type, difficulty, workload, skills, topics]:", checks)
        
        if all(checks):
            status = "pass"
        elif any(checks):
            status = "partial"
        else:
            status = "fail"

    return {
        **case,
        "actual_result": result,
        "status": status,
    }


def main():
    cases = json.loads(TEST_FILE.read_text(encoding="utf-8"))
    results = []

    for case in cases:
        print(f"Running {case['id']}...")
        try:
            evaluated = evaluate_case(case)
            print(f"  Status: {evaluated['status']}")
        except Exception as error:
            evaluated = {
                **case,
                "actual_result": {
                    "error": type(error).__name__,
                    "message": str(error),
                },
                "status": "pending",
            }
            print(f"  Error: {type(error).__name__}: {error}")

        results.append(evaluated)

    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
