from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class StudentInfo(BaseModel):
    """
    A Pydantic model representing student information.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: int | str | None = None
    name: str | None = None
    email: str | None = None
    enrollment_date: datetime | None = None
    is_active: bool | None = None

class CourseInfo(BaseModel):
    """
    A Pydantic model representing course information.
    """

    model_config = ConfigDict(extra="forbid")

    course_id: str = Field(..., description="The unique identifier for the course.")
    title: str = Field(..., description="The title of the course.")
    description: str = Field(..., description="A brief description of the course.")
    credits: int = Field(..., description="The number of credits for the course.")
    instructor: str = Field(..., description="The name of the instructor for the course.")

class AssignmentInfo(BaseModel):
    """
    A Pydantic model representing assignment information.
    """

    model_config = ConfigDict(extra="forbid")

    assignment_id: str = Field(..., description="The unique identifier for the assignment.")
    title: str = Field(..., description="The title of the assignment.")
    due_date: datetime = Field(..., description="The due date for the assignment.")
    max_score: float = Field(..., description="The maximum score achievable for the assignment.")
    course_id: str = Field(..., description="The unique identifier for the course associated with the assignment.")
    status: str = Field(..., description="The current status of the assignment (e.g., 'pending', 'submitted', 'graded').")

class CalendarEventInfo(BaseModel):
    """
    A Pydantic model representing calendar event information.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., description="The unique identifier for the calendar event.")
    title: str = Field(..., description="The title of the calendar event.")
    start_time: datetime = Field(..., description="The start time of the calendar event.")
    end_time: datetime = Field(..., description="The end time of the calendar event.")
    location: str = Field(..., description="The location where the calendar event will take place.")
    description: str = Field(..., description="A brief description of the calendar event.")
    source: str = "moodle_ical"  # Default source for calendar events

class GradeInfo(BaseModel):
    """
    A Pydantic model representing grade information.
    """

    model_config = ConfigDict(extra="forbid")

    assignment_id: str = Field(..., description="The unique identifier for the assignment.")
    student_id: str = Field(..., description="The unique identifier for the student.")
    score: float = Field(..., description="The score achieved by the student for the assignment.")
    feedback: str = Field(..., description="Feedback provided by the instructor for the assignment.")

class StudentPreferences(BaseModel):
    """
    A Pydantic model representing student preferences.
    """

    model_config = ConfigDict(extra="forbid")
    study_hours_per_week: float | None = None
    interests: list[str] = Field(default_factory=list, description="A list of the student's interests.")
    career_goals: dict[str] = Field(default_factory=list, description="A dictionary containing the student's career goals.")

class ContextMetadata(BaseModel):
    """
    A Pydantic model representing metadata for the student context.
    """

    model_config = ConfigDict(extra="forbid")

    last_updated: datetime |None = None
    source: str = "local"
    source_status: dict[str, Any] = Field(default_factory=dict, description="A dictionary containing information about the source of the student context data.")

class StudentContext(BaseModel):
    """
    A Pydantic model representing the complete student context.
    """

    model_config = ConfigDict(extra="forbid")

    student_info: StudentInfo = Field(default_factory=StudentInfo, description="Basic information about the student.")
    courses: list[CourseInfo] = Field(default_factory=list, description="A list of courses the student is enrolled in.")
    assignments: list[AssignmentInfo] = Field(default_factory=list, description="A list of assignments for the student.")
    calendar_events: list[CalendarEventInfo] = Field(default_factory=list, description="A list of calendar events for the student.")
    grades: list[GradeInfo] = Field(default_factory=list, description="A list of grades for the student's assignments.")
    preferences: StudentPreferences = Field(default_factory=StudentPreferences, description="The student's preferences and interests.")
    metadata: ContextMetadata = Field(default_factory=ContextMetadata, description="Metadata about the student context.")