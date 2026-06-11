# 工业元数据语义增强与 SOP-to-Action 抽取：论文草案

日期：2026-05-14

## 论文一：面向工业元数据的证据驱动语义增强

### Introduction

Industrial metadata is the foundation of industrial data governance, semantic integration, and ontology-driven applications. In manufacturing and industrial software systems, metadata commonly appears as object models, tables, fields, enumerations, lifecycle states, relations, API schemas, and business object definitions maintained by MES, PLM, ERP, QMS, and EAM systems. Such metadata is structurally reliable because it is usually governed by information systems and operational databases. However, it is often semantically incomplete. Field names such as `status`, `type`, `result`, and `reason_code` may encode critical business semantics, yet their definitions, valid interpretations, operational constraints, and lifecycle implications are rarely explicit in machine-readable metadata.

Industrial documents provide complementary knowledge. Standards, manuals, process specifications, quality documents, and work instructions often contain definitions, aliases, business rules, constraints, lifecycle explanations, role responsibilities, and operational semantics. However, directly converting such documents into ontology structures with large language models (LLMs) is risky. Document-derived knowledge may be ambiguous, context-dependent, version-sensitive, and difficult to verify. Unconstrained generation can introduce unsupported concepts, duplicate existing metadata elements, or attach incorrect semantics to operational fields.

This paper therefore studies metadata semantic enrichment rather than metadata extraction or free-form ontology construction. Given an existing industrial metadata schema and a corpus of related documents, the objective is to generate an evidence-grounded enrichment layer attached to existing metadata elements. The original metadata schema is preserved; LLMs are used only to propose semantic annotations under schema, target, and evidence constraints.

Existing benchmarks and resources motivate this formulation. Ontology-constrained extraction benchmarks such as Text2KGBench demonstrate the importance of evaluating conformance to a given ontology rather than only text-level extraction quality [CITATION: Text2KGBench]. Industrial modeling resources such as AAS templates, OPC UA NodeSets, SysML examples, AAS BoM templates, and process planning materials provide schema-level industrial semantics, but they do not directly provide gold labels for evidence-grounded metadata enrichment [CITATION: AAS; CITATION: OPCUA; CITATION: SYSML]. This gap motivates a method that treats industrial metadata as the stable target structure and documents as evidence sources.

The central research question is:

```text
Given an existing industrial metadata schema M and a document corpus D,
how can an LLM generate an evidence-grounded enrichment layer E
for elements in M without modifying M?
```

### Methodology

#### Problem Formulation

Let the existing industrial metadata be denoted as:

```text
M = (O, A, R, S)
```

where `O` is the set of metadata objects, `A` is the set of attributes or fields, `R` is the set of relations, and `S` is the set of enumerations, states, or lifecycle values. Let `D = {d_1, ..., d_n}` be a corpus of industrial documents. The task is to construct an enrichment layer:

```text
E = {e_i}
```

where each enrichment `e_i` is attached to an existing metadata element `m_i ∈ M` and is supported by evidence from `D`.

Each enrichment is represented as:

```json
{
  "target": "metadata_element_id",
  "type": "definition|alias|constraint|business_rule|lifecycle_semantics|role_semantics|parameter_semantics",
  "content": {},
  "evidence": {
    "document_id": "",
    "span": ""
  }
}
```

The method must satisfy three constraints:

1. **Schema preservation**: no enrichment may modify the original metadata schema `M`.
2. **Target grounding**: every enrichment must be attached to an existing element in `M`.
3. **Evidence grounding**: every enrichment must be supported by an explicit span in `D`.

#### Method Overview

The proposed method consists of three components: metadata profiling, evidence-grounded LLM enrichment, and validation.

```text
Existing Metadata M
        +
Document Corpus D
        ↓
Metadata-aware Evidence Retrieval
        ↓
Constrained LLM Enrichment
        ↓
Validation and Repair
        ↓
Metadata Enrichment Layer E
```

#### Metadata-aware Evidence Retrieval

For each metadata element `m ∈ M`, the system constructs a retrieval query from its name, owner object, data type, existing description, neighboring fields, and known aliases. The retriever returns a small set of candidate evidence spans:

```text
C_m = retrieve(m, D)
```

This step does not infer new semantics. Its only purpose is to collect document evidence likely to explain or constrain the target metadata element.

#### Constrained LLM Enrichment

The LLM receives `(m, C_m, T)`, where `T` is the allowed enrichment type set. The model is instructed to generate only annotations for the given metadata element. It is not allowed to introduce new metadata fields, new classes, or new lifecycle states unless they are marked as unresolved candidates.

The output is a set of candidate enrichments:

```text
E_m = LLM(m, C_m, T)
```

The prompt includes:

- the target metadata element;
- its owner object and local schema context;
- retrieved evidence spans;
- the allowed enrichment schema;
- a requirement that every claim cite an evidence span.

#### Validation

A validator filters or repairs candidate enrichments. An enrichment is accepted only if:

```text
target(e) ∈ M
evidence(e) ⊆ D
type(e) ∈ T
consistent(e, M) = true
```

Validation includes:

| Constraint | Description |
|---|---|
| Target validity | The target metadata element must exist in `M`. |
| Evidence validity | The evidence span must be present in the retrieved document context. |
| Type validity | The enrichment type must be compatible with the target element type. |
| Consistency | The enrichment must not contradict existing enumerations, states, units, or constraints. |
| Preservation | The original metadata schema must remain unchanged. |

Invalid outputs are either rejected, repaired by a constrained repair prompt, or routed to human review. The final result is an enrichment layer separated from the original metadata schema, enabling versioning, rollback, review, and downstream consumption by retrieval, reasoning, and SOP-to-action generation systems.

