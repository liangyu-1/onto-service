#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Initializing Doris schema + HAI demo data..."
echo "Assumes docker-compose is up and doris-fe is reachable."

# Doris FE container includes mysql client in most images; if not, run from host with mysql installed.
run_mysql() {
  docker exec -i onto-doris-fe mysql -h127.0.0.1 -P9030 -uroot "$@"
}

run_mysql < "$ROOT_DIR/sql/02_abox_schema.sql"
run_mysql < "$ROOT_DIR/sql/03_hai_demo.sql"
run_mysql < "$ROOT_DIR/sql/04_tpch_schema.sql"

# Load public TPCH SF0.01 dataset into Doris
bash "$ROOT_DIR/scripts/init_tpch.sh"

echo "Done."

