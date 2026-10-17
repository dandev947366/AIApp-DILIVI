# DAIA — Setup & Operations Guide

Works on **macOS** and **Windows**. Follow the section for your OS when
commands differ.

## 0. Prerequisites

- **Docker Desktop** installed and running.
  - macOS: https://docs.docker.com/desktop/install/mac-install/
  - Windows: https://docs.docker.com/desktop/install/windows-install/
- **Docker must be ON** before running any command below.
  - macOS: whale icon in the menu bar, no animation
  - Windows: whale icon in the system tray, "Docker Desktop is running"

![Docker Container Running](imgs/docker-container.png)

- Verify Docker is alive:

  ```bash
  docker --version
  docker compose version
  ```

  Both must print a version. If not, launch Docker Desktop and wait until it is fully started.

---

## 1. Make the entrypoint scripts executable

These two files must have the executable bit set, or the containers will fail to start with `permission denied`:
- `docker/entrypoint-ollama.sh`
- `docker/wait-for-ollama.sh`

### macOS
Open Terminal, `cd` into the project root, then:
```bash
chmod +x docker/entrypoint-ollama.sh
chmod +x docker/wait-for-ollama.sh
```

### Windows
`chmod` does not exist in PowerShell or CMD. Pick **one** of the following:

**Option A — WSL (Recommended)**
Open a WSL terminal (Ubuntu, etc.):
```bash
cd /mnt/c/path/to/your/project
chmod +x docker/entrypoint-ollama.sh
chmod +x docker/wait-for-ollama.sh
```

**Option B — Git Bash**
Git Bash ships with Git for Windows and includes `chmod`:
```bash
cd /c/path/to/your/project
chmod +x docker/entrypoint-ollama.sh
chmod +x docker/wait-for-ollama.sh
```

**Option C — Force permissions at build time**
If neither WSL nor Git Bash is available, tell Docker to set the bit during build. Edit `Dockerfile.backend` and add one line before the final `CMD`:
```dockerfile
RUN chmod +x /app/docker/entrypoint-ollama.sh /app/docker/wait-for-ollama.sh
```

---

## 2. Choose the model

The model is set in `.env` at the project root. Docker will pull it automatically on the next start if it is not already cached in the Ollama volume.

Open `.env` in any editor and set:
```bash
MODEL_ID=llama3.1:8b
```
*(Change the value to whichever model you want, e.g., `llama3.2:3b`, `qwen2.5:7b`).*

Restart the services so the new value takes effect:
```bash
docker compose down
docker compose up -d
```

![Docker Run](imgs/docker-run.png)

On the next boot, the Ollama container will download the new model if it is missing. Wait until you see `success` in the logs.

---

## 3. Common Commands

**All of these assume Docker Desktop is running.**

### Stop everything (keep data)
```bash
docker compose down
```
- Stops and removes containers.
- **Keeps** the SQLite database and the Ollama model cache.

### Stop and remove containers + all data (⚠️ Destructive)
```bash
docker compose down -v
```
- Removes containers **and** volumes.
- Your student profiles, calendar events, skills, and sessions are wiped.
- Ollama models must be re-downloaded on the next start.

### Start the stack
```bash
docker compose up -d
```

### Rebuild the backend and follow the logs
Use this after changing any Python file in `app/`, `src/`, or `tests/`:
```bash
docker compose up -d --force-recreate backend
docker compose logs -f backend
```

![Docker Terminal Backend](imgs/docker-terminal-backend.png)

---

## 4. First-time setup checklist

Run these in order the first time you clone the project:

1. **Docker Desktop is running.**
2. **Make the scripts executable** (Section 1).
3. **Set the model** in `.env` (Section 2).
4. **Start the stack** — `docker compose up -d`.
5. **Open** http://localhost:7860 in your browser.

### Step-by-step UI Walkthrough

#### 1. The Dashboard (Logged Out)
When you first open the app, you will see the main chat interface and the **Account** panel on the right.

![Dashboard No Account](imgs/dashboard-noaccount.png)

#### 2. Create a New Account (First Time)
Click the **Create account** radio button. Enter your full name and paste your Moodle iCal export URL.
![Account Create](imgs/account-create.png)

Once you submit the form, the system will sync your Moodle calendar and create your profile.

![Account New](imgs/account-new.png)
#### 3. Log In (Returning Users)
If you already have an account (or after you log out), select the **Log in** radio button. Enter the Moodle Student ID and the exact Full Name you registered with.

![Account Login](imgs/account-login.png)

#### 4. Import Your Transcript (Optional)
To auto-fill your skills, degree, and courses, open the **📄 Import Transcript** accordion in the main chat area. Upload a PDF or TXT file and click **Extract Data**.

![Transcript Import](imgs/transcript-import.png)

#### 5. Update Your Profile via Chat
You don't need to fill out a form to update your preferences. Just tell DAIA! 
For example, say: *"I prefer studying in the evening and I can study 15 hours a week."* The sidebar will auto-update in real-time.

![Profile Update](imgs/profile-update.png)

---

## 5. Troubleshooting

### `permission denied` when starting a container
The entrypoint script is missing its executable bit. Go back to Section 1.

### Backend keeps restarting
Check the logs:
```bash
docker compose logs backend | tail -100
```
The traceback names the file and line. Most common causes: a missing import, a syntax error in `app/ui.py`, or a broken `MODEL_ID`.

### Port 7860 is already in use
Another process is bound to the port. Stop the other process, or edit `docker-compose.yml`:
```yaml
services:
  backend:
    ports:
      - "7861:7860"
```
Then `docker compose up -d` and open http://localhost:7861.

---

## 6. What lives where

| Path | Contents |
| --- | --- |
| `.env` | Runtime configuration (model, DB URL, secrets) |
| `data/student_context.db` | SQLite database (profiles, skills, events) |
| `data/.session_secret` | Auto-generated session signing key |
| `docker/entrypoint-ollama.sh` | Ollama container entrypoint |
| `docker/wait-for-ollama.sh` | Backend container wait-for-Ollama helper |
| `app/ui.py` | Gradio interface |
| `src/` | Services, agents, models, tools |

---

## 7. Quick reference card

```bash
# Start everything (Docker must be running)
docker compose up -d

# Stop everything, keep data
docker compose down

# Stop everything, wipe data (⚠️ destructive)
docker compose down -v

# Rebuild backend after Python changes, then watch logs
docker compose up -d --force-recreate backend
docker compose logs -f backend

# Check status
docker compose ps
```