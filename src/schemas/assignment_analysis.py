from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AssignmentAnalysis(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)

    task_type: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    estimated_workload_hours: float = Field(ge=0)
    skills: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
