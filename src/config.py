import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# If running inside Docker, default to the Docker Compose service name ('ollama').
# If running locally on your Mac/PC, default to 'localhost'.
IS_DOCKER = os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
DEFAULT_OLLAMA_HOST = "http://ollama:11434" if IS_DOCKER else "http://localhost:11434"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
MODEL_ID = os.getenv("MODEL_ID", "qwen2.5:7b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "600"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ICAL_URL = os.getenv("ICAL_URL", "")
HOURS_PER_DAY = int(os.getenv("HOURS_PER_DAY", "2"))
BUFFER_DAYS = int(os.getenv("BUFFER_DAYS", "1"))
REMINDER_TIME = os.getenv("REMINDER_TIME", "09:00")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/student_context.db")

API_PORT = int(os.getenv("API_PORT", "8000"))


@dataclass
class Config:
    """Simple configuration object reading environment variables."""

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_HOST)
    model_name: str = os.getenv("MODEL_NAME", "llama3.2")


# Instantiate global configuration object
config = Config()
