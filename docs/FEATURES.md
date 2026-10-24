
# 🎓 DAIA: AI Study Path & Career Assistant

Your personalized study planner, student profile, and AI career assistant. DAIA integrates with your university's Moodle system, utilizes local LLMs for privacy-first AI tutoring, and helps you map your academic journey to your career goals.

---

## ✨ Key Features

### 🔐 Account Creation & Moodle Sync
Create your account by linking your Moodle profile. DAIA syncs your calendar, extracting upcoming deadlines and course information automatically.

![Account Creation UI](../imgs/account-create.png)
*Secure account creation with Moodle calendar export URL.*

![Login UI](../imgs/account-login.png)
*Easy login using your Moodle Student ID and Full Name.*

![Account Sync Success](../imgs/account-new.png)
*Successful account creation and calendar synchronization.*

![Logged Out View](../imgs/dashboard-noaccount.png)
*Secure logged-out dashboard state.*

### 🎓 Personalized Student Profile
DAIA maintains a dynamic profile of your academic journey, including your degree, preferred study times, career goals, interests, and a breakdown of your skills.

![Profile Updates](../imgs/profile-update.png)
*Update your profile naturally via chat (e.g., "update my study time to morning").*

![Transcript Import](../imgs/transcript-import.png)
*Import your academic transcript (PDF). DAIA uses a local LLM to extract structured information like degrees, skills, and interests across chunks.*

### 🤖 AI Tutor & Study Assistant
Get personalized help with your coursework. The AI assistant reads your Moodle assignments and provides structured study guides, sample quizzes, and preparation strategies.

![Assignment Sync](../imgs/assignment-sync.png)
*Chat interface to check upcoming assignments.*

![Assignment Prep](../imgs/tutor-agent-mcp.png)
*DAIA fetches current Moodle assignments and offers to help you break down the concepts.*

![Study Guide](../imgs/tutor-1.png)
*AI-generated study guide for a Neural Networks class test.*

![Sample Quiz 1](../imgs/tutor-2.png)
*AI generating sample multiple-choice questions for practice.*

![Sample Quiz 2](../imgs/tutor-3.png)
*Continued quiz generation and answers.*

### 📚 AI Thesis Advisor & Knowledge Base (RAG)
DAIA features a dedicated Thesis Agent powered by a localized Retrieval-Augmented Generation (RAG) pipeline. It helps you brainstorm thesis topics based on your unique skills and interests, while also acting as an expert consultant for university rules.

![Thesis RAG 1](../imgs/thesis-rag-fixed.png)
*Querying the local ChromaDB knowledge base for exact HAMK thesis rules and Wihi instructions.*


![Thesis Idea 1](../imgs/thesis-idea-fixed.png)
*Generating personalized thesis topics based on your student profile.*

### 💼 AI Career Assistant & Job Market Data
Bridge the gap between your studies and your career. DAIA searches for relevant jobs based on your location and interests, and provides live job market data.

![Interest Update](../imgs/feat-streaming.png)
*Add interests via chat to refine job searches.*

![Job Search](../imgs/feat-job-search.png)
*Search for jobs (e.g., "find me jobs in Europe") with AI matching scores.*

![Job Market Data](../imgs/job-market-data.png)
*Live Job Market Data panel showing active jobs and healthy system status.*

### 📱 Telegram Bot Integration
Access DAIA on the go. The Telegram bot allows you to create accounts, sync calendars, and chat with the AI assistant directly from your mobile device.

![Telegram Start](../imgs/telegram-start.png)
*Telegram Bot start menu with Login and Create Account options.*

![Telegram Sync](../imgs/telegram-create-account.png)
*Creating an account and syncing Moodle calendar via the Telegram bot.*

### 🐳 Local Deployment & System Architecture
DAIA is built for privacy and efficiency, utilizing Docker for containerization and Ollama for running local Large Language Models (LLMs).

![Docker Desktop](../imgs/docker-container.png)
*Running containers for the frontend, backend, and Ollama.*

![Docker Compose](../imgs/docker-run.png)
*Terminal output showing the successful build and launch of the application stack.*

![Backend Logs](../imgs/docker-terminal-backend.png)
*Backend logs confirming successful connection to the local Ollama instance and running on localhost.*

---

## 🚀 Getting Started
*check out SETUP.md at root folder**

## 🛠️ Tech Stack
*   **Frontend**: *(e.g., Gradio, React)*
*   **Backend**: *(e.g., Python, FastAPI)*
*   **AI/LLM**: Ollama (Llama 3.2)
*   **Containerization**: Docker & Docker Compose
*   **Integrations**: Moodle API / iCal, Telegram Bot API, Jobicy API