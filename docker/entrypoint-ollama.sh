#!/bin/bash
# Entrypoint script for Ollama container
# Pulls the models specified in env vars

set -e

MODEL="${MODEL_ID:-qwen2.5:7b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║              DAIA Ollama Model Loader                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Target LLM: $MODEL"
echo "🎯 Target Embedding Model: $EMBEDDING_MODEL"
echo "⏰ Starting Ollama server..."
echo ""

# Start Ollama server in background
/bin/ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for Ollama server to start..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama server is ready"
        break
    fi
    sleep 1
done

# Function to pull a model
pull_model() {
    local M="$1"
    echo ""
    echo "🔍 Checking if model '$M' is available..."
    if ollama list 2>/dev/null | grep -q "^$M"; then
        echo "✅ Model '$M' already downloaded"
    else
        echo "📥 Downloading model '$M' (this may take several minutes)..."
        if ! ollama pull "$M"; then
            echo "❌ Failed to pull model '$M'"
            echo "   Check your internet connection and model name."
            kill $OLLAMA_PID
            exit 1
        fi
        echo "✅ Model '$M' downloaded successfully"
    fi
}

# Pull both models
pull_model "$MODEL"
pull_model "$EMBEDDING_MODEL"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Ollama ready. Backend can now connect.                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Keep container running (Ollama server in foreground)
wait $OLLAMA_PID