# Paper 1 Function Layer Benchmark

This directory is the benchmark construction area for Paper 1:

> autonomous construction of ontology-bound atomic Functions from API and
> operational artifacts.

The checked-in `.sample` files are a pilot fixture. They are useful for schema
checks and smoke runs, but they are not a complete benchmark.

Paper 1 cannot be evaluated with PET, MyFixit, MSPT, or OMIn directly. Those
datasets contain procedural text, actions, entities, and process relations, but
they do not contain API endpoints, OpenAPI schemas, execution traces, endpoint
bindings, or gold ontology-bound function contracts. They are more appropriate
for Paper 2.

## Required Layout

```text
dataset/function_layer_benchmarks/
  openapi/
    service_001.json
    service_002.json
  ontology.json
  ontology_overlay.jsonl
  gold_functions.jsonl
  traces.jsonl
```

For the checked-in pilot fixture:

```text
openapi/retail_order.sample.json
ontology.draft.sample.json
ontology.sample.json
ontology_overlay.sample.jsonl
gold_functions.sample.jsonl
traces.sample.jsonl
```

`ontology.draft.sample.json` is auto-generated from OpenAPI. `ontology.sample.json`
is the reviewed pilot ontology. The reviewed file may merge, rename, reject, or
enrich draft objects.

## Candidate Public Sources

- APIs.guru / OpenAPI Directory: public OpenAPI specifications.
- ToolFactory API Extraction Benchmark: API documentation and extraction
  labels, useful for endpoint and parameter extraction baselines.
- API KG / In-N-Out style resources: useful for parameter dependencies and API
  graph baselines.
- Locally available service artifacts: Huawei iDME HTML pages, Kafka function
  upsert messages, or internal OpenAPI files if available.

## Required Overlay

The public API sources alone are not enough for the Paper 1 claim. We still
need an ontology overlay:

- object types;
- object properties;
- endpoint-to-object bindings;
- parameter semantic roles;
- preconditions and effects where supported;
- error contracts;
- replay traces or executable mocks.

Without this overlay, the experiment is only API schema extraction, not
ontology Function Layer construction.

## Ontology Drafting

For public API corpora such as APIs.guru or ToolFactory/APIdoc2json, the first
step is to draft an object ontology from API artifacts:

```bash
python scripts/draft_object_ontology.py \
  --openapi dataset/function_layer_benchmarks/openapi/retail_order.sample.json \
  --output /private/tmp/ontology.draft.json
```

This draft extracts:

- schema objects from `components.schemas`;
- object aliases from path names, operation ids, summaries, and descriptions;
- properties and primitive types;
- state candidates from enum fields, status/state properties, operation text,
  error messages, and common lifecycle verbs;
- relation candidates from object-typed properties and path nesting;
- evidence references for every nontrivial candidate.

The draft is not gold. Review it before using it as `ontology.json`.

The overlay is the reviewable layer between raw API artifacts and final gold
functions:

```text
OpenAPI operation
  -> ontology_overlay candidate / reviewed record
  -> gold OntologyFunction label
```

Overlay fields:

- `endpoint_binding`: API operation identity;
- `candidate_function_id`: proposed canonical function id;
- `operation_kind`: function category;
- `bound_object_types`: ontology objects operated on;
- `parameter_bindings`: parameter to ontology property and semantic role;
- `output_bindings`: response object/property bindings;
- `preconditions`: evidence-backed validity conditions;
- `effects`: evidence-backed ontology state/property changes;
- `error_contract`: relevant error responses;
- `review_status`: `draft`, `reviewed`, or `rejected`;
- `evidence`: source references supporting nontrivial semantics.

Do not treat a `draft` overlay as gold. Only `reviewed` overlay records should
be converted into `gold_functions.jsonl`.

## Gold Annotation Unit

The unit is one API operation:

```text
METHOD + PATH + operationId
```

Each gold line should specify:

- endpoint binding;
- bound ontology object types;
- operation kind: `read`, `create`, `update`, `delete`, `compute`, or
  `external`;
- input parameter semantic roles;
- output object/property bindings;
- preconditions and effects when evidence exists;
- error contracts;
- evidence source references.

See `dataset/annotation_guidelines/paper1_function_layer_guideline.md`.

## Structural Validation

Validate the pilot fixture:

```bash
python scripts/validate_function_layer_benchmark.py \
  --openapi dataset/function_layer_benchmarks/openapi/retail_order.sample.json \
  --ontology dataset/function_layer_benchmarks/ontology.sample.json \
  --overlay dataset/function_layer_benchmarks/ontology_overlay.sample.jsonl \
  --gold dataset/function_layer_benchmarks/gold_functions.sample.jsonl \
  --traces dataset/function_layer_benchmarks/traces.sample.jsonl
```

Generate a first-pass overlay draft from an OpenAPI file and ontology:

```bash
python scripts/draft_ontology_overlay.py \
  --openapi dataset/function_layer_benchmarks/openapi/retail_order.sample.json \
  --ontology dataset/function_layer_benchmarks/ontology.sample.json \
  --output /private/tmp/ontology_overlay.draft.jsonl
```

Run the Paper 1 smoke experiment on the fixture:

```bash
python experiments/paper1_function_layer/run_experiment.py \
  --openapi dataset/function_layer_benchmarks/openapi/retail_order.sample.json \
  --ontology dataset/function_layer_benchmarks/ontology.sample.json \
  --gold dataset/function_layer_benchmarks/gold_functions.sample.jsonl \
  --traces dataset/function_layer_benchmarks/traces.sample.jsonl \
  --output-dir /private/tmp/paper1_function_layer_smoke
```

## Current Repository State

The repository currently contains useful industrial metadata and SOP/action
datasets under `dataset/`, but it does not yet contain a completed Paper 1
Function Layer benchmark in this directory.

The immediate benchmark-building task is to expand from this pilot to
100--200 API operations across 3--5 services/domains.
