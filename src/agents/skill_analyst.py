"""Skill Analyst: Analyzes skills and identifies gaps."""

import os
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from src.config import MODEL_ID, OLLAMA_TIMEOUT
from src.agents.state import AgentState

# ✅ Bulletproof Docker network fix for LangChain
if "OLLAMA_HOST" in os.environ:
    del os.environ["OLLAMA_HOST"]
if "OLLAMA_BASE_URL" in os.environ:
    del os.environ["OLLAMA_BASE_URL"]

OLLAMA_HOST_DOCKER = "http://ollama:11434"

llm = ChatOllama(
    model=MODEL_ID, base_url=OLLAMA_HOST_DOCKER, timeout=OLLAMA_TIMEOUT, temperature=0.3
)

SYSTEM_PROMPT = """You are a Skill Analyst agent. Review skills against career goals.
Identify gaps. Recommend concrete actions. Keep response under 300 words."""


def skill_analyst_node(state: AgentState) -> dict:
    context = state.get("student_context", {})
    skills = context.get("skills", [])
    profile = context.get("profile", {})

    skills_text = (
        "\n".join(f"- {s['skill_name']} ({s['proficiency'] or '?'}/5)" for s in skills)
        or "No skills recorded."
    )
    career_goals = profile.get("career_goals", {})
    interests = ", ".join(profile.get("interests", [])) or "Not specified"

    user_prompt = f"""Skills:\n{skills_text}\n\nCareer goals: {career_goals}\nInterests: {interests}\n\nAnalyze gaps and recommend next steps."""

    response = llm.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )

    return {
        "skill_analysis_result": response.content,
        "messages": [AIMessage(content=f"[Skill Analyst]\n{response.content}")],
    }
