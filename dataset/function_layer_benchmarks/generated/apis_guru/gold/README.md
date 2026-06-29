# Paper 1 Gold Label Pilot

This directory contains manually reviewed **gold labels** for a small pilot set
of APIs from the APIs.guru collection.

## APIs included

| API | Domain | Object types | Gold functions |
|-----|--------|--------------|----------------|
| `1password.local_connect` | password vault management | 3 | 11 |
| `trello.com` | project management (board/list/card) | 3 | 12 |
| `sendgrid.com` | email/marketing campaigns | 5 | 18 |
| **Total** | | **11** | **41** |

## Files

```text
dataset/function_layer_benchmarks/generated/apis_guru/gold/
├── README.md
├── ontology.gold.json              # merged gold object ontology
├── ontology_overlay.gold.jsonl     # 41 reviewed overlays
├── gold_functions.gold.jsonl       # 41 gold functions
└── summary.json
```

Per-API gold files are also kept under:

```text
dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/<api>/
├── ontology.gold.json
├── ontology_overlay.gold.jsonl
└── gold_functions.gold.jsonl
```

## Review status

All overlay records in this directory have `review_status: "gold"` and were
manually curated from the corresponding OpenAPI spec. They are intended as:

- High-quality training/validation signal for function extraction models
- A benchmark seed for evaluating draft-to-gold pipelines
- Examples for extending the review guidelines

## Validation

```bash
for api in 1password.local_connect trello.com sendgrid.com; do
  python -B scripts/validate_function_layer_benchmark.py \
    --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/${api}.openapi.json \
    --ontology dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/${api}/ontology.gold.json \
    --overlay dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/${api}/ontology_overlay.gold.jsonl \
    --gold dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/${api}/gold_functions.gold.jsonl
done
```

All three APIs pass structural validation.

## Extending

To add another API as gold:

1. Manually create `<api>/ontology.gold.json` and `<api>/ontology_overlay.gold.jsonl`.
2. Run `scripts/overlay_to_gold_functions.py` to generate `gold_functions.gold.jsonl`.
3. Validate with `scripts/validate_function_layer_benchmark.py`.
4. Re-run the aggregation script or manually update this directory.
