# DAIA — Agent Graph Architecture

## 1. Overview

DAIA uses a **Supervisor-Worker architecture** built on `langgraph`. The graph does not route with a single monolithic prompt; instead, it uses a central `Supervisor` node that acts as an intelligent dispatcher, routing the user's request to one or more specialized worker nodes.

### Core Architectural Rules

1. **Memory First:** Every request passes through the `Memory Node` exactly once at the start. This loads the student's profile, skills, courses, and Moodle assignments into `state["student_context"]`. Workers **never** query the database for core student data directly.
2. **Supervisor Routing:** The `Supervisor` uses deterministic regex shortcuts (e.g., "homework", "update my degree") and an LLM fallback to populate `state["tasks"]`.
3. **Aggregation:** Workers never talk to the UI directly. They append their result to the state (e.g., `study_plan_result`). The `Final Response Node` concatenates these results into a single markdown response.

---

## 2. Graph Topology
![LangGraph Topology](../imgs/3-langgraph-topology.png)
