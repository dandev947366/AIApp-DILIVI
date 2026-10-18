#!/bin/sh
set -e

# Wait for Ollama and the configured model before starting the application.
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
MODEL_ID="${MODEL_ID:-qwen2.5:7b}"
MAX_WAIT=300

echo "Waiting for Ollama at ${OLLAMA_HOST}..."
echo "Expected model: ${MODEL_ID}"

elapsed=0

while [ "$elapsed" -lt "$MAX_WAIT" ]; do
    if curl -fsS "${OLLAMA_HOST}/api/tags" -o /tmp/ollama-tags.json; then
        if python -c '
import json, os, sys
with open("/tmp/ollama-tags.json") as f:
    models = json.load(f).get("models", [])
expected = os.environ["MODEL_ID"]
sys.exit(0 if any(m.get("name") == expected or m.get("name", "").split(":")[0] == expected.split(":")[0] and ":" not in expected for m in models) else 1)
' ; then
            echo "Ollama is ready with model '${MODEL_ID}'."
            echo "Starting application: $*"
            exec "$@"
        fi
    fi

    sleep 5
    elapsed=$((elapsed + 5))
    echo "Still waiting... (${elapsed}s / ${MAX_WAIT}s)"
done

echo "ERROR: Timed out waiting for Ollama model '${MODEL_ID}'."
exit 1