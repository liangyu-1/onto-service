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

## Initial Reviewed Annotation

The first manually reviewed Paper 1 annotation package is under:

```text
twilio_conversations_v1/
```

It contains:

```text
ontology.reviewed.json
ontology_overlay.reviewed.jsonl
gold_functions.reviewed.jsonl
```

Scope:

- reviewed core object ontology for Twilio Conversations;
- 15 reviewed ontology-bound atomic functions;
- coverage over Conversation, Message, and Participant operations;
- no execution traces yet.

Validation:

```bash
python -B scripts/validate_function_layer_benchmark.py \
  --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/twilio_conversations_v1.openapi.json \
  --ontology dataset/function_layer_benchmarks/generated/apis_guru/twilio_conversations_v1/ontology.reviewed.json \
  --overlay dataset/function_layer_benchmarks/generated/apis_guru/twilio_conversations_v1/ontology_overlay.reviewed.jsonl \
  --gold dataset/function_layer_benchmarks/generated/apis_guru/twilio_conversations_v1/gold_functions.reviewed.jsonl
```

Expected structural result:

```json
{
  "ok": true,
  "openapi_operation_count": 101,
  "overlay_count": 15,
  "gold_function_count": 15,
  "trace_count": 0,
  "error_count": 0
}
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
