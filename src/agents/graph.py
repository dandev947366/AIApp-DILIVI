# src/agents/graph.py
"""LangGraph: Builds the supervisor graph."""

from langgraph.graph import StateGraph, END, START

from src.agents.state import AgentState
from src.agents.memory_node import memory_node
from src.agents.supervisor import supervisor_node
from src.agents.study_planner import study_planner_node
from src.agents.skill_analyst import skill_analyst_node
from src.agents.general_chat import general_chat_node


def route_after_supervisor(state: AgentState) -> str:
    tasks = state.get("tasks", [])
    if "study_planning" in tasks:
        return "study_planner"
    elif "skill_analysis" in tasks:
        return "skill_analyst"
    return "general_chat"  # <--- DEFAULT IS NOW GENERAL CHAT


def route_after_study_planner(state: AgentState) -> str:
    if "skill_analysis" in state.get("tasks", []):
        return "skill_analyst"
    return "final_response"


def final_response_node(state: AgentState) -> dict:
    parts = []

    # Check for general chat result first
    if state.get("general_chat_result"):
        parts.append(state["general_chat_result"])

    if state.get("study_plan_result"):
        parts.append(f"📅 **Study Plan:**\n{state['study_plan_result']}")

    if state.get("skill_analysis_result"):
        parts.append(f"🎯 **Skill Analysis:**\n{state['skill_analysis_result']}")

    return {
        "final_response": (
            "\n\n---\n\n".join(parts) if parts else "No response generated."
        )
    }


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("memory", memory_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("study_planner", study_planner_node)
    graph.add_node("skill_analyst", skill_analyst_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("final_response", final_response_node)

    graph.add_edge(START, "memory")
    graph.add_edge("memory", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "study_planner": "study_planner",
            "skill_analyst": "skill_analyst",
            "general_chat": "general_chat",
        },
    )
    graph.add_conditional_edges(
        "study_planner",
        route_after_study_planner,
        {"skill_analyst": "skill_analyst", "final_response": "final_response"},
    )
    graph.add_edge("skill_analyst", "final_response")
    graph.add_edge("general_chat", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()


agent_graph = build_agent_graph()
