# Inducing Executable Ontology Workflow Skills from Procedural Documents

## Abstract

Procedural documents describe how objects are inspected, transformed, and
coordinated through multiple operations. Existing process-extraction methods
recover activities and control-flow relations, but their nodes are commonly
text spans rather than operations grounded in an ontology. We formulate
**ontology workflow skill induction**: given an Object Layer, an ontology
Function Layer, and an SOP or user manual, construct a typed state-transition
workflow whose nodes reference ontology functions, variables reference ontology
objects and properties, conditions are ontology predicates, and edges are
constrained by effect--precondition compatibility. We propose a structure-aware
framework that jointly grounds procedural units to functions and objects,
constructs control and data flow, infers state transitions and exception paths,
and validates the result through ontology reasoning and sandbox execution. The
output is an executable Workflow Skill rather than a textual process summary or
generic BPMN graph. Experiments combine procedural graph, process extraction,
maintenance, and SOP execution datasets with a new Full Ontology Workflow
benchmark. Evaluation explicitly ablates the Object Layer, Function Layer,
state predicates, typed data flow, and execution validation to determine
whether ontology grounding provides measurable value.

## 1. Introduction

Standard operating procedures, maintenance manuals, user instructions, and
service playbooks encode reusable operational knowledge. They describe which
operations should be performed, which objects those operations affect, what
state enables each step, how information flows between steps, and how the
procedure changes under exceptional conditions.

Automatic process extraction has progressed from identifying activities and
actors to constructing procedural graphs and BPMN-like models
[@bellan2022pet; @neuberger2024universal; @du2024paged]. Agent-oriented work
executes SOPs through LLM planning and tool calls
[@kulkarni2025agents; @nandi2025sopbench]. These approaches leave a critical
gap. A process graph can be structurally plausible while referring to
operations that do not exist, passing the wrong object between steps, or
violating the state semantics of the underlying enterprise system.

This paper studies Workflow construction inside an operational ontology. Its
inputs are:

1. an **Object Layer** containing object types, properties, relations, and state
   predicates;
2. a **Function Layer** containing ontology-bound atomic functions, produced by
   Paper 1 or manually curated for controlled experiments;
3. a procedural document.

The output is an **Ontology Workflow Skill**. Every function-call node
references a Function Layer identifier. Every variable has an ontology type.
Conditions and invariants are predicates over object properties and relations.
Data-flow edges connect function outputs to compatible downstream inputs.
Control-flow edges are checked against function preconditions and effects. The
workflow therefore describes a state transition over ontology objects, not only
a sequence of textual activities.

This distinction is the primary scientific claim. The ontology is not used as
additional prompt context. It acts as the workflow's type system, world-state
model, and composition constraint. Removing it must measurably reduce object
consistency, state correctness, or executability; otherwise the method is only
a renamed procedural-graph extractor.

The central technical difficulty is joint non-local grounding. A step can omit
its object because the object was introduced several pages earlier. A value
returned by one function can become the target identifier of another.
Warnings can impose global invariants. A later exception clause can invalidate
the apparent normal transition of an earlier step. Independent node extraction
cannot reliably recover these dependencies.

We propose a joint document--ontology--function framework. It reconstructs the
document hierarchy, identifies procedural units, retrieves candidate objects
and functions, jointly predicts nodes and typed variables, builds control and
data-flow edges, and verifies the graph using ontology constraints and
execution. Unsupported operations remain unresolved rather than being invented.

We address:

- **RQ1:** Does Object Layer grounding improve object identity, state
  conditions, and typed data flow?
- **RQ2:** Does Function Layer grounding reduce hallucinated operations and
  improve executable workflow rate?
- **RQ3:** Does effect--precondition reasoning improve control-flow and missing
  dependency recovery?
- **RQ4:** Which structural and ontology metrics predict downstream execution
  success?
- **RQ5:** How do errors from an automatically constructed Function Layer
  propagate into Workflow Skills?

The contributions are:

1. a formal target representation for ontology-grounded Workflow Skills;
2. a joint method for function, object, state, data-flow, and control-flow
   induction;
3. ontology and execution validation with localized graph repair;
4. an evaluation protocol that directly tests whether the ontology is
   necessary.

## 2. Related Work

### 2.1 Process Element and Procedural Graph Extraction

PET annotates activities, actors, gateways, and flow relations
[@bellan2022pet]. Universal Prompting improves process-element extraction using
carefully specified LLM prompts [@neuberger2024universal]. PAGED introduces a
benchmark for procedural graph extraction and shows that LLMs identify textual
elements more reliably than non-sequential logical structure
[@du2024paged].

These works provide direct baselines for node and edge extraction. Their target
graphs do not require nodes to bind to a finite ontology Function Layer or
variables to remain consistent with ontology objects across the graph.

### 2.2 Process Model Generation

