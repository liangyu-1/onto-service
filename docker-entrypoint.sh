#!/bin/bash
set -e

echo "Starting Ontology Service Java..."
exec java -jar /app/onto-service.jar "$@"
