import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
)

MODEL_ID = os.getenv(
    "MODEL_ID",
    "qwen3:4b",
)

OLLAMA_TIMEOUT = float(
    os.getenv("OLLAMA_TIMEOUT", "300")
)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
)

ICAL_URL = os.getenv(
    "ICAL_URL",
    "",
)
