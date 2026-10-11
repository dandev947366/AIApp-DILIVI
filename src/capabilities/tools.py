"""
Optional project capability: Tools & External API Integration.

Implement this module only if this capability is relevant to your application's
user problem. Remove the file if the capability is not used.

Conceptual Overview:
-------------------
Tools allow the AI application to perform operations beyond text generation,
such as fetching live data from external APIs, performing calculations, or
executing internal application functions.

Key concepts when implementing tools:
1. Tool Definition: Defining function schemas (names, descriptions, parameters)
   that describe what each tool does.
2. Model Tool Calling: Providing tool schemas to the model so it can request tool execution
   when needed.
3. Execution & Response: Parsing tool call requests, executing the corresponding
   Python function or API call, and passing the results back to the model or user.

Note:
-----
Tools should be deterministic, safe, and scoped to the user problem.
"""

# Tool functions for the AI Study Path & Career Assistant
# Ollama tool schemas and execution logic will be added next.

from src.services.calendar_service import upcoming_assignments


def get_upcoming_assignments(days: int = 7) -> dict:
    """Retrieve upcoming assignments within the next specified days."""

    if not isinstance(days, int) or isinstance(days, bool):
        return {
            "status": "error",
            "message": "Days must be an integer.",
        }

    if not 0 <= days <= 365:
        return {
            "status": "error",
            "message": "Days must be between 0 and 365.",
        }

    result = upcoming_assignments(days=days)

    if result["status"] != "ok":
        return result

    return {
        "status": "ok",
        "assignments": [
            {
                "title": assignment.title,
                "course": assignment.course,
                "deadline": assignment.deadline.isoformat(),
                "description": assignment.description,
            }
            for assignment in result["assignments"]
        ],
    }


UPCOMING_ASSIGNMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_upcoming_assignments",
        "description": (
            "Retrieve a student's upcoming assignments and deadlines "
            "within a specified number of days."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days ahead to check, from 0 to 365.",
                    "minimum": 0,
                    "maximum": 365,
                    "default": 7,
                }
            },
            "required": [],
        },
    },
}


