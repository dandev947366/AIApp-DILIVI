from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Assignment(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1)
    course: str
    deadline: datetime
    description: str = ""
