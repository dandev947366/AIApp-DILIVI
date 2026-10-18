import os
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

from src.config import MODEL_ID, OLLAMA_TIMEOUT
from src.agents.state import AgentState
from src.mcp.tutor_mcp import get_tutor_tools

# Bulletproof Docker network fix
if "OLLAMA_HOST" in os.environ:
    del os.environ["OLLAMA_HOST"]
if "OLLAMA_BASE_URL" in os.environ:
    del os.environ["OLLAMA_BASE_URL"]

OLLAMA_HOST_DOCKER = "http://ollama:11434"


def tutor_agent_node(state: AgentState) -> dict:
    """Node that handles adaptive tutoring via Tutor MCP tools."""
    messages = state.get("messages", [])
    user_messages = [m for m in messages if getattr(m, "type", None) == "human"]
    user_question = (
        user_messages[-1].content
        if user_messages
        else (messages[-1].content if messages else "")
    )

    context = state.get("student_context", {})
    upcoming = context.get("upcoming_assignments", [])
    overdue = context.get("overdue_assignments", [])

    # 1. Load MCP tools
    tutor_tools = get_tutor_tools()
    if not tutor_tools:
        fallback = (
            "The adaptive tutoring system is currently offline. Please try again later."
        )
        return {
            "tutor_result": fallback,
            "messages": [AIMessage(content=f"[Tutor Agent]\n{fallback}")],
        }

    # 2. Format assignments for the prompt
    if upcoming or overdue:
        assignments_text = "### CURRENT MOODLE ASSIGNMENTS ###\n"
        for a in overdue:
            assignments_text += (
                f"- [OVERDUE] {a['title']} ({a['course']}) | Due: {a['deadline']}\n"
            )
        for a in upcoming:
            assignments_text += f"- {a['title']} ({a['course']}) | Due: {a['deadline']} | {a['days_until']} days left\n"
        assignments_text += "################################\n"
    else:
        assignments_text = "### CURRENT MOODLE ASSIGNMENTS ###\nNo upcoming or overdue assignments found.\n################################\n"

    print(
        f"[TUTOR AGENT] Injecting assignments into user prompt:\n{assignments_text}",
        flush=True,
    )

    # 3. Initialize LLM
    llm = ChatOllama(
        model=MODEL_ID,
        base_url=OLLAMA_HOST_DOCKER,
        timeout=OLLAMA_TIMEOUT,
        temperature=0,
    )

    # 4. Create the modern LangChain 1.0+ agent
    agent = create_agent(
        model=llm,
        tools=tutor_tools,
        system_prompt="""You are DAIA, an AI study assistant with access to an adaptive Tutor MCP server.
Your goal is to help the student learn using spaced-repetition and mastery-based methods.

CRITICAL RULES:
- You DO have access to the student's Moodle assignments. The data is injected in the user's message.
- NEVER say "I don't have access" or "I am a large language model". You are DAIA, their personal tutor.
- If the user asks about assignments, read the list provided in their message and tell them what they need to study.
- If they ask for help with a specific assignment, use the `init_domain` tool to create a study plan for the concepts in that assignment.

Follow this workflow for tutoring:
1. **Check Alerts**: At the start of a session, call `get_pending_alerts`.
2. **Find Next Activity**: Use `get_next_activity` to determine the student's next optimal task.
3. **Record Results**: After the student completes an activity, call `record_interaction` to save their progress.
   - Always include a fresh `idempotency_key` (e.g., a UUID string) for each new interaction.
""",
    )

    # Inject the assignments directly into the user's question
    enhanced_user_question = f"""
[SYSTEM CONTEXT: Here is the student's current Moodle data. You MUST use this data.]
{assignments_text}
[END SYSTEM CONTEXT]

User Question: {user_question}
"""

    try:
        # Invoke using the modern message format
        response = agent.invoke({"messages": [("user", enhanced_user_question)]})
        result_text = response["messages"][-1].content
    except Exception as exc:
        print(f"[TUTOR AGENT] Error: {exc}")
        result_text = f"An error occurred in the tutor system: {exc}"

    # ─────────────────────────────────────────────────────────
    # PYTHON INTERCEPTOR: If the LLM still hallucinates, force
    # the correct response using the Python data.
    # ─────────────────────────────────────────────────────────
    hallucination_phrases = [
        "don't have direct access",
        "do not have direct access",
        "as a large language model",
        "i don't have access to your personal",
        "i cannot access your personal",
        "can you please provide me with",
        "i won't have direct access",
    ]

    if any(phrase in result_text.lower() for phrase in hallucination_phrases):
        print(
            "[TUTOR AGENT] LLM hallucination detected! Overriding with deterministic response."
        )

        if upcoming or overdue:
            result_text = "Here are your current Moodle assignments:\n\n"
            for a in overdue:
                result_text += f"- ⚠️ **{a['title']}** ({a['course']}) - OVERDUE (Due: {a['deadline']})\n"
            for a in upcoming:
                result_text += f"- 📝 **{a['title']}** ({a['course']}) - Due in {a['days_until']} days\n"

            result_text += "\nWhich of these would you like to prepare for? I can help you break down the concepts."
        else:
            result_text = "I checked your Moodle sync, but I don't see any upcoming assignments. Try re-syncing your calendar in the Account section."

    return {
        "tutor_result": result_text,
        "messages": [AIMessage(content=f"[Tutor Agent]\n{result_text}")],
    }
