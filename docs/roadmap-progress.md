# AI Study Path & Career Assistant – Roadmap
*From study management to study path and career support*

> **Status Legend:**
> `[ ]` Pending / Not Started
> `[/]` In Progress (custom notation)
> `[x]` Completed

---

## 🗺️ Main Roadmap

### 1. Project Foundation
Set up the technical foundation.
- [x][Vindya] GitHub repository
- [x][Vindya] Python environment
- [x][Vindya] Project structure
- [x][Vindya] FastAPI, SQLite, SQLAlchemy
- [x][Dima] Pydantic
- [x][Vindya] .env configuration
- [x][Vindya] Basic API & database
- **Deliverable:** [x] FastAPI + SQLite basic setup

### 2. Core Application
Implement core functionality (without AI).
- [x][Dima] Student, assignment, course, deadline models
- [x][Lien] CRUD operations
- [x][Dima] Validation & error handling
- **Deliverable:** [x] Student → Assignments → Deadlines

### 3. AI Integration
Add AI for assignment analysis.
- [x][Dima] Ollama + Qwen3 4B
- [x][Vindya] Pydantic structured output
- [x][Vindya] Prompt design
- **Deliverable:** [x] AI assignment analysis service

### 4. Study Planning
Calculate workload and recommended start date.
- [x][Dima] Workload calculation
- [x][Dima] Safety buffer
- [x][Dan] Study Planner LangGraph Agent
- **Deliverable:** [x] Assignment → AI estimate → Recommended start date + AI Study Plan

### 5. User Interface + Notifications
Enable interaction via Telegram.
- [x][Dima] Telegram bot
- [x][Dima] Natural-language queries
- [x][Dima] /start, /assignments, /today, /week, /plan
- [x][Dima] Reminder notifications
- [x][Dima] APScheduler
- [x][Dan] Gradio Web UI 
- **Deliverable:** [x] Telegram assistant + reminders + Web UI

### 6. Personalization
Build student profile and track skills.
- [x][Lien] Student profile (degree, courses, skills, interests)
- [x][Lien] Assignment → skills
- [x][Lien] Skill development history
- **Deliverable:** [x] Personalized profile + skill tracking (Backend & AI)

### 7. Advanced AI (LangGraph, MCP, & Backend Architecture)
Add thesis assistant, tool calling and RAG.
- [x][Dan/Vindya] Tool calling (Calendar tool implemented and tested; Tutor MCP tools implemented)
- [x][Dan] LangGraph Agent Architecture
- [x][Dan] Tutor MCP Integration
- [x][Dan] Job Search Tool Calling
- [x][Dan] Backend Service Layer
- [x][Dan] Closed Memory Loop
- [x][Dan] Document processing
- [x][Dan] Thesis topic generation
- [x][Dan] RAG (ChromaDB + embeddings)
- **Deliverable:** [x] Advanced Agentic Backend + Tools + MCP Server

### 8. Moodle + Career Integration
Connect with external data sources.
- [x][Dima] Moodle iCal integration
- [x][Dima] Assignment sync
- [x][Dan] Career & internship data
- [x][Dan] Market information
- **Deliverable:** [x] Moodle integration + career insights

### 9. Testing & Evaluation
Validate functionality and AI performance.
- [x][Vindya] AI output accuracy (initial 4-case evaluation)
- [x][Dan] System testing
- [x][Dan] End-to-end test
- [x][Dan] Evaluation
- **Deliverable:** [x] Test results + evaluation reports

### 10. Final Demo & Documentation
Prepare final delivery.
- [x][Lien] User guide
- [x][Lien] Technical documentation
- [x][Vindya] Architecture diagram
- [x][Lien] Project report
- [x][All members] Demo presentation
- **Deliverable:** [x] Final system + documentation
