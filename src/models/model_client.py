from ollama import Client

from src.config import OLLAMA_HOST, OLLAMA_TIMEOUT

model_client = Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
