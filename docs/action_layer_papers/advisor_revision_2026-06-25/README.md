# Advisor-Revision Paper Set

Date: 2026-06-25

This directory contains a clean redesign of the three action-layer papers after
the advisor discussion. It does not overwrite the earlier indexing,
collaborative-ontogenesis, or ontology-admissibility drafts.

## Revised Dissertation Spine

```text
heterogeneous operational artifacts
  -> Paper 1: autonomous ontology Function Layer construction
  -> Paper 2: ontology-grounded Workflow Skill induction
  -> Paper 3: adversarially robust and controllable execution
```

The term "Palantir-like" is used only as an industrial analogy. The papers do
not claim to reproduce Palantir Foundry. Their scientific objects are open,
platform-independent representations and measurable learning or execution
problems.

## Files

- `research_design.zh.md`: Chinese research plan, paper boundaries, measurable
  hypotheses, dataset strategy, and implementation implications.
- `paper1_ontology_function_extraction.md`: atomic function extraction from API
  documentation under an existing object ontology.
- `paper2_ontology_workflow_induction.md`: workflow/skill induction from SOPs
  by composing the atomic functions produced by Paper 1.
- `paper3_controllable_workflow_execution.md`: workflow-conformant execution
  and bounded recovery under state uncertainty and tool failures.
- `references.bib`: shared bibliography.
- `references/`: downloaded papers selected for deep reading.

## Important Scope Decisions

1. Paper 1 studies automatic construction of the Function Layer as part of
   ontology construction. No per-function expert review is allowed during
   inference; human gold annotation remains necessary for evaluation.
2. Paper 2 composes ontology functions into state-transition workflows. Object
   types, properties, predicates, effects, variables, and outputs must all be
   ontology grounded.
3. Paper 3 assumes a workflow has already been published. It studies robustness
   and controllability under benign noise and adaptive attacks.
4. Existing Paper 3 code is reusable only as infrastructure. Its former
   ontology-admissibility claim is not automatically evidence for the revised
   paper.

## Validation Status

The files are research designs and paper-section drafts, not completed empirical
papers. Every result statement is therefore written as a hypothesis, planned
analysis, or required decision rule unless it is explicitly tied to an existing
experiment.
