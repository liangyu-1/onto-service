# Official tau2/tau3 Evaluation Path

This experiment has two evaluation paths:

- Local runner: useful for debugging planner behavior and local DB-hash reward.
- Official tau2/tau3 runner: required for any paper claim about tau-bench task performance.

Do not claim tau-bench task-performance improvement from local runner results.

The runtime ActionBank used below is a deterministic projection of
`data/action_ir/retail_action_ir.json`. After editing the canonical Action IR,
regenerate the runtime file and check the projection:

```bash
python experiments/paper3_agent_planning/compile_action_ir_to_action_bank.py
python experiments/paper3_agent_planning/smoke_action_ir_projection.py
```

## Run Official Baseline

Preferred one-command pipeline:

```bash
python experiments/paper3_agent_planning/run_official_tau2_pair.py \
  --domain retail \
  --agent-model gemma4-31b \
  --agent-base-url http://172.16.22.79:9999/v1 \
  --api-key EMPTY \
  --user-llm gpt-4.1 \
  --task-split-name base \
  --num-trials 1 \
  --max-concurrency 1 \
  --combined-output experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --report-output experiments/paper3_agent_planning/results_official_tau2/official_report.md
```

Manual commands are useful for debugging individual runs.

The one-command pipeline runs a preflight step before launching simulations.
It checks the Action IR projection, ActionBank, custom agent module, tau2 imports, and the
OpenAI-compatible `/v1/models` endpoint for the configured agent model. If you
only want to inspect commands, use `--dry-run`. If tau2 or the model endpoint is
not available in the current shell, use the skip flags only for local smoke
tests, not for paper runs:

```bash
python experiments/paper3_agent_planning/preflight_official_tau2.py \
  --agent-model gemma4-31b \
  --agent-base-url http://172.16.22.79:9999/v1 \
  --api-key EMPTY
```

The main comparison uses `Schema-Only` versus `Ours`. For ablation studies,
add `--run-ablations` to also run `OntologyPrompt` and `OntologyLite`.

The agent variants are:

- `Schema-Only`: official tau2 tools and policy only.
- `OntologyPrompt`: official tools, policy, and ActionBank in the prompt; no
  runtime gate.
- `OntologyLite`: ActionBank prompt plus runtime checks for official action
  membership, ActionBank membership, required parameters, and duplicates.
- `Ours`: ActionBank prompt plus full runtime admissibility checks.

The full `ontology`/`Ours` agent receives the ActionBank and runs a lightweight
admissibility checker before emitting tool calls. The checker rejects unknown
actions, missing required parameters, duplicate tool calls, and ActionBank
conditions that are not supported by conversation/tool evidence, including
authentication, explicit user confirmation, allowed cancellation reasons, and
order-status preconditions. Rejected candidates are returned to the LLM for
bounded repair. This keeps the official tau2 environment and reward unchanged
while testing the proposed action-layer control mechanism.

Before running expensive official simulations, verify that the ontology gate
itself is active:

```bash
python experiments/paper3_agent_planning/smoke_tau2_admissibility.py
```

## Manual: Run Official Baseline

```bash
python experiments/paper3_agent_planning/tau2_ontology_agent.py \
  --domain retail \
  --agent-kind schema \
  --agent-model gemma4-31b \
  --agent-base-url http://172.16.22.79:9999/v1 \
  --api-key EMPTY \
  --user-llm gpt-4.1 \
  --task-split-name base \
  --num-trials 1 \
  --max-concurrency 1 \
  --save-to schema_baseline_retail
```

## Manual: Run Official Ontology Agent

```bash
python experiments/paper3_agent_planning/tau2_ontology_agent.py \
  --domain retail \
  --agent-kind ontology \
  --agent-model gemma4-31b \
  --agent-base-url http://172.16.22.79:9999/v1 \
  --api-key EMPTY \
  --user-llm gpt-4.1 \
  --task-split-name base \
  --num-trials 1 \
  --max-concurrency 1 \
  --save-to ontology_guided_retail
```

## Import Official Results

Replace the paths below with the actual tau2 output files or directories.

```bash
python experiments/paper3_agent_planning/import_tau2_results.py \
  --left-path /path/to/schema_baseline_retail \
  --left-name Schema-Only \
  --right-path /path/to/ontology_guided_retail \
  --right-name Ours \
  --output experiments/paper3_agent_planning/results_official_tau2/combined.json
```

## Analyze Claim Readiness

```bash
python experiments/paper3_agent_planning/analyze_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json
```

## Generate Paper-Ready Tables

```bash
python experiments/paper3_agent_planning/report_official_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --output-md experiments/paper3_agent_planning/results_official_tau2/official_report.md
```

The report contains the planner summary, paired comparison table, ablation
table, ontology-gate mechanism table, claim-readiness status, and discordant
cases. It is for paper writing and audit; it does not replace fail-fast
validation.

## Fail-Fast Validation

Use this before copying results into the paper:

```bash
python experiments/paper3_agent_planning/validate_official_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --left Schema-Only \
  --right Ours \
  --min-unique-tasks 40 \
  --min-paired-simulations 40 \
  --alpha 0.05 \
  --require-gate-trace
```

The main claim is ready only if `CLAIM READINESS` reports:

- `Metric: paper_task_performance`
- `Ready for main paper claim: True`
- 40 unique paired retail tasks
- at least 40 paired simulations
- official evaluator names
- positive paired delta
- exact McNemar/binomial `p < 0.05`
- positive task-cluster delta and task-cluster sign-test `p < 0.05`
- ontology-gate traces for the proposed planner when mechanism analysis is
  claimed

For multi-trial official runs, `import_tau2_results.py` keeps `task_id::trial_id`
as the paired key instead of deduplicating by task id. However, repeated trials
are not treated as independent tasks for the main claim: `analyze_results.py`
also aggregates paired outcomes by `task_id` and runs a task-cluster sign test.
Use multi-trial runs to reduce stochastic variance, not to inflate the apparent
sample size.
