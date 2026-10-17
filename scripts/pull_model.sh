#!/bin/bash
echo "Starting Ollama..."
ollama serve &
sleep 5
echo "Pulling model qwen2.5:7b..."
ollama pull qwen2.5:7b
echo "Model ready!"