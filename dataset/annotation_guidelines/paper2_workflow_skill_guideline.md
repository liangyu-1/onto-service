# Paper 2 Annotation Guideline: Ontology Workflow Skill

## Goal

Annotate gold `OntologyWorkflowSkill` records from procedural documents,
object ontology, and a curated Function Layer.

The annotation target is not a generic process graph. Every executable node
must be grounded to a function ID, and every variable/condition/data-flow edge
must be typed by the ontology.

## Input Package

Each annotation item must include:

```text
document.json
ontology.json
function_layer.jsonl
```

The annotator must not invent a function that is absent from `function_layer`.
If the document requires an unavailable function, mark the node as
`UnresolvedCapability`.

## Output Schema

```json
{
  "skill_id": "repair_battery_replacement",
  "source_id": "myfixit_38109",
  "goal_predicate": "Battery.replaced == true",
  "typed_inputs": [
    {"name": "device", "type": "Device"}
  ],
  "typed_outputs": [
    {"name": "battery", "type": "Battery"}
  ],
  "object_variables": [
    {"name": "v_device", "type": "Device"},
    {"name": "v_battery", "type": "Battery"}
  ],
  "nodes": [
    {
      "node_id": "n1",
      "node_type": "OntologyFunctionCall",
      "text": "Unscrew both side panel 2mm screws using the T3 Torx screwdriver.",
      "function_id": "remove_fastener",
      "object_variables": ["v_device"],
      "state_predicates": [],
      "evidence": {"start": 0, "end": 65}
    }
  ],
  "control_edges": [
    {"source": "n1", "target": "n2", "edge_type": "sequence", "condition": null}
  ],
  "dataflow_edges": [
    {"source": "n1.output.fastener", "target": "n2.input.fastener", "edge_type": "data"}
  ],
  "invariants": [
    "Do not damage electronics"
  ],
  "exception_paths": [
    {"source": "n3", "target": "n_reheat", "edge_type": "exception", "condition": "adhesive_loose == false"}
  ],
  "unresolved_regions": []
}
```

## Node Types

- `OntologyFunctionCall`: executable function call grounded to Function Layer.
- `Decision`: branch or condition evaluation.
- `UserInteraction`: request missing information or confirmation.
- `End`: terminal node.
- `UnresolvedCapability`: required operation not present in Function Layer.

## Annotation Rules

### Function Grounding

Choose the most specific function whose:

- action semantics match the text;
- target object type matches the document object;
- required inputs can be supplied by document, workflow input, prior outputs, or user interaction.

If no function matches, use `UnresolvedCapability`.

### Object Variables

Create stable variables for objects that persist across steps:

```text
v_watch: Device
v_battery: Battery
v_rear_cover: Cover
```

Do not create a new variable for every mention of the same object.

### Data Flow

Annotate data flow when one step produces an object/value used by another
step. Do not add data-flow edges merely because steps are sequential.

### State Predicates

Use state predicates for conditions such as:

- after the adhesive is loosened;
- if receipts are missing;
- once the user confirms;
- before removing the battery.

### Invariants

Annotate safety, policy, or global constraints:

- do not damage electronics;
- do not sew the pocket closed;
- keep the device powered off;
- must obtain confirmation before mutation.

### Exception Paths

Annotate exception paths only when the document gives an alternative branch or
recovery action.

## Public Dataset Limitations

PET can support activities and control-flow labels.
MyFixit can support repair steps, tools, and parts.
MSPT can support procedural operations and typed arguments.
OMIn can support maintenance entity grounding.

None of them provides complete gold labels for ontology Function IDs,
state predicates, typed data flow, invariants, exceptions, and execution tests.
Those fields require manual annotation.
