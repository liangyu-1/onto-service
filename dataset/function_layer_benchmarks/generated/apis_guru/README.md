# APIs.guru Ontology Drafts

This directory contains generated Paper 1 ontology artifacts derived from the
downloaded APIs.guru OpenAPI subset.

## Generated Ontology Drafts

The following command generated one draft ontology per API system:

```bash
python -B scripts/draft_object_ontology.py \
  --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/<api>.openapi.json \
  --output dataset/function_layer_benchmarks/generated/apis_guru/<api>/ontology.draft.json \
  --name <api>_ontology_draft
```

Summary:

```text
atlassian_jira: 679 object candidates, 520 relation candidates
box_com: 225 object candidates, 82 relation candidates
docusign: 627 object candidates, 4050 relation candidates
github_com: 750 object candidates, 1836 relation candidates
sendgrid: 247 object candidates, 149 relation candidates
slack_com: 222 object candidates, 68 relation candidates
stripe_com: 837 object candidates, 662 relation candidates
twilio_conversations_v1: 75 object candidates, 31 relation candidates
xero_accounting: 140 object candidates, 241 relation candidates
```

These files are machine-generated drafts. They are not gold ontologies.

## Reviewed Core Annotation Subsets

Each API directory now contains a reviewed core annotation package:

```text
ontology.reviewed.json
ontology_overlay.reviewed.jsonl
gold_functions.reviewed.jsonl
```

Scope and counts:

```text
atlassian_jira: 3 reviewed object types, 13 reviewed functions
box_com: 3 reviewed object types, 13 reviewed functions
docusign: 3 reviewed object types, 8 reviewed functions
github_com: 3 reviewed object types, 11 reviewed functions
sendgrid: 4 reviewed object types, 14 reviewed functions
slack_com: 3 reviewed object types, 8 reviewed functions
stripe_com: 3 reviewed object types, 14 reviewed functions
twilio_conversations_v1: 9 reviewed object types, 15 reviewed functions
xero_accounting: 3 reviewed object types, 13 reviewed functions
```

Total reviewed seed labels:

```text
34 reviewed object types
109 reviewed ontology-bound atomic functions
```

These reviewed files are core benchmark seeds. They intentionally cover stable,
high-value resource families such as issue/comment/project, file/folder/comment,
envelope/template, repository/issue/pull request, contact/list/segment,
conversation/message, customer/payment intent/invoice, and
account/contact/invoice. They are not exhaustive labels for every operation in
the source OpenAPI files.

The non-Twilio reviewed files were generated from the explicit configuration in:

```text
scripts/build_reviewed_api_core_annotations.py
```

That script verifies that every selected endpoint exists in the corresponding
OpenAPI file before writing the reviewed files. It does not use an LLM.

Validation:

```bash
python -B scripts/validate_function_layer_benchmark.py \
  --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/<api>.openapi.json \
  --ontology dataset/function_layer_benchmarks/generated/apis_guru/<api>/ontology.reviewed.json \
  --overlay dataset/function_layer_benchmarks/generated/apis_guru/<api>/ontology_overlay.reviewed.jsonl \
  --gold dataset/function_layer_benchmarks/generated/apis_guru/<api>/gold_functions.reviewed.jsonl
```

All nine reviewed subsets have passed structural validation:

```text
atlassian_jira: ok, 13 overlay records, 13 gold functions
box_com: ok, 13 overlay records, 13 gold functions
docusign: ok, 8 overlay records, 8 gold functions
github_com: ok, 11 overlay records, 11 gold functions
sendgrid: ok, 14 overlay records, 14 gold functions
slack_com: ok, 8 overlay records, 8 gold functions
stripe_com: ok, 14 overlay records, 14 gold functions
twilio_conversations_v1: ok, 15 overlay records, 15 gold functions
xero_accounting: ok, 13 overlay records, 13 gold functions
```

Smoke experiment:

```bash
python -B experiments/paper1_function_layer/run_experiment.py \
  --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/twilio_conversations_v1.openapi.json \
  --ontology dataset/function_layer_benchmarks/generated/apis_guru/twilio_conversations_v1/ontology.reviewed.json \
  --gold dataset/function_layer_benchmarks/generated/apis_guru/twilio_conversations_v1/gold_functions.reviewed.jsonl \
  --output-dir /private/tmp/paper1_twilio_smoke
```

The smoke run proves that the pipeline can consume the real OpenAPI file and
the reviewed gold subset. It is not a strong method result yet: the current
baseline publishes many unreviewed candidates and has poor effect/precondition
matching.

## Review Rule

Use `ontology.draft.json` only as a candidate source. For benchmark labels,
create reviewed files:

```text
ontology.reviewed.json
ontology_overlay.reviewed.jsonl
gold_functions.reviewed.jsonl
```

Do not report draft-only fields as gold.
