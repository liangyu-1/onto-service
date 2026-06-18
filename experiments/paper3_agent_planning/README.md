# Paper 3: Ontology-Grounded Action Planning

This directory contains the experiment code for the third paper idea:
using an ontology-grounded action layer to improve LLM agent planning and
execution on policy-constrained tool-use tasks.

The experiment is intentionally organized around two evidence channels:

1. Official tau2 task performance: whether the method improves task success
   under the official tau2/tau-bench runner and reward.
2. Ontology semantics diagnostics: whether the canonical Action IR, projected
   ActionBank, grounding logic, and verifier actually encode the claimed action
   semantics.

Local toy runners and old Kimi result folders were removed because they cannot
support paper-grade tau-bench performance claims.

The schema convention is:

```text
Paper2 SOP extraction -> canonical Action IR -> deterministic ActionBank projection -> Paper3 agent
```

`data/action_ir/retail_action_ir.json` is the canonical schema shared by Paper2
and Paper3. `data/action_bank/retail_action_bank.json` is generated from it and
contains only the runtime fields needed by the tau2 agent.

The runtime method separates action semantics into two grounding regimes:

- Epistemic actions (`action_kind=epistemic`, `grounding_mode=weak`) acquire
  world state, for example user/order/product lookups. They require concrete
  input identifiers and policy prerequisites such as authentication, but they
  must not require the target object to already be cached.
- Mutating actions (`action_kind=mutate`, `grounding_mode=strong`) change the
  environment. They require observed target objects, role-bound parameters,
  policy preconditions, and confirmation before execution.

This distinction is central to the paper claim: the ontology layer should not
only reject unsafe actions, but should preserve exploration actions that are
needed to ground later state-changing actions.

## What The Code Does

### Official tau2 path

Use this path for the main paper claim about task performance.

| File | Purpose |
| --- | --- |
| `tau2_ontology_agent.py` | Custom tau2 half-duplex agent exposing the paper-defined `schema`, `ontology_prompt`, `state_only`, `typed_admissibility`, and `ontology_full` variants. |
| `make_heldout_tau2_commands.py` | Samples held-out task ids while excluding the debug set, then prints matched schema/ontology tau2 commands. |
| `run_official_tau2_pair.py` | One-command paired run wrapper for baseline and ontology variants, plus import/report steps. |
| `preflight_official_tau2.py` | Checks Action IR projection, ActionBank, tau2 imports, custom agent registration, and model endpoint before expensive runs. |
| `import_tau2_results.py` | Converts official tau2 result directories/files into the paired JSON format used by analysis. |
| `analyze_results.py` | Computes paired success deltas, McNemar/binomial tests, task-cluster sign test, and claim-readiness reasons. |
| `report_official_results.py` | Generates paper-facing markdown tables from imported official results. |
| `validate_official_results.py` | Fail-fast validation before copying numbers into the paper. |
| `compile_action_ir_to_action_bank.py` | Compiles canonical Action IR into the runtime ActionBank JSON used by Paper3. |

### Ontology semantics path

Use this path to prove that the ontology/action-layer mechanism itself is
implemented coherently.

| File | Purpose |
| --- | --- |
| `run_ontology_benchmarks.py` | Runs deterministic diagnostics for state-sensitive admissibility, counterfactual state tests, role binding, effect consistency, and component ablations. |
| `src/action_bank.py` | Loads canonical Action IR or projected runtime ActionBank schemas. |
| `src/runtime_ontology.py` | Reconstructs authentication, object state, successful calls, mutations, and action-bound confirmations from observed events only. |
| `src/argument_grounder.py` | Grounds arguments through ActionBank target bindings and parameter roles. |
| `src/ontology_repair.py` | Converts violations to missing predicates and resolves enabling actions through ActionBank predicate providers. |
| `src/verifier.py` | Checks local ontology preconditions and policy constraints. |
| `src/simulator.py` | Retail tool-effect simulator used by ontology diagnostics, not by official tau2 scoring. |
| `src/state_manager.py` | Dialogue/action state representation for diagnostics. |
| `src/data_loader.py` | Loader for local retail tau-bench data used by diagnostics. |

### Smoke tests

These scripts are small guards for code-level regressions. They are not paper
experiments by themselves.

| File | Purpose |
| --- | --- |
| `smoke_tau2_admissibility.py` | Checks ontology-gate rejection, repair hints, and deterministic repair behavior. |
| `smoke_tau2_response_guard.py` | Checks response handling around tau2 agent output. |
| `smoke_import_tau2_mechanism.py` | Checks official result import and ontology-gate trace extraction. |
| `smoke_report_official_results.py` | Checks report generation on synthetic imported results. |
| `smoke_task_cluster_stats.py` | Checks task-cluster significance logic. |
| `smoke_action_ir_projection.py` | Checks that the committed ActionBank is the deterministic projection of the canonical Action IR. |
| `smoke_epistemic_action_semantics.py` | Checks that read/lookup actions use weak grounding while mutating actions keep strong grounding. |
| `smoke_method_alignment.py` | Checks role projection, structured evidence binding, cross-order counterexamples, and predicate-driven repair. |
| `smoke_variant_isolation.py` | Checks strict isolation of ActionBank, runtime state, gate, and repair across paper variants. |

## Data And Action Schemas

| Path | Meaning |
| --- | --- |
| `data/action_ir/retail_action_ir.json` | Canonical ontology-grounded Action IR. It contains actor, target binding, structured parameters, preconditions, effects, constraints, state transitions, control-flow hints, evidence, grounding, and runtime projection metadata. |
| `data/action_bank/retail_action_bank.json` | Runtime ActionBank projection generated from `data/action_ir/retail_action_ir.json`. It is used by the agent prompt, admissibility gate, and diagnostics. |
| `data/raw/retail/` | Local tau-bench retail data. It is used only by ontology diagnostics and local checks. The official tau2 runner uses its own installed data path. |