## 论文二：基于增强元数据约束的 SOP-to-Action 抽取

### Introduction

Standard Operating Procedures (SOPs), work instructions, maintenance procedures, and business rule documents describe how operations should be performed. However, SOPs are written for human interpretation and cannot be directly executed by industrial software systems. To support workflow automation, ontology actions, business operations, or API invocation, SOPs must be transformed into structured action representations with explicit actors, target objects, parameters, preconditions, effects, state transitions, and evidence.

Directly generating platform-specific actions from SOP text is unreliable. SOPs frequently omit explicit subjects, rely on domain-specific terminology, distribute conditions and effects across multiple sentences, and contain exceptions or implicit state changes. Moreover, action formats differ across target platforms. A platform-neutral intermediate representation is therefore required before compiling SOP-derived actions into concrete systems.

This paper builds on the enrichment layer produced by the first paper. The enriched metadata provides definitions, aliases, constraints, lifecycle semantics, role semantics, and parameter semantics that constrain SOP interpretation. For example, it helps determine whether “stop equipment” corresponds to an equipment state transition, whether “failed inspection” maps to an inspection result enumeration, and whether a condition can be evaluated from available metadata fields.

The research question is:

```text
Given SOP documents P and enriched industrial metadata E,
how can an LLM produce metadata-aligned, evidence-grounded, and verifiable Action IR?
```

Related benchmarks motivate different aspects of this task. PET supports process element extraction [CITATION: PET]. BREX/BPRF-style resources support Chinese condition-action rule extraction [CITATION: BREX]. PAGED motivates procedural graph extraction from documents [CITATION: PAGED]. WONDERBREAD provides workflow-to-SOP and trace-oriented evaluation settings [CITATION: WONDERBREAD]. SOP-Bench emphasizes tool execution and verifier-based evaluation of SOP-following agents [CITATION: SOP-Bench]. None of these benchmarks alone solves metadata-aligned SOP-to-action extraction, but they motivate the decomposition into graph extraction, metadata alignment, and action validation.

### Methodology

#### Problem Formulation

Let `P = {p_1, ..., p_n}` denote SOP or procedural documents. Let `M` be the original metadata schema and `E` be the enrichment layer generated by the first paper. The task is to generate an action set:

```text
A = {a_i}
```

where each action `a_i` is derived from an SOP evidence span, aligned to metadata elements in `M`, and constrained by semantic enrichments in `E`.

Each action is represented in a platform-neutral Action IR:

```json
{
  "name": "stopEquipment",
  "target": "Equipment",
  "actor": "Operator",
  "parameters": [],
  "preconditions": [],
  "effects": [],
  "state_transitions": [],
  "evidence": {
    "document_id": "",
    "span": ""
  }
}
```

The method must satisfy four constraints:

1. **Evidence grounding**: every action must be supported by an SOP span.
2. **Metadata alignment**: action targets, parameters, and states must align to `M`.
3. **Semantic consistency**: preconditions and effects must respect enrichments in `E`.
4. **Platform neutrality**: the generated action is an intermediate representation, not a platform-specific API call.

#### Method Overview

The proposed method has four components: procedural graph extraction, metadata alignment, Action IR compilation, and validation.

```text
SOP Documents P
        +
Metadata M
        +
Enrichment Layer E
        ↓
LLM Procedural Graph Extraction
        ↓
Metadata Alignment
        ↓
Action IR Compilation
        ↓
Validation and Repair
        ↓
Verified Action Layer
```

#### Procedural Graph Extraction

The model first transforms SOP text into a procedural graph rather than directly generating actions. A procedural graph contains steps, actors, objects, conditions, effects, dependencies, and exceptions:

```json
{
  "steps": [
    {
      "id": "s1",
      "actor": "operator",
      "operation": "stop equipment",
      "object": "equipment",
      "condition": "temperature exceeds 80 C",
      "effect": "equipment is stopped",
      "next": ["s2"],
      "evidence": ""
    }
  ]
}
```

This intermediate graph separates process understanding from action compilation and reduces the risk of prematurely producing invalid actions.

#### Metadata Alignment

Each graph element is linked to metadata using aliases, definitions, object context, lifecycle semantics, and constraints from `E`. Alignment maps surface forms in SOP text to metadata elements:

```text
align("machine", E) -> Equipment
align("failed inspection", E) -> InspectionResult.FAIL
align("stop equipment", E) -> Equipment.status = Stopped
```

Unresolved or ambiguous alignments are not forced. They are marked for repair or human review.

#### Action IR Compilation

After alignment, the procedural graph is compiled into Action IR. The compilation maps graph fields to action fields:

| Procedural graph | Action IR |
|---|---|
| actor | actor |
| object | target |
| condition | preconditions |
| effect | effects |
| dependency / branch | state transition or workflow edge |
| evidence | evidence |

The compiler only emits an action if the step has an identifiable target, actor or role, evidence span, and explicit operational effect.

#### Validation

The validator accepts an action only if:

```text
target(a) ∈ M
evidence(a) ⊆ P
consistent(a, M, E) = true
```

Validation checks include:

| Constraint | Description |
|---|---|
| Schema validity | Required Action IR fields must be present. |
| Target validity | The action target must align to a metadata object. |
| Parameter validity | Parameters must align to known fields or reviewable candidates. |
| Precondition validity | Preconditions must be evaluable from metadata fields or explicit evidence. |
| Effect validity | Effects must be explicit state changes, record creation, notifications, or external calls. |
| Transition validity | State transitions must respect lifecycle semantics in `E`. |
| Evidence validity | Each action must cite the SOP span that supports it. |

Invalid actions are repaired with a constrained prompt or routed to human review. The accepted actions form a verified action layer that can later be compiled into platform-specific business operations, workflow tasks, or API calls.

