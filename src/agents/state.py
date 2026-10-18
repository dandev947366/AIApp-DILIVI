from typing import TypedDict, Annotated
import operator
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    student_id: int
    student_context: dict
    tasks: list[str]
    study_plan_result: str
    skill_analysis_result: str
    job_search_result: str
    general_chat_result: str
    tutor_result: str
    final_response: str
