#!/usr/bin/env bash
set -euo pipefail

# Full official tau2 retail paired run for Paper 3.
#
# Scope:
#   - retail/base full split
#   - Schema-Only vs Ours
#   - same task split, same number of trials, same model settings
#   - no local retail DB leakage; tau2_ontology_agent owns runtime grounding
#
# Required:
#   export AGENT_API_KEY=...
#
# Optional overrides:
#   PYTHON=python
#   AGENT_MODEL=GLM-5.1
#   AGENT_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
#   USER_LLM=openai/GLM-5.1
#   USER_BASE_URL=$AGENT_BASE_URL
#   USER_API_KEY=$AGENT_API_KEY
#   NUM_TRIALS=2
#   MAX_CONCURRENCY=1
#   MAX_STEPS=200
#   SEED_TAG=20260617
#   RUN_ABLATIONS=0
#   SKIP_PREFLIGHT=0

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXP_DIR="$ROOT_DIR/experiments/paper3_agent_planning"

PYTHON_BIN="${PYTHON:-python}"
AGENT_MODEL="${AGENT_MODEL:-GLM-5.1}"
AGENT_BASE_URL="${AGENT_BASE_URL:-https://open.bigmodel.cn/api/coding/paas/v4}"
USER_LLM="${USER_LLM:-openai/GLM-5.1}"
USER_BASE_URL="${USER_BASE_URL:-$AGENT_BASE_URL}"
NUM_TRIALS="${NUM_TRIALS:-2}"
MAX_CONCURRENCY="${MAX_CONCURRENCY:-1}"
MAX_STEPS="${MAX_STEPS:-200}"
SEED_TAG="${SEED_TAG:-$(date +%Y%m%d_%H%M%S)}"
RUN_ABLATIONS="${RUN_ABLATIONS:-0}"
SKIP_PREFLIGHT="${SKIP_PREFLIGHT:-0}"

: "${AGENT_API_KEY:?Set AGENT_API_KEY before running this script.}"
USER_API_KEY="${USER_API_KEY:-$AGENT_API_KEY}"

SCHEMA_SAVE_TO="full_base_schema_${SEED_TAG}"
ONTOLOGY_SAVE_TO="full_base_ontology_${SEED_TAG}"
ONTOLOGY_PROMPT_SAVE_TO="full_base_ontology_prompt_${SEED_TAG}"
ONTOLOGY_LITE_SAVE_TO="full_base_ontology_lite_${SEED_TAG}"
OUT_DIR="$EXP_DIR/results_official_tau2/full_base_${SEED_TAG}"
COMBINED_OUTPUT="$OUT_DIR/combined.json"
REPORT_OUTPUT="$OUT_DIR/official_report.md"

mkdir -p "$OUT_DIR"

echo "[1/6] Compile canonical Action IR -> runtime ActionBank"
"$PYTHON_BIN" "$EXP_DIR/compile_action_ir_to_action_bank.py"

echo "[2/6] Run local smoke checks"
"$PYTHON_BIN" "$EXP_DIR/smoke_action_ir_projection.py"
"$PYTHON_BIN" "$EXP_DIR/smoke_epistemic_action_semantics.py"
"$PYTHON_BIN" "$EXP_DIR/smoke_tau2_admissibility.py"
"$PYTHON_BIN" "$EXP_DIR/smoke_import_tau2_mechanism.py"

PAIR_CMD=(
  "$PYTHON_BIN" "$EXP_DIR/run_official_tau2_pair.py"
  --domain retail
  --agent-model "$AGENT_MODEL"
  --agent-base-url "$AGENT_BASE_URL"
  --api-key "$AGENT_API_KEY"
  --user-llm "$USER_LLM"
  --task-split-name base
  --num-trials "$NUM_TRIALS"
  --max-concurrency "$MAX_CONCURRENCY"
  --max-steps "$MAX_STEPS"
  --schema-save-to "$SCHEMA_SAVE_TO"
  --ontology-save-to "$ONTOLOGY_SAVE_TO"
  --ontology-prompt-save-to "$ONTOLOGY_PROMPT_SAVE_TO"
  --ontology-lite-save-to "$ONTOLOGY_LITE_SAVE_TO"
  --combined-output "$COMBINED_OUTPUT"
  --report-output "$REPORT_OUTPUT"
  --skip-validate
)

if [[ "$SKIP_PREFLIGHT" == "1" ]]; then
  PAIR_CMD+=(--skip-preflight)
fi

if [[ "$RUN_ABLATIONS" == "1" ]]; then
  PAIR_CMD+=(--run-ablations)
fi

echo "[3/6] Run full official paired tau2 evaluation"
echo "Schema save_to:   $SCHEMA_SAVE_TO"
echo "Ontology save_to: $ONTOLOGY_SAVE_TO"
echo "Trials:           $NUM_TRIALS"
echo "Concurrency:      $MAX_CONCURRENCY"
"${PAIR_CMD[@]}"

echo "[4/6] Strict full-run validation"
PAIRED_MIN=$((114 * NUM_TRIALS))
if "$PYTHON_BIN" "$EXP_DIR/validate_official_results.py" \
  "$COMBINED_OUTPUT" \
  --left Schema-Only \
  --right Ours \
  --min-unique-tasks 114 \
  --min-paired-simulations "$PAIRED_MIN" \
  --alpha 0.05 \
  --require-gate-trace; then
  VALIDATION_STATUS="passed"
else
  VALIDATION_STATUS="failed"
fi

echo "[5/6] Result locations"
echo "Schema official output:   data/simulations/$SCHEMA_SAVE_TO"
echo "Ontology official output: data/simulations/$ONTOLOGY_SAVE_TO"
echo "Combined JSON:            $COMBINED_OUTPUT"
echo "Markdown report:          $REPORT_OUTPUT"
echo "Strict validation:        $VALIDATION_STATUS"

echo "[6/6] Done"
if [[ "$VALIDATION_STATUS" != "passed" ]]; then
  echo "The run completed, but the strict paper-readiness validation failed. Inspect the report before using the numbers."
fi
