# Paper 1 Function Layer Review Guidelines

This document describes how to manually review auto-generated ontology overlays
and gold functions for the Paper 1 function-layer extraction benchmark.

## Files to review

For each API you are reviewing, open:

```text
<api>/ontology_overlay.reviewed.jsonl
```

Each line is one overlay record (one OpenAPI operation). If you change an
overlay, regenerate the gold function with `scripts/overlay_to_gold_functions.py`
or update the corresponding line in `<api>/gold_functions.reviewed.jsonl`.

## Review checklist

### 1. Endpoint binding

- `method` matches the OpenAPI operation.
- `path` matches the OpenAPI operation.
- `operation_id` is either the spec's `operationId` or a stable generated id.

If the binding does not point to a real operation, mark `review_status` as
`rejected`.

### 2. Operation kind

Allowed values: `read`, `create`, `update`, `delete`, `compute`, `external`.

- `GET` → usually `read`
- `POST` with create/add semantics → `create`
- `PUT`/`PATCH` → `update`
- `DELETE` → `delete`
- Search/analytics/action endpoints → `compute`
- Webhooks, health checks, admin callbacks → `external` (often rejected)

### 3. Bound object types

`bound_object_types` should list the domain objects the operation acts on.

- For `GET /orders/{order_id}` → `["Order"]`
- For `POST /orders/{order_id}/items` → `["Order", "OrderItem"]`
- Remove generic objects (e.g. `ApiResponse`, `Error`) unless they are genuine
  domain entities.
- Remove objects that are only technical containers.

### 4. Parameter bindings

For each input:

- `name` matches the OpenAPI parameter or request-body field.
- `location` is one of `path`, `query`, `header`, `requestBody`.
- `type` is correct (`string`, `integer`, `boolean`, `array`, `object`).
- `semantic_role`:
  - `identifier` for ids/uuids/keys that select a single resource
  - `state` for status/state fields
  - `policy` for approval/reason/permission fields
  - `measure` for amount/price/quantity
  - `time` for date/time fields
  - `payload` for everything else
- `ontology_property` should be `Object.property` when the parameter clearly
  corresponds to an ontology property; otherwise `null`.
- `required` matches the spec.

### 5. Output bindings

For each output:

- `name` describes the returned value.
- `type` is correct.
- `ontology_property` links to the returned object type when the response schema
  is a domain object (e.g. `Order`).

### 6. Preconditions

List conditions that must hold before the operation can succeed.

Examples:

- `Order.id == order_id`
- `Order exists`
- `Order.state in [pending, paid]`
- `User has permission X`

Keep preconditions simple and state them as boolean expressions.

### 7. Effects

List state changes caused by the operation.

Examples:

- `Order created`
- `Order.state -> cancelled`
- `Order.shipping_address -> address`

For `read` operations effects are usually empty.

### 8. Error contract

- Include the main client/server error codes from the OpenAPI spec.
- Add short descriptions if they help clarify preconditions.

### 9. Review status and notes

Set exactly one of:

- `reviewed` — you have checked the overlay and believe it is correct.
- `draft` — needs more work.
- `rejected` — not a real function (e.g. health check, callback, broken spec).

Add a `review_note` explaining any non-obvious decisions.

## Common correction patterns

| Problem | Fix |
|---------|-----|
| Generic `operation_kind` = `external` | Reclassify as read/create/update/delete/compute |
| Too many `bound_object_types` | Keep only domain objects actually operated on |
| Identifier param marked as `payload` | Change `semantic_role` to `identifier` |
| `ontology_property` is null for obvious id | Set to `Object.id` or `Object.{paramName}` |
| Output `ontology_property` is null | Link to the response schema object type |
| Missing preconditions/effects | Add based on operation kind and summary text |
| Path parameter not marked required | Set `required: true` |

## Regenerating gold functions after review

After editing overlays, regenerate the gold file:

```bash
python -B scripts/overlay_to_gold_functions.py \
  --overlay <api>/ontology_overlay.reviewed.jsonl \
  --output <api>/gold_functions.reviewed.jsonl
```

Then validate:

```bash
python -B scripts/validate_function_layer_benchmark.py \
  --openapi dataset/function_layer_benchmarks/raw/apis_guru/specs/<api>.openapi.json \
  --ontology <api>/ontology.reviewed.json \
  --overlay <api>/ontology_overlay.reviewed.jsonl \
  --gold <api>/gold_functions.reviewed.jsonl
```

## Aggregation

After several APIs are manually reviewed, you can rebuild the aggregate files
with:

```bash
python -B scripts/auto_review_apis_guru_sample.py \
  --sample-file dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/selected_apis.json \
  --max-overlays-per-api 1000
```

Set `--max-overlays-per-api` high enough to include all reviewed overlays per API.
