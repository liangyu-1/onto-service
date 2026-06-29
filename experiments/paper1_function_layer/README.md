# Paper 1 Function Layer Experiments

This directory contains the experimental code for Paper 1:

> Autonomous Construction of Ontology Function Layers from Operational Artifacts

The code is intentionally separated from the Paper 2 workflow-induction and
Paper 3 robust-execution code. Paper 1 evaluates whether ontology-bound atomic
functions can be constructed from operational artifacts without per-function
human review.

## Dataset Requirement

Do not run this as a paper experiment until the Paper 1 benchmark has been
constructed and reviewed. The benchmark must contain API/OpenAPI artifacts,
object ontology, endpoint-to-object bindings, parameter roles, outputs,
preconditions, effects, error contracts, and optional traces.

The expected location is:

```text
dataset/function_layer_benchmarks/
  openapi/
  ontology.json
  gold_functions.jsonl
  traces.jsonl
```

See `dataset/annotation_guidelines/paper1_function_layer_guideline.md` for the
gold-label definition. Public procedural datasets such as PET, MyFixit, MSPT,
and OMIn are not valid primary Paper 1 datasets because they do not provide API
operation semantics.

## Inputs

Required:

- `--openapi`: one OpenAPI JSON file or a directory of `.json` files.
- `--ontology`: object-layer ontology JSON.

Optional:

- `--gold`: JSONL gold file for evaluation.
- `--traces`: JSONL execution traces or replay observations.
- `--output-dir`: directory for generated functions, reports, and metrics.

The ontology JSON should use this minimal shape:

```json
{
  "object_types": [
    {
      "id": "Order",
      "aliases": ["order"],
      "properties": [
        {"id": "order_id", "type": "string", "aliases": ["id"]}
      ],
      "states": ["pending", "delivered", "cancelled"]
    }
  ]
}
```

Gold JSONL should contain one expected function per line:

```json
{
  "function_id": "get_order",
  "endpoint_binding": {"method": "GET", "path": "/orders/{order_id}"},
  "bound_object_types": ["Order"],
  "inputs": [{"name": "order_id", "ontology_property": "Order.order_id", "semantic_role": "identifier"}],
  "outputs": [{"name": "order", "ontology_property": "Order"}],
  "preconditions": [],
  "effects": []
}
```

## Run

The paths below are the expected benchmark layout. They are not shipped as a
complete dataset in the current repository. See
`dataset/function_layer_benchmarks/README.md` for what must be prepared before
running a real Paper 1 experiment.

```bash
python experiments/paper1_function_layer/run_experiment.py \
  --openapi dataset/function_layer_benchmarks/openapi \
  --ontology dataset/function_layer_benchmarks/ontology.json \
  --gold dataset/function_layer_benchmarks/gold_functions.jsonl \
  --traces dataset/function_layer_benchmarks/traces.jsonl \
  --output-dir outputs/paper1_function_layer
```

If `--gold` is omitted, the pipeline still writes constructed functions and a
validation report, but metric fields that require gold labels are absent.

By default the runner uses deterministic discovery, alignment, validation, and
publication. This is useful for baselines and smoke checks. The full method can
enable evidence-bearing LLM contract generation:

```bash
export PAPER1_LLM_API_KEY=...

python experiments/paper1_function_layer/run_experiment.py \
  --openapi dataset/function_layer_benchmarks/openapi \
  --ontology dataset/function_layer_benchmarks/ontology.json \
  --gold dataset/function_layer_benchmarks/gold_functions.jsonl \
  --output-dir outputs/paper1_function_layer \
  --llm-base-url http://172.16.22.79:9999/v1 \
  --llm-model gemma4-31b \
  --api-key-env PAPER1_LLM_API_KEY
```

For the GLM-5.2 setup, use the OpenAI-compatible endpoint and the exact model
identifier exposed by the service. In earlier checks the model id was
`glm-5.2`.

```bash
export GLM_API_KEY=...

python experiments/paper1_function_layer/run_experiment.py \
  --openapi dataset/function_layer_benchmarks/openapi \
  --ontology dataset/function_layer_benchmarks/ontology.json \
  --gold dataset/function_layer_benchmarks/gold_functions.jsonl \
  --traces dataset/function_layer_benchmarks/traces.jsonl \
  --output-dir outputs/paper1_function_layer_glm52 \
  --llm-base-url https://open.bigmodel.cn/api/coding/paas/v4 \
  --llm-model glm-5.2 \
  --api-key-env GLM_API_KEY
```

The API key is read from the environment and must not be committed. Do not pass
keys directly on the command line when saving shell history or logs.

## Outputs

- `published_functions.jsonl`: accepted ontology functions.
- `all_candidates.jsonl`: all generated candidates with status.
- `validation_report.json`: validation errors and evidence coverage.
- `metrics.json`: gold-based metrics when `--gold` is available.

## Non-goals

- This directory does not run Paper 2 workflow induction.
- This directory does not run Paper 3 agent execution.
- It does not fabricate synthetic benchmark results when gold labels or replay
  traces are missing.
