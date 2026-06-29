# Paper 2 Workflow Skill Experiments

This directory starts the new Paper 2 implementation:

> Inducing Executable Ontology Workflow Skills from Procedural Documents

It is intentionally separate from the old Action IR extraction code. The target
output is an `OntologyWorkflowSkill`, whose nodes reference ontology functions
and whose variables, conditions, data flow, invariants, and exceptions are
validated against ontology/function-layer constraints.

## Dataset Requirement

Do not treat the existing processed public files as complete gold labels. They
can seed procedural documents, but the Paper 2 benchmark must additionally
provide:

- reviewed object ontology;
- curated Function Layer;
- workflow nodes grounded to function IDs;
- typed object variables;
- control-flow and typed data-flow edges;
- state predicates, invariants, exception paths;
- train/dev/test splits.

Use `dataset/full_ontology_workflow_benchmark/` as the benchmark working
directory and
`dataset/annotation_guidelines/paper2_workflow_skill_guideline.md` as the
annotation rule. Until those files exist, runs from this directory are smoke
tests only.

## Inputs

Required:

- `--documents`: JSONL procedural documents. The existing
  `dataset/idea2_sop_action_benchmark/processed/*.jsonl` files can be used for
  early development.
- `--ontology`: ontology JSON. The existing
  `dataset/idea2_sop_action_benchmark/seed_ontology.json` can be used for smoke
  tests, but it is not a validated industrial ontology.
- `--function-layer`: JSONL functions, preferably Paper 1
  `published_functions.jsonl` or a curated Function Layer.

Optional:

- `--gold-workflows`: JSONL gold `OntologyWorkflowSkill` annotations for
  evaluation.
- `--llm-base-url`, `--llm-model`, `--api-key-env`: enable GLM-5.2 or another
  OpenAI-compatible model for workflow generation.
- `--max-docs`: limit records for smoke tests.

## Smoke Run

This requires a function-layer file. If Paper 1 output is not ready, create a
small curated function library for the target domain rather than inventing it
inside the code.

```bash
python experiments/paper2_workflow_skill/run_experiment.py \
  --documents dataset/idea2_sop_action_benchmark/processed/myfixit.jsonl \
  --ontology dataset/idea2_sop_action_benchmark/seed_ontology.json \
  --function-layer outputs/paper1_function_layer/published_functions.jsonl \
  --gold-workflows dataset/full_ontology_workflow_benchmark/annotations/workflow_skills.gold.jsonl \
  --output-dir outputs/paper2_workflow_skill \
  --max-docs 20
```

Pilot schema check using the checked-in sample fixture:

```bash
python experiments/paper2_workflow_skill/run_experiment.py \
  --documents dataset/full_ontology_workflow_benchmark/documents/myfixit_10262.sample.jsonl \
  --ontology dataset/full_ontology_workflow_benchmark/ontology/ontology.sample.json \
  --function-layer dataset/full_ontology_workflow_benchmark/function_layer/functions.sample.jsonl \
  --gold-workflows dataset/full_ontology_workflow_benchmark/annotations/workflow_skills.gold.sample.jsonl \
  --output-dir /private/tmp/paper2_pilot_smoke \
  --max-docs 1
```

## GLM-5.2 Run

```bash
export GLM_API_KEY=...

python experiments/paper2_workflow_skill/run_experiment.py \
  --documents dataset/idea2_sop_action_benchmark/processed/myfixit.jsonl \
  --ontology dataset/idea2_sop_action_benchmark/seed_ontology.json \
  --function-layer outputs/paper1_function_layer/published_functions.jsonl \
  --gold-workflows dataset/full_ontology_workflow_benchmark/annotations/workflow_skills.gold.jsonl \
  --output-dir outputs/paper2_workflow_skill_glm52 \
  --llm-base-url https://open.bigmodel.cn/api/coding/paas/v4 \
  --llm-model glm-5.2 \
  --api-key-env GLM_API_KEY
```

## Outputs

- `workflow_skills.jsonl`
- `validation_report.json`
- `metrics.json`

## Current Limitation

Public processed datasets provide partial gold labels. PET is useful for
activities and flow relations; MyFixit is useful for repair steps, tools, and
parts; MSPT is useful for scientific procedure operations and arguments. None
of them is a complete gold benchmark for Function IDs, ontology variables,
state predicates, typed data flow, exceptions, invariants, and execution tests.
Those fields require a curated Full Ontology Workflow benchmark.
