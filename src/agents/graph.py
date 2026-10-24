# src/agents/graph.py
"""LangGraph: Builds the supervisor graph."""

from langgraph.graph import StateGraph, END, START

from src.agents.state import AgentState
from src.agents.memory_node import memory_node
from src.agents.supervisor import supervisor_node
from src.agents.study_planner import study_planner_node
from src.agents.skill_analyst import skill_analyst_node
from src.agents.general_chat import general_chat_node
from src.agents.job_search import job_search_node
from src.agents.tutor_agent import tutor_agent_node
from src.agents.assignment_sync import assignment_sync_node

# New Agents
from src.agents.thesis_agent import thesis_agent_node
from src.agents.knowledge_manager import knowledge_manager_node


def route_after_supervisor(state: AgentState) -> str:
    tasks = state.get("tasks", [])
    if "knowledge_management" in tasks:
        return "knowledge_manager"
    elif "assignment_sync" in tasks:
        return "assignment_sync"
    elif "study_planning" in tasks:
        return "study_planner"
    elif "skill_analysis" in tasks:
        return "skill_analyst"
    elif "job_search" in tasks:
        return "job_search"
    elif "tutor_agent" in tasks:
        return "tutor_agent"
    elif "thesis" in tasks:
        return "thesis_agent"
    return "general_chat"


def route_after_study_planner(state: AgentState) -> str:
    if "skill_analysis" in state.get("tasks", []):
        return "skill_analyst"
    return "final_response"


def final_response_node(state: AgentState) -> dict:
    parts = []

    if state.get("general_chat_result"):
        parts.append(state["general_chat_result"])

    if state.get("thesis_result"):
        parts.append(f"🎓 **Thesis Advisor:**\n{state['thesis_result']}")

    if state.get("study_plan_result"):
        parts.append(f"📅 **Study Plan:**\n{state['study_plan_result']}")

    if state.get("skill_analysis_result"):
        parts.append(f"🎯 **Skill Analysis:**\n{state['skill_analysis_result']}")

    if state.get("tutor_result"):
        parts.append(f"🎓 **Tutor:**\n{state['tutor_result']}")

    return {
        "final_response": (
            "\n\n---\n\n".join(parts) if parts else "No response generated."
        )
    }


def build_agent_graph():
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("memory", memory_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("assignment_sync", assignment_sync_node)
    graph.add_node("study_planner", study_planner_node)
    graph.add_node("skill_analyst", skill_analyst_node)
    graph.add_node("job_search", job_search_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("tutor_agent", tutor_agent_node)

    # Register the new RAG nodes
    graph.add_node("thesis_agent", thesis_agent_node)
    graph.add_node("knowledge_manager", knowledge_manager_node)

    graph.add_node("final_response", final_response_node)

    # Edges
    graph.add_edge(START, "memory")
    graph.add_edge("memory", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "knowledge_manager": "knowledge_manager",
            "assignment_sync": "assignment_sync",
            "study_planner": "study_planner",
            "skill_analyst": "skill_analyst",
            "job_search": "job_search",
            "general_chat": "general_chat",
            "tutor_agent": "tutor_agent",
            "thesis_agent": "thesis_agent",
        },
    )

    graph.add_conditional_edges(
        "study_planner",
        route_after_study_planner,
        {"skill_analyst": "skill_analyst", "final_response": "final_response"},
    )

    # New edge: after assignment_sync, go to tutor_agent
    graph.add_edge("assignment_sync", "tutor_agent")

    # All other nodes go to final_response
    graph.add_edge("skill_analyst", "final_response")
    graph.add_edge("general_chat", "final_response")
    graph.add_edge("job_search", "final_response")
    graph.add_edge("tutor_agent", "final_response")

    # Edges for the RAG nodes
    graph.add_edge("thesis_agent", "final_response")
    graph.add_edge("knowledge_manager", "final_response")

    graph.add_edge("final_response", END)

    return graph.compile()


agent_graph = build_agent_graph()
