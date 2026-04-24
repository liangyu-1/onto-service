#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Seeding Neo4j TBOX demo graph..."
echo "Assumes docker-compose is up and neo4j container is running."

docker exec -i onto-neo4j cypher-shell -u neo4j -p neo4jpass < "$ROOT_DIR/scripts/seed_tbox.cypher"
docker exec -i onto-neo4j cypher-shell -u neo4j -p neo4jpass < "$ROOT_DIR/scripts/seed_tpch.cypher"

echo "Done."