The official tau2 agent must not read `data/raw/retail/db.json` or any other
complete environment database. During official runs, object grounding is allowed
to use only:

- the current conversation,
- official tool outputs already observed in the trajectory,
- the ActionBank / ontology schema.

This restriction is necessary to avoid hidden database leakage.

The implemented Method path is:

```text
Canonical Action IR
  -> ActionBank(target binding, parameter roles, predicates, providers)
  -> RuntimeOntologyState(observed evidence only)
  -> Type-aware admissibility
  -> Missing predicate
  -> Ontology provider action
  -> Repaired candidate
```

Authentication, object state, duplicate execution, and confirmation are checked
against structured runtime evidence. Confirmation is bound to the concrete
action and target arguments rather than treated as a global dialogue flag.

Official experiment variants:

| `agent-kind` | ActionBank prompt | Runtime state prompt | Gate | Full conditions | Repair |
| --- | ---: | ---: | ---: | ---: | ---: |
| `schema` | No | No | No | No | No |
| `ontology_prompt` | Yes | No | No | No | No |
| `state_only` | Yes | Yes | No | No | No |
| `typed_admissibility` | Yes | Yes | Yes | Yes | No |
| `ontology_full` / `ontology` | Yes | Yes | Yes | Yes | Yes |

`ontology_lite` remains a legacy structural-gate debugging variant and is not a
paper-table baseline.

The current implementation is retail-focused. Airline-specific prototype files
were removed because the official agent path does not yet implement a separate
airline ActionBank/gate.

## Recommended Workflow

Run smoke checks first:

```bash
python experiments/paper3_agent_planning/smoke_tau2_admissibility.py
python experiments/paper3_agent_planning/smoke_import_tau2_mechanism.py
python experiments/paper3_agent_planning/smoke_report_official_results.py
python experiments/paper3_agent_planning/smoke_task_cluster_stats.py
python experiments/paper3_agent_planning/smoke_action_ir_projection.py
```

Rebuild the runtime ActionBank after editing the canonical Action IR:

```bash
python experiments/paper3_agent_planning/compile_action_ir_to_action_bank.py
```

Run ontology diagnostics:

```bash
python experiments/paper3_agent_planning/run_ontology_benchmarks.py \
  --split test \
  --output experiments/paper3_agent_planning/results/ontology_benchmark_test.json
```

Run official paired tau2 evaluation:

```bash
python experiments/paper3_agent_planning/run_official_tau2_pair.py \
  --domain retail \
  --agent-model GLM-5.1 \
  --agent-base-url https://open.bigmodel.cn/api/coding/paas/v4 \
  --api-key "$AGENT_API_KEY" \
  --user-llm openai/GLM-5.1 \
  --task-split-name base \
  --num-trials 1 \
  --max-concurrency 1 \
  --combined-output experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --report-output experiments/paper3_agent_planning/results_official_tau2/official_report.md
```

For held-out debugging after changing the method, generate matched commands
instead of reusing the hand-debugged 10 tasks:

```bash
python experiments/paper3_agent_planning/make_heldout_tau2_commands.py \
  --split base \
  --num-tasks 40 \
  --seed 20260616
```

Run both printed commands. The default excluded task ids are:

```text
0 1 2 3 4 5 6 8 9 11
```

These were used for method debugging and should not be used as the primary
paper result.

If you run baseline and ontology agents manually, import their official tau2
outputs explicitly:

```bash
python experiments/paper3_agent_planning/import_tau2_results.py \
  --left-path /path/to/schema_run \
  --left-name Schema-Only \
  --right-path /path/to/ontology_run \
  --right-name Ours \
  --domain retail \
  --task-split-name base \
  --output experiments/paper3_agent_planning/results_official_tau2/combined.json
```

Analyze and validate:

```bash
python experiments/paper3_agent_planning/analyze_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json

python experiments/paper3_agent_planning/validate_official_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --left Schema-Only \
  --right Ours \
  --min-unique-tasks 40 \
  --min-paired-simulations 40 \
  --alpha 0.05 \
  --require-gate-trace
```

## What Counts As Paper Evidence

Valid evidence:

- Official tau2 rewards imported through `import_tau2_results.py`.
- Paired comparisons between the same task/trial keys.
- Positive task-success delta plus statistical significance.
- Task-cluster significance, because repeated trials are not independent tasks.
- Ontology-gate traces for the proposed planner when claiming mechanism effects.
- Deterministic ontology diagnostics from `run_ontology_benchmarks.py`.
- A passing `smoke_action_ir_projection.py`, proving that Paper3 uses the
  runtime projection of the Paper2-compatible Action IR.

Invalid evidence:

- Old local runner success numbers.
- Smoke tests alone.
- Ad hoc Kimi result folders.
- Partial tau2 runs with missing task/trial coverage.
- Runs on the hand-debugged task set alone.
- Any run where the official tau2 agent reads the full local retail database
  instead of using only observed tool outputs.
- Any run where `schema` baseline secretly uses ontology normalization or gate logic.
- Any manually edited ActionBank that no longer matches the canonical Action IR.

## Current Scope And Limitations

- The implementation targets tau2 retail.
- The ontology gate is conservative; it can reject unsafe/unsupported action
  candidates but does not guarantee global task optimality.
- The main claim is not valid until official paired results pass
  `validate_official_results.py`.
- Generated result files are ignored by Git. Keep raw official tau2 output paths
  when auditing a paper table.
