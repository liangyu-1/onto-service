# Full Ontology Workflow Benchmark

This directory is the working area for Paper 2 benchmark construction.

Only files without the `.sample` suffix should be used for reported
experiments. The checked-in `.sample` files are schema examples and validator
fixtures, not benchmark data.

## Layout

```text
documents/
  *.jsonl
ontology/
  ontology.json
function_layer/
  functions.jsonl
annotations/
  workflow_skills.gold.jsonl
splits/
  train.txt
  dev.txt
  test.txt
```

## Construction Steps

1. Select 50--100 procedures from MyFixit, PET, MSPT, or internal SOPs.
2. Normalize each procedure into `documents/*.jsonl`.
3. Build or curate the object ontology for the selected domain.
4. Build a curated Function Layer before workflow annotation.
5. Annotate `OntologyWorkflowSkill` records using the guideline.
6. Run `scripts/validate_benchmark_annotations.py`.
7. Freeze train/dev/test splits before experiments.

Validator example:

```bash
python scripts/validate_benchmark_annotations.py \
  --annotations dataset/full_ontology_workflow_benchmark/annotations/workflow_skills.gold.jsonl \
  --ontology dataset/full_ontology_workflow_benchmark/ontology/ontology.json \
  --functions dataset/full_ontology_workflow_benchmark/function_layer/functions.jsonl
```

Sample-fixture check:

```bash
python scripts/validate_benchmark_annotations.py \
  --annotations dataset/full_ontology_workflow_benchmark/annotations/workflow_skills.gold.sample.jsonl \
  --ontology dataset/full_ontology_workflow_benchmark/ontology/ontology.sample.json \
  --functions dataset/full_ontology_workflow_benchmark/function_layer/functions.sample.jsonl
```

## Minimum First Version

For a first credible experiment:

- 20 MyFixit repair procedures;
- 10 PET process procedures;
- 10 MSPT synthesis procedures;
- at least one curated domain ontology;
- at least one curated Function Layer;
- full workflow annotations for all selected procedures.

## Non-goal

This directory is not an automatic output directory. It is for gold benchmark
construction and annotation review.
