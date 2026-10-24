# DAIA (Digital Artificial Intelligent Assistant) - AI Study Path and Career Assistant

Group project for the **Development of AI Applications** course

A local, privacy-preserving AI assistant that helps university students plan their studies and connect daily coursework to longer-term academic and career goals.

## Team members

- Member 1 Dmytro Krempovskyy (amk1002944@student.hamk.fi)
- Member 2: Vindya Nukulasooriya (amk1001863@student.hamk.fi)
- Member 3: Lien Pham (amk1002343@student.hamk.fi)
- Member 4: Dan Le (dan23001@student.hamk.fi)

## 1. Problem

### 1.1 Intended users

University students who:
1. Manage coursework, assignments, and deadlines through Moodle.
2. Support students in planning their longer-term study and career paths
3. Want a private, local alternative to cloud AI assistants

### 1.2 Problem statement

Students can be confused with a maxtrix of deadline relating to individual assignments, group projects, quiz, exams,..They can see when assignments or submissions are due, but it can be difficult to decide when they should start working on them.

Different assignments require different amounts of time and effort. Starting too late can lead to rushed work and missed deadlines.

The problem is not only remembering tasks, but also understanding what to do next and how current study activities connect to longer-term academic and career goals. Our project aims to develop an AI-powered student assistant that can support students across different stages of their study path:
* Managing and understanding homework, individual assignments and group projects.
* Organizing academic priorities and deadlines.
* Generating thesis topic suggestions based on the student's major, interest, and skills.
* Connecting study experience with possible career directions.
* Supporting internship and job-market exploration
* Learns durable preferences from natural-language chat
* Authenticate users and isolates their data.

The project therefore moves from a simple task-management assistant toward a more comprehensive study-to-career support system.


### 1.3 Why AI is appropriate

Assignment descriptions contain unstructured natural language and can vary significantly between courses.

An LLM can interpret the assignment description, identify the type and complexity of the task, and produce an estimated workload.

Traditional fixed rules would have difficulty handling the different ways assignments are described.

Furthermore, students have not yet defined a graduation thesis topic that aligns with their skills, interests and field of study. For example, a student may ask: "I study Computer Applications and I am interested in Python, SQL and AI. What thesis topics could fit my interest?"

These tasks require understanding context, identifying relationships between information, and generating personalized suggestions.

In this scenario, LLM is useful for generating personalized suggestions connecting student's interest, strength and study goals.

In terms of further career goals, it can generate some research about job market, internship opportunities that helps student have insight about market demand.

AI therefore adds a reasoning and personalization layer on top of traditional student-management functionality.

### 1.4 Solution

The AI Study Deadline Assistant helps students plan when to start their assignments.

The application reads assignment information, uses an AI model to estimate the workload, and calculates a recommended starting time before the deadline.

Example:

Assignment description  
- AI workload estimate  
- Recommended start date  
- Student reminder

The solution can be viewed as three connected levels:
1. Study management including: understanding assignments, organize homework and deadlines, identify priorities and make reminder by synchronizing Moodle iCal, estimates workload, recommends start dates.
2. Thesis and study planning: based on study major, skills, interests and previous academic activities to suggest possible thesis areas, thesis topic ideas, research direction, technologies or skills that may be relevant.
3. Career exploration: as a future extension, the assistant can connect the student's profile with current job-market information to support internship research, career development planning.
4. Adaptive tutor: 46 tool MCP server that tracks mastery, routes learning, and diagnoses misconceptions.

### 1.5 Main user workflow

1. **Get assignment:** The application receives assignment information and its deadline.
2. **Process assignment:** The service layer validates and prepares the assignment description.
3. **AI analysis:** The local LLM analyses the assignment and returns a structured workload estimate.
4. **Planning:** The application calculates a recommended start time using the estimate, deadline, and a safety buffer.
5. **User output:** The student sees the assignment, estimated workload, and recommended start time.
6. **Study-profile connection:** The system compares the skills and topics identified from assignment with student's study profile, interests, previous projects.
7. **Thesis topic generation:** Based on the accumulated study information, the AI suggests possible thesis areas or topics that are related to the student's major, skills and completed assignments.
8. **Career and thesis output:** student receives a connected set of recommendations showing how current assignments can contribute to longer-term goals, for example: Assignment → Skills → Thesis idea → Career skills → Seeking for internship/Workplacement.
9. **User reaction:** student can accept, reject, or refine the suggestions, allowing the AI to generate more relevant thesis and internship recommendations.

