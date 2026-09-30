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
- [x] GitHub repository
- [x] Python environment
- [x] Project structure
- [ ] FastAPI, SQLite, SQLAlchemy
- [][Dima] Pydantic
- [x] .env configuration
- [ ][Dima] Basic API & database
- **Deliverable:** [ ] FastAPI + SQLite basic setup

### 2. Core Application
Implement core functionality (without AI).
- [ ][Dima] Student, assignment, course, deadline models
- [ ] CRUD operations
- [ ] Study availability
- [ ][Dima] Validation & error handling
- **Deliverable:** [ ] Student → Assignments → Deadlines

### 3. AI Integration
Add AI for assignment analysis.
- [_][Dima] Ollama + Qwen3 4B
- [_][Vindya] Pydantic structured output
- [_][Vindya] Prompt design
- [ ] Task type, difficulty, workload, skills, topics
- **Deliverable:** [ ] AI assignment analysis service

### 4. Study Planning
Calculate workload and recommended start date.
- [ ][Dima] Workload calculation
- [ ] Deadline & priority
- [ ] Safety buffer
- [ ] Study schedule
- **Deliverable:** [ ] Assignment → AI estimate → Recommended start date

### 5. User Interface + Notifications
Enable interaction via Telegram.
- [ ][Dima] Telegram bot
- [ ][Dima] Natural-language queries
- [ ][Dima] /start, /assignments, /today, /week, /plan
- [ ][Dima] Reminder notifications
- [ ] APScheduler
- **Deliverable:** [ ] Telegram assistant + reminders

### 6. Personalization
Build student profile and track skills.
- [ ] Student profile (degree, courses, skills, interests)
- [ ] Assignment → skills
- [ ] Skill development history
- **Deliverable:** [ ] Personalized profile + skill tracking

### 7. Advanced AI
Add thesis assistant, tool calling and RAG.
- [ ] Thesis topic generation
- [ ] Tool calling (get_assignments, get_profile, etc.)
- [ ] RAG (ChromaDB + embeddings)
- [ ] Document processing
- **Deliverable:** [ ] Thesis assistant + tools + RAG

### 8. Moodle + Career Integration
Connect with external data sources.
- [ ][Dima] Moodle iCal integration
- [ ][Dima] Assignment sync
- [ ] Career & internship data
- [ ] Market information
- **Deliverable:** [ ] Moodle integration + career insights

### 9. Testing & Evaluation
Validate functionality and AI performance.
- [ ] AI output accuracy - Vindya
- [ ] Workload estimation
- [ ] System testing (API, DB, Telegram, Moodle, etc.)
- [ ] End-to-end test
- **Deliverable:** [ ] Test results + evaluation report

### 10. Final Demo & Documentation
Prepare final delivery.
- [ ] User guide
- [ ] Technical documentation
- [ ] Architecture diagram
- [ ] Project report
- [ ] Demo presentation
- **Deliverable:** [ ] Final system + documentation