Process-model generation maps text to formal or semi-formal BPMN-style
representations [@kourani2024processmodeling]. BPMN captures tasks, events, and
gateways, but it does not by itself specify the enterprise object identities,
ontology properties, callable function contracts, or machine-checkable state
effects required for agent execution.

### 2.3 Ontology-Based Workflow Representation

Semantic workflow research represents processes, services, resources, and
execution state with ontologies. Linked Data workflow systems define workflow
semantics over REST resources [@kaefer2018linkedworkflows]. Scientific and
engineering process ontologies model sequence, state transition, intervention,
and provenance patterns [@norouzi2025processodp]. BioThings Explorer
semantically annotates API inputs and outputs and composes multi-hop calls
[@callaghan2023biothings].

This literature demonstrates that ontology semantics can support workflow
composition. Our task is different: the workflow itself must be induced from
unstructured procedural documents.

### 2.4 SOP Automation and Runtime Skills

Agent-S navigates SOPs using specialized LLM components and execution memory
[@kulkarni2025agents]. SOP-Bench evaluates long-horizon industrial procedures
with tool interfaces and reveals low success for current agents
[@nandi2025sopbench]. Formal Skill represents reusable agent capability using
structured metadata, executable logic, hooks, and local state
[@zhang2026formalskill].

Our work is upstream of runtime skill execution. It constructs a structured
skill from source documents and an ontology, making the result statically
checkable and independent of the extraction model.

### 2.5 Research Gap

Existing work separately provides procedural structure, semantic workflow
models, API composition, or SOP execution. It does not jointly require:

- function nodes grounded in an ontology Function Layer;
- variables grounded in object types and properties;
- conditions and effects represented as ontology state predicates;
- control edges justified by effect--precondition compatibility;
- ontology conformance and execution validation.

## 3. Method

### 3.1 Ontology Workflow Representation

Given Object Layer \(O\), Function Layer \(F\), and document \(D\), the model
constructs:

```text
OntologyWorkflowSkill {
  skill_id,
  goal_predicate,
  typed_inputs,
  typed_outputs,
  object_variables,
  nodes,
  control_edges,
  dataflow_edges,
  state_predicates,
  invariants,
  exception_paths,
  evidence,
  unresolved_regions
}
```

Node types are `OntologyFunctionCall`, `UserInteraction`, `Decision`, and
`End`. An `OntologyFunctionCall` must reference exactly one Function Layer ID.
Variables reference ontology classes or datatypes. A valid workflow has a
well-typed path from its input state to its goal predicate.

### 3.2 Structure-Aware Document Parsing

The parser preserves hierarchy, enumerations, tables, warning blocks,
cross-references, and page offsets. It identifies:

- goals and scope;
- prerequisites;
- operations;
- observations and expected results;
- conditions and branch markers;
- exceptions and warnings;
- recovery or compensation steps.

Document structure determines candidate scope but does not directly determine
workflow edges.

### 3.3 Joint Function and Object Retrieval

For each procedural unit, the system retrieves pairs:

\[
(f,o) \in F \times O
\]

using action semantics, target-object compatibility, input/output properties,
preconditions, effects, and neighboring context. Joint retrieval avoids
selecting a lexically similar function that operates on the wrong object type.

If no function has sufficient evidence, the unit is labeled
`unresolved_capability`. The model cannot invent a new atomic operation.

### 3.4 Typed Object and Data-Flow Grounding

The method tracks object variables across the complete document:

```text
v_order : Order
lookup_order.output.order -> v_order
v_order.id -> cancel_order.input.order_id
```

Coreference, relation paths, function signatures, and ontology cardinality
jointly constrain bindings. A required input must be provided by a workflow
input, a prior function output, a user interaction, or an ontology relation
traversal.

### 3.5 Ontology State-Transition Induction

Every function contributes preconditions and effects defined in \(F\).
Document conditions are normalized into predicates over ontology objects. The
workflow state after node \(n\) is:

\[
S_{n+1} = \mathrm{Apply}(S_n,\mathrm{effect}(f_n)).
\]

The constructor uses effect--precondition compatibility to:

- justify sequential dependencies;
- identify missing observation or update steps;
- reject impossible orderings;
- infer branch predicates;
- detect repeated or conflicting mutations.

### 3.6 Control, Exception, and Invariant Induction

The model predicts sequence, branch, join, loop, and exception edges.
Warnings and policies become invariants over ontology predicates. Exceptions
are linked to the smallest supported scope and can select an alternative
function, compensation path, user interaction, or escalation.

Normal and exceptional paths are generated jointly because exception semantics
often change the validity of a preceding transition.

### 3.7 Ontology and Graph Validation

The validator checks:

- function and object identifiers exist;
- variables are type-compatible;
- required parameters are bound;
- object identity is preserved;
- function preconditions hold on every executable path;
- effects provide downstream requirements;
- object cardinality and policy invariants are preserved;
- all branches can reach a valid terminal state;
- repeated side effects and deadlocks are absent.

