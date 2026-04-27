# Experiments

This folder implements the reproducible experiment workflow described in `paper-experiment-blueprint`.

## Structure
- `preflight.py`: hard-gate checks for TPCH/PlantGraph TBOX + mappings.
- `metrics.py`: paper metrics (Average Regret, CNU, UTR, Hit Rate + auxiliary metrics).
- `policies.py`: policy adapters (Static, Always, Edit-Threshold, Workload-Only, Significance-Only, Proposed, Oracle).
- `runner.py`: unified policy evaluation engine and result schema writer.
- `run_exp1_exp2.py`: replay + decision quality (with curve/table source files).
- `run_exp3_counterfactual.py`: counterfactual scenarios.
- `run_exp4_generalization.py`: leave-one-ontology-out.
- `run_exp5_drift.py`: workload drift experiment.
- `paper_pack.py`: merge latest outputs into a paper-ready artifact index.
- `run_all.py`: execute exp1-exp5 and build artifact pack.
- `configs/*.jsonl`: event/replay inputs.

## Quick Start
1. Ensure services are up (`docker-compose up -d`) and seeded:
   - `bash scripts/init_doris.sh`
   - `bash scripts/seed_neo4j.sh`
2. Run all experiments:
   - `python experiments/run_all.py`
3. Check outputs under:
   - `experiments/results/`

## Output Convention
- Per-run:
  - `steps_<policy>.jsonl`
  - `summary_<policy>.json`
  - `summary.csv`
  - `run_meta.json`
- Paper pack:
  - `paper_artifact_pack_*/artifact_index.json`
  - `paper_artifact_pack_*/summary.csv`

