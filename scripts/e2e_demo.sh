#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

need_image() {
  local img="$1"
  if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${img}$"; then
    echo "Missing docker image: ${img}"
    echo "Please pull it first: docker pull ${img}"
    exit 2
  fi
}

need_image "apache/doris:fe-4.0.4"
need_image "apache/doris:be-4.0.4"
need_image "neo4j:5.22"

echo "Building Java jar..."
(cd "$ROOT_DIR/onto-service-java" && mvn -DskipTests package)

echo "Starting docker-compose..."
cd "$ROOT_DIR"
docker-compose up -d --remove-orphans

echo "Initializing Doris..."
bash "$ROOT_DIR/scripts/init_doris.sh"

echo "Seeding Neo4j..."
bash "$ROOT_DIR/scripts/seed_neo4j.sh"

echo "Smoke check..."
curl -fsS "http://localhost:8080/api/v1/domains/PlantGraph/versions" >/dev/null || true
echo "Open UI at http://localhost:8080/"

