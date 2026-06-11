#!/usr/bin/env bash
# 对已运行的 Doris 补建 TBOX 表（ontology_object_type 等）。
# 默认连接 localhost:9030；Docker 内可从 onto-doris-init 同网段用 -h doris-fe。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-9030}"
echo "Applying $ROOT/sql/01_tbox_schema.sql to $HOST:$PORT (database ontology) ..."
mysql -h"$HOST" -P"$PORT" -uroot <"$ROOT/sql/01_tbox_schema.sql"
echo "Done. Verify: SHOW TABLES FROM ontology LIKE 'ontology_object_type';"
