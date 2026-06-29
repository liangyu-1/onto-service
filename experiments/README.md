# Experiment Lines

The dissertation experiments are split into two independent lines so that
method claims remain attributable.

## Required Benchmark Order

Do not start long-running experiments until the benchmark package is prepared.
The code in this directory assumes the following inputs already exist:

```text
documents / API artifacts
  -> reviewed object ontology
  -> curated or Paper1-generated Function Layer
  -> gold workflow/function annotations
  -> validated train/dev/test splits
```

For annotation rules and sample schemas, see:

- `dataset/annotation_guidelines/`
- `dataset/full_ontology_workflow_benchmark/`
- `dataset/function_layer_benchmarks/`

Without these files, a run is only a smoke test or engineering check. It is not
paper evidence.

## Server A: Paper 2 + Paper 3

Server A evaluates workflow induction and robust execution:

```text
Object Layer + curated Function Layer + procedural document
  -> Paper 2: Ontology Workflow Skill
  -> Paper 3: robust and controllable workflow execution
```

Paper 2 should first use a gold or curated Function Layer. This isolates
workflow-induction errors from Paper 1 function-construction errors.

Paper 3 should first use gold or validated workflows. Extracted workflows are a
cascade setting, not the primary robustness evidence.

Current Server A code:

```text
experiments/paper2_workflow_skill/
```

Paper 3 robust-execution code has not been rebuilt after the redesign. The
previous tau/action-bank implementation was removed because it targeted the
old Action IR framing rather than the current Workflow Skill / Execution
Envelope framing.

## Server B: Paper 1

Server B evaluates autonomous Function Layer construction:

```text
OpenAPI / API docs / SDK signatures / examples / traces + Object Layer
  -> Paper 1: ontology-bound Atomic Function Layer
```

The Paper 1 output consumed by Server A is:

```text
outputs/paper1_function_layer/published_functions.jsonl
```

Current Server B code:

```text
experiments/paper1_function_layer/
```

Only functions with `status = "published"` should be used by Paper 2 cascade
experiments. Abstained and rejected candidates are evaluation artifacts, not
workflow inputs.

## Cascade Evaluation

After Paper 1 produces a published Function Layer, Server A can run:

```text
Paper1-generated Function Layer
  -> Paper 2 Workflow Skill induction
  -> Paper 3 robust execution
```

These cascade results show whether the three-paper system composes. They should
not replace the isolated main experiments for Paper 2 or Paper 3.
