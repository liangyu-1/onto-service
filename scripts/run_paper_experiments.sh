#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/3] Preflight checks..."
python experiments/preflight.py

echo "[2/3] Running exp1-exp5..."
python experiments/run_all.py

echo "[3/3] Done. See experiments/results/"

