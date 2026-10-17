from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CompletionStatus = Literal[
    "completed",
    "in_progress",
    "failed",
    "withdrawn",
]


class TranscriptCourse(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    course_code: str | None = None
    course_name: str = Field(min_length=1, max_length=255)
    grade: str | None = Field(default=None, max_length=30)
    credits: float | None = Field(default=None, ge=0)
    completion_status: CompletionStatus | None = None
    completed_at: date | None = None

    @field_validator("course_code", "grade", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class TranscriptExtraction(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    degree_program: str | None = None
    institution: str | None = None
    courses: list[TranscriptCourse] = Field(default_factory=list)

    @field_validator("degree_program", "institution", mode="before")
    @classmethod
    def empty_metadata_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class TranscriptImportResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    transcript_id: int
    status: Literal["completed", "failed"]
    courses_extracted: int = Field(ge=0)
    message: str
