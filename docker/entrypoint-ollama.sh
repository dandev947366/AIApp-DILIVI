#!/bin/bash
# Entrypoint script for Ollama container
# Pulls the model specified in MODEL_ID env var

set -e

MODEL="${MODEL_ID:-qwen2.5:7b}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║              DAIA Ollama Model Loader                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Target model: $MODEL"
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

# Check if model already exists
echo ""
echo "🔍 Checking if model '$MODEL' is available..."
if ollama list 2>/dev/null | grep -q "^$MODEL"; then
    echo "✅ Model '$MODEL' already downloaded"
else
    echo "📥 Downloading model '$MODEL' (this may take several minutes)..."
    echo "   Model will be cached and won't need to be re-downloaded."
    echo ""
    
    # Pull with progress
    if ! ollama pull "$MODEL"; then
        echo "❌ Failed to pull model '$MODEL'"
        echo "   Check your internet connection and model name."
        echo "   Available models: https://ollama.com/library"
        kill $OLLAMA_PID
        exit 1
    fi
    
    echo ""
    echo "✅ Model '$MODEL' downloaded successfully"
fi

# Show model info
echo ""
echo "📊 Model information:"
ollama show "$MODEL" --modelfile 2>/dev/null | head -5 || true

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Ollama ready. Backend can now connect.                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Keep container running (Ollama server in foreground)
wait $OLLAMA_PID