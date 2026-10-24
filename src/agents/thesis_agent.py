import os
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from src.config import MODEL_ID, OLLAMA_TIMEOUT
from src.agents.state import AgentState
from src.tools.rag_search import search_thesis_guide

if "OLLAMA_HOST" in os.environ:
    del os.environ["OLLAMA_HOST"]
if "OLLAMA_BASE_URL" in os.environ:
    del os.environ["OLLAMA_BASE_URL"]

OLLAMA_HOST_DOCKER = "http://ollama:11434"


def thesis_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    user_question = messages[-1].content if messages else ""

    context = state.get("student_context", {})
    profile = context.get("profile", {})
    skills = context.get("skills", [])

    skills_text = (
        ", ".join([s["skill_name"] for s in skills]) if skills else "None recorded"
    )

    sys_prompt = f"""You are DAIA, an expert academic advisor.
Your job is to help the student with their thesis.

Student Profile:
- Degree: {profile.get('degree_program', 'Unknown')}
- Interests: {profile.get('interests', [])}
- Skills: {skills_text}
- Career Goals: {profile.get('career_goals', {})}

Instructions:
1. If the user asks for thesis topic ideas, generate 3-4 innovative topics based on their profile.
2. If the user asks about rules, deadlines, or guidelines, you MUST use the `search_thesis_guide` tool to get the factual answer.
3. Never invent university rules. Only use the tool."""

    llm = ChatOllama(
        model=MODEL_ID,
        base_url=OLLAMA_HOST_DOCKER,
        timeout=OLLAMA_TIMEOUT,
        temperature=0.7,
    )
    agent = create_agent(
        model=llm, tools=[search_thesis_guide], system_prompt=sys_prompt
    )

    try:
        response = agent.invoke({"messages": [("user", user_question)]})
        result_text = response["messages"][-1].content
    except Exception as exc:
        result_text = f"Thesis Agent Error: {exc}"

    return {
        "thesis_result": result_text,
        "messages": [AIMessage(content=f"[Thesis Agent]\n{result_text}")],
    }