### 1.6 Scope
| Phase | Feature | Status |
| 1 | Moodle iCal -> SQLite | ✅ |
| 2 | Deterministic DB tools | ✅ |
| 3 | LangGraph agents (memory, supervisor, planner, analyst) | ✅ |
| 4 | Conversation history + memory extraction | ✅ |
| 5 | Authentication, login/logout, session cahe | ✅ |
| 6 | Tutor MCP Server, adaptive learning tools | ✅ |
| 7 | Career assistant + live job-market data | ✅ |
| 8 | Telegram bot intergration | ✅ |
| 9 | RAG career advisor | 🚧 planned |

### 1.7 Features
[Features](docs/FEATURES.md)

#  2. Architecture

[Architecture](docs/architecture.md)

## 2.1 System diagram
Initial architecture:

![AI Study Deadline Assistant Architecture](docs/DAIA_architecture.svg)

> **Core Architectural Rule:** The user interface does not communicate directly with the model or Ollama. Model interaction passes through the application/service layer, which enforces authentication, context loading, memory updates, and caching.

System Overview:

![System Overview](imgs/1-system-overview.png)


LangGraph Topology
![LangGraph Topology](imgs/3-langgraph-topology.png)

See Agent graph logic:
[Agent graph](docs/AGENT_GRAPH.md)

