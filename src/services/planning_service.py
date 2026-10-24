import math
from datetime import timedelta

from src.config import BUFFER_DAYS, HOURS_PER_DAY
from src.services.assignment_analysis_service import analyze_assignment
from src.services.calendar_service import student_assignments


def recommended_start(deadline, hours):
    work_days = math.ceil(hours / HOURS_PER_DAY)
    return deadline.date() - timedelta(days=work_days + BUFFER_DAYS)


def build_plan(student_id, analyses):
    result = student_assignments(student_id)

    if result["status"] == "error":
        return result

    plan = []

    for item in result["assignments"]:
        if item.title.endswith("opens"):
            continue

        if item.title not in analyses:
            try:
                analyses[item.title] = analyze_assignment(item).model_dump()
            except Exception:
                plan.append({"assignment": item, "analysis": None})
                continue

        analysis = analyses[item.title]

        plan.append({
            "assignment": item,
            "analysis": analysis,
            "start": recommended_start(item.deadline, analysis["estimated_workload_hours"]),
        })

    return {"status": "ok", "plan": plan}
