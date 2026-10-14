
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssignmentAnalysis(BaseModel):
    """Structured AI analysis of a student's assignment."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    task_type: str = Field(
        min_length=1,
        description="Type of assignment, such as essay, coding, or research.",
    )

    difficulty: Literal["easy", "medium", "hard"] = Field(
        description="Estimated assignment difficulty.",
    )

    estimated_workload_hours: float = Field(
        ge=0,
        description="Estimated hours required to complete the assignment.",
    )

    skills: list[str] = Field(
        description="Skills needed to complete the assignment.",
    )

    topics: list[str] = Field(
        description="Main subject areas covered by the assignment.",
    )
