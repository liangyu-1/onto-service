#!/bin/bash
set -e

echo "Starting Ontology Service Java..."

# Start Java service in background
java -jar /app/onto-service.jar "$@" &
JAVA_PID=$!

# Wait for Java health
MAX_RETRIES=60
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf http://localhost:8080/actuator/health >/dev/null 2>&1; then
        echo "Java service is healthy"
        break
    fi
    if [ $i -eq $MAX_RETRIES ]; then
        echo "Java service failed to start"
        exit 1
    fi
    echo "Waiting for Java service... ($i/$MAX_RETRIES)"
    sleep 2
done

# Check if Neo4j has data, if not trigger full sync
echo "Checking Neo4j data..."
SYNC_NEEDED=$(curl -sf http://localhost:8080/actuator/metrics/full_sync_completed_total 2>/dev/null | grep -o '"value":[0-9.]*' | cut -d: -f2 | cut -d. -f1)
if [ -z "$SYNC_NEEDED" ] || [ "$SYNC_NEEDED" = "0" ]; then
    echo "No full sync detected, triggering..."
    curl -sf -X POST "http://localhost:8080/v1/tbox/sync/full?ontologyId=default&ontologyVersion=latest" >/dev/null 2>&1 || true
    echo "Full sync triggered"
fi

# Bring Java to foreground
wait $JAVA_PID
