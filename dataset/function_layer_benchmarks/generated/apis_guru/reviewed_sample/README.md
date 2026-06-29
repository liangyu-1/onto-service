# APIs.guru Reviewed Sample (Silver Labels)

This directory contains an auto-reviewed sample of 50 APIs selected from the
805 valid APIs.guru OpenAPI specs. It is intended as a starting point for
Paper 1 function-layer extraction experiments.

## Scope

- **Selected APIs**: 50 (diverse sample across operation-count tiers)
- **Reviewed overlays**: ~539
- **Gold functions**: ~539
- **Reviewed object types**: ~412
- **Status**: silver labels (rule-based auto-review; requires spot-check before
  being reported as gold)

## How the sample was built

1. **Download & validate specs** (`scripts/download_apis_guru.py`,
   `scripts/validate_apis_guru_specs.py`) produced 805 valid specs.
2. **Per-spec draft generation** (`scripts/batch_draft_apis_guru_annotations.py`)
   created `ontology.draft.json` and `ontology_overlay.draft.jsonl` for every
   spec.
3. **Diverse sampling** (`scripts/auto_review_apis_guru_sample.py`) deduplicated
   multi-version APIs and selected 50 APIs evenly across size tiers (small,
   medium, large, x-large).
4. **Auto-review** promoted high-confidence drafts to `reviewed` using REST
   heuristics:
   - operation_kind is read/create/update/delete
   - 1–3 bound object types supported by path segments or bindings
   - at least one parameter binding
   - clean REST path (≤7 segments)
   - identifiable parameter/output semantics
5. **Post-processing** fixed common identifier semantics (e.g. `vaultUuid` →
   identifier for `Vault`), linked outputs to bound object types, and injected
   inferred properties into the ontology so validation passes.
6. **Validation** (`scripts/validate_function_layer_benchmark.py`) confirmed all
   50 per-API reviewed packages are structurally consistent with their OpenAPI
   specs.

## Directory layout

```text
dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/
├── README.md                              # this file
├── summary.json                           # aggregate counts
├── selected_apis.json                     # list of sampled APIs
├── ontology.reviewed.json                 # aggregated reviewed ontology
├── ontology_overlay.reviewed.jsonl        # aggregated reviewed overlays
├── gold_functions.reviewed.jsonl          # aggregated gold functions
└── <api_name>/
    ├── ontology.reviewed.json
    ├── ontology_overlay.reviewed.jsonl
    └── gold_functions.reviewed.jsonl
```

## Important caveats

These labels are **silver**, not fully manual gold:

- Object boundaries may be over/under-split.
- `operation_kind` can be wrong for non-CRUD operations.
- `preconditions` and `effects` are heuristic placeholders.
- Some `bound_object_types` may miss objects only referenced by request/response
  schemas.
- Multi-version APIs were deduplicated by base name; domain coverage is not
  exhaustive.

Before using this as a final benchmark, spot-check a subset and correct
systematic errors.

## Manual review workflow

See `docs/paper1_function_layer_review_guidelines.md` for the review checklist.

Quick steps to review one API:

```bash
API=api.ebay.com_sell-account
python -B scripts/validate_function_layer_benchmark.py \
  --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/${API}.openapi.json \
  --ontology dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/${API}/ontology.reviewed.json \
  --overlay dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/${API}/ontology_overlay.reviewed.jsonl \
  --gold dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/${API}/gold_functions.reviewed.jsonl
```

Edit the per-API `ontology_overlay.reviewed.jsonl` to fix errors, then rerun
`scripts/overlay_to_gold_functions.py` to regenerate gold functions, or edit the
gold file directly.

## Extending the sample

To generate a larger or differently sampled set:

```bash
# Regenerate drafts for all specs (fast, ~1-2 minutes)
python -B scripts/batch_draft_apis_guru_annotations.py --skip-existing

# Create a new reviewed sample, e.g. 100 APIs with 30 overlays each
python -B scripts/auto_review_apis_guru_sample.py \
  --output-root dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample_100 \
  --max-overlays-per-api 30
```

## Validation summary

All 50 per-API reviewed packages passed structural validation against their
source OpenAPI specs.