Validation failures trigger localized repair of the implicated node, edge,
predicate, or binding.

### 3.8 Execution Validation

The workflow is executed against function mocks, benchmark tools, or sandbox
services. Tests cover nominal, branch, exception, and counterfactual object
states. A workflow is considered executable only if it can instantiate all
required inputs, call registered functions, follow observation-dependent
branches, and reach a valid ontology goal state without forbidden effects.

## 4. Experiment

### 4.1 Dataset Roles

Evaluation is layered because no public dataset annotates the complete target:

- PAGED for procedural nodes and graph edges [@du2024paged];
- PET and Universal Prompting datasets for activities, actors, gateways, and
  relations [@bellan2022pet; @neuberger2024universal];
- MyFixit and MSPT for maintenance actions, tools, parts, materials, and
  arguments;
- SOP-Bench for downstream execution [@nandi2025sopbench];
- a new Full Ontology Workflow benchmark for Function IDs, object variables,
  predicates, typed data flow, exceptions, invariants, and executable tests.

Scores are reported only for annotated fields.

### 4.2 Main Experimental Isolation

The primary experiment uses a gold Object Layer and gold Function Layer to
isolate workflow induction. Additional settings replace them with:

- automatically constructed Function Layer from Paper 1;
- noisy Object Layer;
- incomplete Function Layer.

Paper 2's main claim cannot depend on Paper 1 being correct.

### 4.3 Baselines

- direct document-to-workflow JSON;
- Universal Prompting plus heuristic graph construction;
- PAGED-style procedural graph extraction;
- document-to-BPMN generation;
- Function Library prompting without Object Layer;
- Object Layer prompting without Function Layer;
- full ontology prompting without retrieval;
- our method without state-transition reasoning;
- our method without execution validation;
- full method.

### 4.4 Metrics

**Document and graph**

- procedural-unit F1;
- node and labeled-edge F1;
- graph edit distance;
- gateway and exception F1.

**Ontology grounding**

- Function grounding top-1 accuracy;
- Object binding accuracy;
- ontology identifier validity;
- state-predicate F1;
- ontology violation rate.

**Typed data flow**

- variable definition/use F1;
- parameter binding F1;
- type-correct binding rate;
- object identity consistency;
- required-input coverage.

**State-transition quality**

- effect--precondition compatibility accuracy;
- invalid transition rate;
- goal-state reachability;
- invariant violation rate.

**Executability**

- executable workflow rate;
- test-case pass rate;
- hallucinated Function rate;
- forbidden side-effect rate;
- downstream task success.

### 4.5 Ontology Necessity Ablations

The following ablations are mandatory:

1. no Object Layer;
2. no Function Layer;
3. no ontology State Predicates;
4. no effect--precondition reasoning;
5. no typed data flow;
6. no execution validation.

The ontology contribution is supported only if these removals degrade ontology
correctness or executable utility, not merely output formatting.

### 4.6 Generalization

Splits are by source manual and organization. Evaluation includes unseen
documents, unseen combinations of known functions, and at least one unseen
domain with a replacement ontology but unchanged extraction code.

### 4.7 Statistical Analysis

Document-cluster bootstrap intervals are used for graph and grounding metrics.
Executable outcomes use paired tests over identical workflow tests. Mixed
models estimate the effects of workflow length, branch depth, variable
lifetime, Function Layer size, and ontology noise.

## 5. Analysis Plan

### 5.1 Main Claim

Paper 2 is successful only if ontology grounding improves:

- Function and Object correctness;
- typed data-flow consistency;
- valid state transitions;
- executable workflow or downstream success.

Higher node/edge F1 alone does not support the ontology claim.

### 5.2 Structural versus Ontological Correctness

Outputs are partitioned into:

- graph-correct and ontology-correct;
- graph-correct but ontology-invalid;
- graph-different but behaviorally equivalent;
- graph-invalid and non-executable.

This analysis identifies errors hidden by procedural graph metrics.

### 5.3 Upstream Error Propagation

The cascade experiment attributes errors to:

```text
Paper 1 Function omission
-> wrong Function grounding
-> broken dataflow/state transition
-> execution failure
```

Function absence, ontology mismatch, and document ambiguity are reported
separately.

### 5.4 Complexity and Failure Analysis

Results are stratified by branch depth, exception density, number of ontology
objects, variable lifetime, relation-path length, and Function candidate-set
size. This distinguishes document-length difficulty from ontology-composition
difficulty.

### 5.5 Limitations

Ontology validation cannot prove that the source document is correct.
Execution mocks may omit real service behavior. Equivalent workflows can have
different graph structures. These limitations require separate structural,
semantic, and executable metrics.

## 6. Conclusion

This paper makes the ontology operational inside workflow extraction. Function
nodes, object variables, conditions, effects, data flow, invariants, and outputs
are all represented in ontology terms. The method must therefore be evaluated
as ontology-grounded state-transition synthesis, not as generic procedural
graph extraction.
