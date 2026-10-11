
from src.config import MODEL_ID
from src.models.model_client import model_client
from src.schemas.assignment import Assignment
from src.schemas.assignment_analysis import AssignmentAnalysis
from src.services.assignment_analysis_prompt import (
    build_assignment_analysis_messages,
)


def analyze_assignment(assignment: Assignment) -> AssignmentAnalysis:
    """Analyse an assignment using Ollama structured output."""

    response = model_client.chat(
        model=MODEL_ID,
        messages=build_assignment_analysis_messages(assignment),
        format=AssignmentAnalysis.model_json_schema(),
        options={
            "temperature": 0,
            "num_predict": 256,
        },
        think=False,
        stream=False,
    )

    return AssignmentAnalysis.model_validate_json(
        response.message.content
    )

