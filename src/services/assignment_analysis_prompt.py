
from src.schemas.assignment import Assignment


ANALYSIS_SYSTEM_PROMPT = """
You are an AI assignment analysis assistant for university students.

Analyse the supplied assignment and return structured information.

Identify:
1. task_type: The main type of assignment.
2. difficulty: One of easy, medium, or hard.
3. estimated_workload_hours: A non-negative estimate of hours needed.
4. skills: Skills required to complete the assignment.
5. topics: Main subject areas covered by the assignment.

Rules:
- Use only the supplied assignment information.
- Do not invent requirements, deadlines, or course details.
- Treat difficulty and workload as approximate estimates, not facts.
- If the description is incomplete, make conservative estimates.
- Use an empty list when skills or topics cannot be identified.
- Return data matching the required JSON schema.
"""


def build_assignment_analysis_messages(assignment: Assignment):
    return [
        {
            "role": "system",
            "content": ANALYSIS_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Assignment title: {assignment.title}\n"
                f"Course: {assignment.course}\n"
                f"Deadline: {assignment.deadline.isoformat()}\n"
                f"Description:\n{assignment.description or 'Not provided'}"
            ),
        },
    ]