## 2.2 Authentication & session cache
- **Register / Login / Logout:** - bcrypt-hashes passwords, HTTP-only cookies, sessions stired in SQLite.
- **Session store** (SQLite) - authoritative, survives restarts, TTL 8 h.
- **Session cache** (in-memory, `TTLCache1) - performmance only:
    + student_context cached 60s (skips Memory Node's 5 SQL queries),
    + answers cahed 300 s (skips the LLM on repeat questions),
    + invalidated on logoit and on profile update.

## 2.3 Data flow 

![Data Flow](imgs/2-data-flow.png)

## 2.4 Closed memory loop
After every response, the LLM extracts durable preferences ("I prefer studying in the evening") and merge them into `student_profiles`. The next request's Memory Node sees the updated profile - this is how DAIA learns.

## 2.5 Project structure

```text
DAIA/
├── app/
│   ├── ui.py                      # Gradio UI + login/logout screens
│   ├── bot.py                     # Telegram integration
│   └── main.py                    # Application entry point
├── src/
│   ├── agents/                    # LangGraph nodes + topology
│   │   ├── graph.py
│   │   ├── memory_node.py
│   │   ├── supervisor.py
│   │   └── ...                    # specialist nodes
│   ├── services/                  # Application/service layer
│   │   ├── agent_service.py       # Main orchestration (chat entry)
│   │   ├── auth_tokens.py         # Session token validation (SQLite)
│   │   ├── student_auth.py        # Register / login / logout
│   │   ├── moodle_sync_service.py # iCal fetch / parse / upsert
│   │   └── transcript_service.py  # PDF extraction & validation
│   ├── mcp/                       # Model Context Protocol clients
│   │   ├── jobicy.py              # Jobicy search + scoring
│   │   └── tutor_mcp.py           # stdio client for 46-tool Tutor MCP
│   ├── tools/                     # Deterministic DB queries
│   │   ├── assignments.py
│   │   ├── profile.py
│   │   ├── skills.py
│   │   └── jobs_db.py
│   ├── memory/                    # Chat history + preference extraction
│   │   ├── conversation_memory.py
│   │   ├── extraction.py
│   │   └── preferences.py
│   ├── models/                    # SQLAlchemy ORM models
│   └── schemas/                   # Pydantic schemas for validation
├── docs/                          # Architecture, reports, and guides
├── data/
│   └── student_context.db         # SQLite database
├── docker/                        # Entrypoint + wait-for scripts
├── tests/                         # Unit + integration tests
└── student_context.db             # Local root DB (for quick testing)
```
## 2.6 Tutor MCP Server - 46 tools in 6 categories
The tutor is an adtaptive, mastery-based learning system exposed as an MCP server. The LLM selects tools by name; all pedagogical rules - what counts as mastery, when to reassess, which misconceptions to surface - are enforced deterministically in code. This prevents the LLM from "hallucunating progress" or skipping prerequisites.
Six tool categories:
1. Curriculum: 12 tools : versioned domains, concepts, prerequisites. Cirriculum changes never destroy learner progress.
2. Learning cycle: 6 tools: routes the next optimal activity, exposes the session plan for learner negotiation, surfaces alerts
3. Assessment: 13 tools: Freezes tasks and rubics before exposure; records evidence from recall, transfer, and self-calibration.
4. Learner model: 7 tools: BKT/FSRS mastery estimates, affects, preferences, if-then practice commitments.
5. Analytics: 4 tools: Per-concept progress, retention alert, and replayable decision snapshots.
6. Availability: 3 tools: Timezone, DND windows, consent-gated notifications.
**Three design principles that matter most:** 
* Versioned curriculum: Every curriculum edit is an immutable revision checked against 'expected_version'; stale writers are rejected. Learners never lose progress when the domain is reorganised.
* Frozen assessments: 'prepare_assessment_attempt' locks the tak and rubric before the learner sees it. Grading cannot drift after the fact.
* Replayable decision: 'get_decision_replay_summary' reconstructs every pedagogical choice from stored snapshots - the explainability layer that distinguishes DAIA from blacj-box chatbot and aligns with EU AI Act transparency expectations.

| Full tools reference (schemas, BKT/FSRS calibration): [Tutor tools](docs/Tutor-MCP.md)


# 3. Technologies

| Layer | Technology | Rationale |
|---|---|---|
| Runtime | Docker Desktop + Compose | Reproducible, cross-platform |
| LLM server | Ollama | Local inference, no cloud |
| Default model | `llama3.2:3b` | Runs on laptop; strong instruction-following |
| Alternative models | `qwen2.5:7b`, `llama3.1:8b` | Larger context or reasoning |
| Backend | Python 3.11 | Ecosystem for AI + web |
| Web UI | Gradio | Fast prototyping, built-in auth hooks |
| Auth | `passlib[bcrypt]` | Industry-standard hashing |
| Cache | `cachetools.TTLCache` | Simple, dependency-light |
| Orchestration | LangGraph | Explicit state machine over LLM calls |
| Tool protocol | MCP (Model Context Protocol) | Standard tool calling |
| DB | SQLAlchemy + SQLite | Zero-config, portable |
| Config | `python-dotenv`, Pydantic | Validation + reproducibility |
| Integrations | Moodle iCal, Jobicy API, Telegram Bot API | Real-world data |
| Learning models | BKT, FSRS | Mastery + retention estimation |

**Model selection rationale.** `llama3.2:3b` runs on a laptop with 8 GB RAM,
follows instructions reliably, and handles the structured extraction required
by `extract_memory_updates` and the MCP tool schemas. Larger models
(`qwen2.5:7b`, `llama3.1:8b`) are tested alternatives for users with more RAM.

---


## Model

- **Model used:** Llama3.2:3b (`llama3.2:3b`)
- **Selection rationale:** Llmama3.2:3b runs on laptop, follows instructions well, and handles structured extraction. Alternatives tested: `qwen2.5:7b`, `llmama3.1:8b`. 

# 4. Installation and Running
See Setup instruction:

[SET UP](SETUP.md)

# 5. Testing Rsults
## 5.1 Automated tests
| Test file | Coverage |
|---|---|
| `test_calendar_backend.py` | iCal parsing, sync idempotency, date filters |
| `test_agent_tools.py` | Assignment queries, profile merge, skill upsert |
| `test_memory_extraction.py` | Preference extraction, invalid-value rejection |
| `test_auth.py` | Register / login / logout, session expiry, rate limit |
| `test_tutor_mcp.py` | Curriculum versioning, frozen assessments, mastery routing |
| `test_career_matcher.py` | Job search, scoring, filter correctness |

## 5.2 Key verified behaviors
| Behaviour | Result |
|---|---|
| Moodle sync twice → no duplicates | ✅ `events_added=0`, `events_updated=N` |
| "I prefer studying in the evening" → profile update | ✅ `preferred_study_time='evening'` |
| Unauthenticated request / revoked session | ✅ `401` returned |
| Login → valid cookie + session row | ✅ |
| Logout → session revoked + cache cleared | ✅ |
| Repeat question within cache TTL | ✅ < 100 ms, no LLM call |
| Curriculum revision preserves progress | ✅ Versioned, stale writer rejected |
| Assessment frozen before exposure | ✅ Rubric immutable |
| Two concurrent users → isolated context | ✅ No cross-talk |

## 5.3 Performance

| Scenario | Time |
|---|---|
| Cold question (LLM call) | 6–20 s |
| Repeat question (cache hit) | < 100 ms |
| Memory Node from cache | < 50 ms |
| Tutor routing (`get_next_activity`) | < 100 ms |

## 5.4 Manual verification

- `docker compose ps` → all containers `healthy`
- Backend log: `Ollama is ready with model 'llama3.2:3b'.`
- UI reachable at `http://localhost:7860`
- Telegram bot responds to `/start`, `/login`, `/create_account`

# 6. Known limitations

- AI workload estimates may be inaccurate; assignment text may be insufficient.
- Assignment descriptions may not contain enough information for a reliable estimate.
- Actual working time differs between students.
- Moodle/iCal data availability may vary.
- Recommended start times should be treated as planning assistance rather than guaranteed estimates.
- Thesis topic suggestions are currently based mainly on the information provided by the student and the LLM's existing knowledge. They do not necessarily represent the current job market.
- The current system does not automatically verify whether suggested thesis topics or career opportunities are available or relevant at a specific university, company, or location.
- AI-generated recommendations should be treated as decision-support and planning assistance rather than guaranteed workload estimates, thesis recommendations, or career outcomes.
- Telegram bot requires user-provided token
- Session cache is per-process (restart clears it; sessions survive in SQLite)
- The tutor MCP's mastery model (BKT/FSRS) is calibrated on synthetic data; production calibration is future work

# 7. Future improvements: Career Path

DAIA's architecture is designed to grow beyond academic planning. The same components - local LLM, versioned curriculum, MCP tools, privay-first deployment - map naturally to career-oriented features planned for later phases.

Possible future extensions:

- Student feedback after completing an assignment
- Personalized workload estimates
- Natural-language commands such as "What's due this week?"
- Snoozing or rescheduling reminders
- Expand the persistent student profile with courses, skills, interests, projects, thesis preferences, and career goals.
- Improve personalization by comparing assignments and acquired skills over time.
- Integrate current job-market data or job-search APIs to support internship and job exploration.
- Add stronger privacy and security mechanisms for storing and processing student information.

# 8. Documentation map

| Document | Audience | Contents |
|---|---|---|
| **README.md** (this file) | Everyone | Overview, architecture, technologies, install & run, testing, limitations, future development |
| `SETUP.md` | New users, operators | Step-by-step install, OS-specific notes, troubleshooting |
| `docs/TUTOR_MCP.md` | AI engineers | Full 46-tool reference, tool schemas, BKT/FSRS calibration, extension points |
| `docs/AGENT_GRAPH.md` | AI engineers, Developers | LangGraph topology, routing logic, node reference, execution flows, extension checklist |
| `docs/DATABASE.md` | Developers, Operators | Table schemas, indexes, ER diagram, migrations, backup & restore, known limitations |
| `docs/FEATURES.md` | Product, Users | Comprehensive list of product features and capabilities |
| `docs/architecture.md` | Developers, Architects | System diagrams and architectural design decisions (accompanies `DAIA_architecture.svg`) |
| `docs/roadmap-progress.md` | Stakeholders | Current progress against the roadmap (`road-map.png`) |
| `evaluation/README.md` | QA, Researchers | Assignment analysis accuracy test cases, evaluation methodology, and results |
