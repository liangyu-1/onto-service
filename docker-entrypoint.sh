#!/bin/bash
set -e

echo "Starting Ontology Service..."

# Start Python grounding service in background
echo "Starting Python grounding service on port 5000..."
python3 /app/python/onto_service/main.py &
PYTHON_PID=$!

# Wait for Python service
sleep 2

# Start Java service
echo "Starting Java service on port 8080..."
exec java -jar /app/onto-service.jar "$@"
