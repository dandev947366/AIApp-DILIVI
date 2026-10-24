import os
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from src.config import MODEL_ID, OLLAMA_TIMEOUT
from src.agents.state import AgentState
from src.tools.kb_updater import add_thesis_rule

if "OLLAMA_HOST" in os.environ:
    del os.environ["OLLAMA_HOST"]
if "OLLAMA_BASE_URL" in os.environ:
    del os.environ["OLLAMA_BASE_URL"]

OLLAMA_HOST_DOCKER = "http://ollama:11434"


def knowledge_manager_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    user_question = messages[-1].content if messages else ""
    clean_question = user_question.replace("ADMIN:", "").strip()

    sys_prompt = """You are DAIA's Knowledge Base Administrator.
Your ONLY job is to update the university handbook using the `add_thesis_rule` tool.
Extract the rule from the user's message and pass it to the tool.
Never answer student questions. Never invent rules."""

    llm = ChatOllama(
        model=MODEL_ID,
        base_url=OLLAMA_HOST_DOCKER,
        timeout=OLLAMA_TIMEOUT,
        temperature=0,
    )
    agent = create_agent(model=llm, tools=[add_thesis_rule], system_prompt=sys_prompt)

    try:
        response = agent.invoke({"messages": [("user", clean_question)]})
        result_text = response["messages"][-1].content
    except Exception as exc:
        result_text = f"Database update failed: {exc}"

    return {
        "thesis_result": f"**Knowledge Base Update:**\n{result_text}",
        "messages": [AIMessage(content=f"[Knowledge Manager]\n{result_text}")],
    }
