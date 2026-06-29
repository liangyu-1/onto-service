# Benchmark Construction Plan

The experiments must not start from empty or fake benchmark paths. The correct
order is:

```text
source documents / API artifacts
  -> domain ontology
  -> function layer
  -> annotation guideline
  -> gold annotations
  -> validation
  -> experiments
```

There are two different benchmark tracks.

## Track 1: Paper 1 Function Layer Benchmark

Paper 1 evaluates automatic construction of ontology-bound atomic functions.

Required material:

- API documentation or OpenAPI specs;
- object ontology;
- endpoint-to-object gold bindings;
- parameter semantic roles;
- output object/property bindings;
- preconditions;
- effects;
- error contracts;
- execution traces or replay/mocks when available.

This track cannot use PET/MyFixit/MSPT as the primary dataset because those
datasets do not contain API endpoint semantics.

## Track 2: Paper 2 Workflow Skill Benchmark

Paper 2 evaluates conversion from procedural documents into ontology-grounded
workflow skills.

Required material:

- procedural document;
- object ontology;
- curated function layer;
- workflow nodes grounded to function IDs;
- object variables;
- typed data-flow edges;
- control-flow edges;
- state predicates;
- invariants;
- exception paths;
- executable test cases when available.

PET/MyFixit/MSPT/OMIn can provide partial public evidence, but a complete
workflow benchmark still requires additional annotation.

## Minimum Viable Annotation Size

A defensible first benchmark should contain:

- Paper 1: 100--200 API operations from 3--5 domains/services.
- Paper 2: 50--100 procedures, with at least 10--20 fully annotated workflows.

Anything smaller is useful for smoke tests but weak for paper claims.

## Annotation Roles

- Annotator A: creates first-pass annotation.
- Annotator B: independently reviews object/function/state/data-flow fields.
- Adjudicator: resolves conflicts and records final gold.

For the first version, one annotator plus one reviewer is acceptable, but the
paper must report this limitation.
