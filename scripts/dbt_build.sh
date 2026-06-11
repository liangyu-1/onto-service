#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/dataplatform-demo/jaffle_shop"
ARTIFACTS_DIR="$ROOT_DIR/dataplatform-demo/artifacts"

mkdir -p "$ARTIFACTS_DIR"

echo "Running dbt (jaffle_shop) to generate artifacts..."
echo "Project: $PROJECT_DIR"
echo "Artifacts: $ARTIFACTS_DIR"

cd "$PROJECT_DIR"

export DBT_PROFILES_DIR="$PROJECT_DIR"

dbt --version
dbt debug --target doris
dbt parse --target doris
dbt docs generate --target doris

cp -f "$PROJECT_DIR/target/manifest.json" "$ARTIFACTS_DIR/manifest.json"
cp -f "$PROJECT_DIR/target/catalog.json" "$ARTIFACTS_DIR/catalog.json"

echo "Done."

