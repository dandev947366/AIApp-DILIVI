import os
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
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

    idea_keywords = ["idea", "brainstorm", "suggest", "topic"]
    is_asking_for_ideas = any(k in user_question.lower() for k in idea_keywords)

    llm = ChatOllama(
        model=MODEL_ID,
        base_url=OLLAMA_HOST_DOCKER,
        timeout=OLLAMA_TIMEOUT,
        temperature=0.1,
        num_predict=250,
    )

    if is_asking_for_ideas:
        sys_prompt = f"""You are DAIA, an expert academic advisor.
Generate 3-4 innovative thesis topics for a {profile.get('degree_program', 'University')} student.
Interests: {profile.get('interests', [])}
Skills: {skills_text}
Focus only on generating topics. Do not list any rules or processes."""
        try:
            response = llm.invoke([("system", sys_prompt), ("user", user_question)])
            result_text = response.content
        except Exception as exc:
            result_text = f"Thesis Agent Error: {exc}"
    else:
        try:
            search_results = search_thesis_guide.invoke(user_question)

            # ➕ FIX: XML-tagged prompt to force Llama 3.2 3B to adhere strictly to context (Fixes R7)
            sys_prompt = f"""You are DAIA, an academic advisor for HAMK University.
You must answer the user's question using ONLY the HAMK guidelines provided below.

<hamk_guidelines>
{search_results}
</hamk_guidelines>

RULES:
1. If the answer is explicitly in the <hamk_guidelines>, provide it clearly.
2. If the answer is NOT in the <hamk_guidelines>, you MUST output exactly: "I couldn't find that in the HAMK guidelines."
3. CRITICAL: Do NOT make up information. Do NOT use outside knowledge.
4. CRITICAL: Do NOT use the student's profile to generate generic advice. If the guidelines do not explicitly state the rules for a specific section (like Introduction, Summary, Theory), output the fallback phrase. NEVER write a sample introduction or summary based on their profile."""

            user_prompt = f"User Question: {user_question}"
            response = llm.invoke([("system", sys_prompt), ("user", user_prompt)])
            result_text = response.content
        except Exception as exc:
            result_text = f"RAG Retrieval Error: {exc}"

    return {
        "thesis_result": result_text,
        "messages": [AIMessage(content=f"[Thesis Agent]\n{result_text}")],
    }
