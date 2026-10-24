
# DAIA — System Architecture

> **Audience:** Developers, architects, and reviewers.
> **Scope:** High-level system design, authentication, data flow, memory loop, and component interactions.
> **Related Docs:** [Agent Graph](AGENT_GRAPH.md) · [Database Schema](DATABASE.md) · [Tutor MCP](Tutor-MCP.md)

---

## 1. System Diagram

**Initial architecture:**
![AI Study Deadline Assistant Architecture](DAIA_architecture.svg)

> **Core Architectural Rule:** The user interface does not communicate directly with the model or Ollama. Model interaction passes through the application/service layer, which enforces authentication, context loading, memory updates, and caching.

**LangGraph Topology:**
*(See [Agent Graph](AGENT_GRAPH.md) for detailed node logic and routing rules, including the new Thesis Agent).*

---

## 2. Authentication & Session Cache

**Session store (SQLite)**
- **Authoritative** source of truth. Survives restarts. TTL: 8 hours.

**Session cache (in-memory, `TTLCache`)**
- `student_context`: 60s TTL (skips Memory Node).
- Chat answers: 300s TTL (skips LLM on repeat questions).
- **Invalidation:** Cleared on logout and on profile update.

---

## 3. Data Flow & Persistence

DAIA uses a **dual-database architecture**:
1. **SQLite:** Relational data (Students, Courses, Deadlines, Profiles).
2. **ChromaDB:** Vector data (University Thesis Rules & AI Guidelines).

**Step-by-step (One Request):**
1. **Browser → `require_session()`** — validate session.
2. **`agent_service`** — hands off to LangGraph.
3. **Memory Node** — loads SQLite data (Profile, Moodle) into `state`.
4. **Supervisor** — routes to the appropriate agent.
5. **Agent Execution:**
   *   *Normal Agents* (Planner, Tutor): Use the LLM and context.
   *   *Thesis Agent (RAG)*: Queries **ChromaDB** via `nomic-embed-text` to retrieve factual university rules.
   *   *Knowledge Manager (Admin)*: Writes new rules to ChromaDB.
6. **Save messages** — persist to `conversation_messages` in SQLite.
7. **Return** — stream to UI.

---

## 4. The RAG Pipeline (Thesis Agent)

DAIA features a localized **Retrieval-Augmented Generation (RAG)** system to prevent the LLM from hallucinating university rules.

### 4.1 Ingestion (Startup)
1. On first boot, `src/rag/ingest.py` reads `data/rag/thesis_rules.txt`.
2. The text is chunked (size 300) and embedded using `nomic-embed-text` (via Ollama).
3. Vectors are persisted to `/app/data/chroma_db`.

### 4.2 Retrieval (Runtime)
1. Student asks: *"What are the rules for my thesis?"*
2. `Thesis Agent` calls `search_thesis_guide` tool.
3. The tool performs a semantic similarity search in ChromaDB (`k=2`).
4. The retrieved text is injected into a strict prompt: *"Answer using ONLY this Context."*

### 4.3 Agentic Updates (Admin)
1. Admin types: *"ADMIN: Update deadline to Dec 15th."*
2. Supervisor routes to `Knowledge Manager`.
3. The agent calls `add_thesis_rule`, which appends to the `.txt` file and embeds the new rule directly into ChromaDB.

---

## 5. Closed Memory Loop

After every response, the LLM extracts durable preferences (e.g., *"I prefer studying in the evening"*) and merges them into `student_profiles` in SQLite. The next request's Memory Node sees the updated profile — **this is how DAIA learns.**