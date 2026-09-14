#!/bin/sh
echo "Checking Ollama model: ${OLLAMA_MODEL:-llama3.2:3b}..."
curl -s "${OLLAMA_BASE_URL:-http://ollama:11434}/api/pull" -d "{\"name\": \"${OLLAMA_MODEL:-llama3.2:3b}\"}"
echo "Ollama model initialization finished."
