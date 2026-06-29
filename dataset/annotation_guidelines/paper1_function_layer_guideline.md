# Paper 1 Annotation Guideline: Ontology Function Layer

## Goal

Annotate gold `OntologyFunction` records from API/OpenAPI artifacts and an
object ontology. The gold record defines what a correct function-layer
constructor should output.

## Unit of Annotation

One API operation:

```text
METHOD + PATH + operationId
```

Examples:

```text
GET /orders/{order_id}
POST /orders/{order_id}/cancel
PATCH /customers/{customer_id}/address
```

## Required Fields

```json
{
  "function_id": "cancel_pending_order",
  "endpoint_binding": {
    "method": "POST",
    "path": "/orders/{order_id}/cancel",
    "operation_id": "cancelOrder"
  },
  "bound_object_types": ["Order"],
  "operation_kind": "delete|update|create|read|compute|external",
  "inputs": [
    {
      "name": "order_id",
      "type": "string",
      "semantic_role": "identifier",
      "ontology_property": "Order.order_id",
      "required": true
    }
  ],
  "outputs": [
    {
      "name": "order",
      "type": "object",
      "ontology_property": "Order",
      "required": false
    }
  ],
  "preconditions": ["Order.state == pending"],
  "effects": ["Order.state -> cancelled"],
  "error_contract": ["404: order not found", "409: order cannot be cancelled"],
  "evidence": [
    {
      "source_type": "openapi",
      "source_reference": "service.json#/paths/~1orders~1{order_id}~1cancel/post",
      "claim": "Cancels a pending order"
    }
  ]
}
```

## Field Definitions

`bound_object_types`: ontology object types the function operates on. Do not
use generic nouns such as `Data` or `Record` unless they exist in the ontology.

`operation_kind`:

- `read`: retrieves or observes state;
- `create`: creates an object;
- `update`: changes existing object properties or state;
- `delete`: deletes, cancels, removes, or invalidates;
- `compute`: returns derived value without object mutation;
- `external`: invokes external effect not captured by the ontology.

`semantic_role`:

- `identifier`: object id or lookup key;
- `attribute`: object property value;
- `state`: lifecycle/status field;
- `measure`: quantity, amount, score, price, count;
- `time`: date, time, duration;
- `policy`: reason code, approval flag, permission;
- `payload`: complex request body.

`preconditions`: conditions over ontology objects that must hold before the
function is valid.

`effects`: expected state or property changes after successful execution.

## Abstain Rules

Use an empty list only when the artifact provides no evidence. Do not infer
business semantics solely from common sense.

Mark unresolved cases in an annotation note when:

- the API name is ambiguous;
- documentation and schema conflict;
- no object type exists in the ontology;
- preconditions/effects are not recoverable from evidence.

## Quality Checks

Before accepting an annotation:

- every `ontology_property` must exist or be intentionally proposed;
- every precondition/effect must mention a known object type;
- endpoint binding must match the source API exactly;
- evidence must support every nontrivial semantic claim;
- annotator must not add semantics that are absent from all sources.
