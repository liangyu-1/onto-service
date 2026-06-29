# Autonomous Construction of Ontology Function Layers from Operational Artifacts

## Abstract

Automatic ontology construction typically focuses on classes, properties,
relations, axioms, or factual triples. Operational enterprise ontologies also
require a function layer that specifies what computations and state-changing
operations are available over ontology objects. Constructing this layer
manually does not scale because function semantics are distributed across API
documentation, OpenAPI schemas, SDK signatures, request-response examples,
error specifications, and execution traces. We formulate **autonomous ontology
function-layer construction**: given heterogeneous operational artifacts and an
automatically generated or existing object-layer draft, construct a library of
ontology-bound atomic functions without per-function expert review. We propose
an evidence-triangulated generate--validate--repair framework that jointly
aligns endpoints, object types, properties, parameter roles, state
preconditions, and effects; validates candidates through ontology constraints,
cross-source agreement, and sandbox or trace-replay execution; and
automatically publishes or abstains according to calibrated risk. Experiments
combine API extraction corpora, API knowledge-graph resources, executable
OpenAPI services, and controlled perturbations of the object layer. Evaluation
measures semantic correctness, executable validity, autonomous accepted
coverage, calibration, error propagation, and downstream workflow
composability. The central question is whether an operational function layer
can be constructed automatically with a measurable quality boundary rather
than relying on manual ontology engineering.

## 1. Introduction

Ontologies used in enterprise systems are increasingly expected to support
operations, not only describe data. An object layer may define `Order`,
`Customer`, their properties, and relationships, yet operational applications
also need to know which functions can retrieve an order, change its delivery
address, calculate a refund, or cancel it under a particular state. Industrial
ontology platforms expose similar object-oriented computations and operations
[@palantirFunctions2026], but constructing such a function layer remains a
substantial engineering task.

Research on automatic ontology and knowledge-graph construction has made rapid
progress. LLM-supported systems generate ontology drafts from requirements,
induce schemas from text, and construct large knowledge graphs with reduced
human involvement [@kommineni2024human2machine; @lippolis2025ontogenia;
@bai2025autoschemakg]. API-oriented research automatically extracts tool schemas
or API knowledge graphs from documentation [@ni2025toolfactory;
@sun2025apikg]. These lines of work remain disconnected. Ontology-construction
methods primarily produce descriptive schemas and triples, whereas API
extraction methods primarily produce callable interfaces. Neither directly
constructs a function layer whose operations are semantically bound to ontology
objects and whose quality can be controlled without expert approval.

This paper studies function extraction as a missing stage of automatic
operational ontology construction. The input is not a single API page and the
output is not merely a JSON function-calling schema. The input consists of
heterogeneous system artifacts: database and object metadata, API
documentation, OpenAPI descriptions, SDK signatures, request-response
examples, error specifications, and observed executions. The output is a
versioned Function Layer in which every atomic function is connected to object
types, properties, state predicates, and an executable endpoint.

The central constraint is **no per-function human intervention during
construction**. Experts do not accept, reject, or repair candidates in the
method loop. This requirement creates a scientific problem rather than only an
automation objective: if human adjudication is removed, the system needs an
automatic evidence and validation mechanism that can decide which candidates
are reliable enough to publish. Human annotation remains necessary for
benchmark construction and independent evaluation; otherwise the claim of
automatic correctness would be unverifiable.

Operational artifacts are noisy and mutually inconsistent. Documentation can
be stale, examples can omit required fields, endpoint names can obscure
business semantics, and automatically generated object ontologies can contain
incorrect classes or property alignments. A fluent LLM can produce a complete
function contract despite these defects, but completeness is not evidence of
correctness. The proposed method therefore treats every source as fallible and
requires semantic claims to survive cross-source and executable validation.

We propose an evidence-triangulated autonomous construction framework. It
discovers function candidates from all operational artifacts, jointly aligns
functions and object-layer elements, generates evidence-bearing contracts,
checks ontology and type consistency, synthesizes executable tests, and repairs
only fields implicated by validation failures. A calibrated publication policy
automatically accepts high-confidence functions and abstains on unresolved
semantics. No expert review is part of the construction pipeline.

We address five research questions:

- **RQ1:** Can multi-source evidence triangulation construct a more accurate
  Function Layer than single-document tool extraction?
- **RQ2:** How much does executable validation reduce semantically plausible
  but unusable functions?
- **RQ3:** Can calibrated automatic publication achieve useful coverage at a
  bounded error rate without human review?
- **RQ4:** How robust is function construction to errors in an automatically
  generated Object Layer?
- **RQ5:** Does the automatically constructed layer support downstream workflow
  composition comparably to a manually curated Function Layer?

The intended contributions are:

1. a task definition for autonomous Function Layer construction as part of
   operational ontology engineering;
2. a joint object-function alignment and evidence-triangulation method;
3. automatic validation, repair, abstention, and publication without
   per-candidate expert decisions;
4. an evaluation protocol covering accepted coverage, risk, execution, object
   ontology noise, and downstream composability.

## 2. Related Work

### 2.1 Automatic Ontology and Knowledge-Graph Construction

LLMs have been used to generate ontology drafts from competency questions and
user stories [@lippolis2025ontogenia], construct ontology-grounded knowledge
graphs [@feng2024ontologykg], and reduce expert effort in TBox and ABox
construction [@kommineni2024human2machine]. Text2KGBench evaluates fact
generation under ontology constraints [@mihindukulasooriya2023text2kg].
AutoSchemaKG goes further by jointly inducing schemas and triples at scale
without a predefined schema [@bai2025autoschemakg].

These systems demonstrate that schema construction can be substantially
automated, but they primarily model descriptive knowledge. The target of this
paper is the operational extension of an object ontology: functions with
inputs, outputs, object bindings, applicability conditions, effects, and
runtime bindings.

### 2.2 API Knowledge-Graph Construction

API knowledge graphs model APIs, parameters, relations, and dependencies for
recommendation and composition. Explore--Construct--Filter automatically
induces an API KG schema, extracts instances, and filters noisy triples
[@sun2025apikg]. In-N-Out models parameter-level dependencies between APIs and
shows that explicit API graphs improve multi-tool execution
[@lee2025innout]. BioThings Explorer uses semantically annotated API inputs and
outputs to compose federated biomedical queries [@callaghan2023biothings].

This literature directly motivates graph-level function semantics. However, API
entities are not necessarily integrated into an enterprise object ontology, and
automatic filtering does not by itself validate state preconditions, effects,
or executable object projections.

### 2.3 Tool-Schema Extraction and Function Calling

ToolFactory extracts AI-compatible tools from heterogeneous REST
documentation and provides an API Extraction Benchmark
[@ni2025toolfactory]. ToolLLM and Gorilla study large-scale tool use and API
selection [@qin2024toolllm; @patil2024gorilla]. CloudAPIBench demonstrates that
documentation can reduce low-frequency API hallucination while irrelevant
retrieval can also degrade performance [@jain2024cloudapi]. OpaqueToolsBench
shows that incomplete documentation requires behavioral learning from
interaction [@hallinan2026opaquetools].

Our task includes schema extraction but evaluates a stronger output contract:
the generated function must become a semantically valid member of an ontology
and remain executable.

### 2.4 Ontology-to-API Compilation

OBA automatically generates REST APIs from ontologies
[@garijo2020oba], and recent ontology-to-tools work compiles ontology
constraints into executable tool interfaces [@zhou2026ontologytools]. These
approaches operate in the reverse direction: the ontology is authoritative and
the interface is generated from it. We infer the Function Layer from existing
interfaces whose semantics may be incomplete or inconsistent with the
object-layer draft.

### 2.5 Research Gap

Prior work does not jointly study:

- automatic construction of the operational Function Layer;
- integration with an automatically generated or noisy Object Layer;
- validation using documentation, schemas, examples, and executions;
- autonomous accept/abstain decisions without expert adjudication;
- downstream workflow composability as a quality criterion.

## 3. Method

### 3.1 Problem Definition

Let \(A=\{A_1,\ldots,A_m\}\) denote operational artifacts and \(O_0\) an
Object Layer draft. \(O_0\) may be manually available, metadata-derived, or
automatically generated. The objective is to construct:

\[
F^* = \arg\max_F Q(F; A,O_0)
\]

subject to an autonomous publication risk bound:

\[
\widehat{R}(F_{\mathrm{published}}) \leq \tau.
\]

Each function is represented as:

```text
OntologyFunction {
  function_id,
  bound_object_types,
  operation_kind,
  inputs[{type, role, ontology_property}],
  outputs[{type, ontology_property}],
  preconditions,
  effects,
  endpoint_binding,
  error_contract,
  evidence_set,
  confidence,
  unresolved_fields
}
```

The construction algorithm outputs published functions, abstained candidates,
and proposed corrections to \(O_0\). It does not request expert decisions.

### 3.2 Multi-Source Function Discovery

Specialized parsers extract endpoint and operation candidates from OpenAPI,
HTML/PDF documentation, SDK signatures, database procedures, examples, logs,
and traces. The system constructs an evidence graph linking:

- operation identifiers and aliases;
- request and response fields;
- referenced data objects;
- documented errors and permissions;
- observed read and write sets;
- source locations and versions.

Candidates supported by only one weak textual cue are retained but assigned a
lower initial reliability.

### 3.3 Joint Object--Function Alignment

Sequentially freezing \(O_0\) before function extraction makes every
object-layer error permanent. We instead jointly score:

\[
(f,o,p,r)
\]

where \(f\) is a function candidate, \(o\) an object type, \(p\) an ontology
property, and \(r\) a semantic parameter role.

The score combines lexical and dense similarity, datatype compatibility,
request-response structure, graph neighborhood, observed data access, and
cross-function consistency. Alignment can propose:

- a binding to an existing ontology element;
- an alias or property correction;
- a missing object/property candidate;
- unresolved alignment.

Object-layer corrections require independent evidence from at least two source
views or one source plus execution.

### 3.4 Evidence-Bearing Contract Generation

A constrained generator produces function contracts from the local evidence
graph and ontology neighborhood. Every predicted field includes source
references and confidence. Preconditions and effects are expressed over
ontology predicates rather than free text.

The generator is prohibited from silently completing critical fields from
parametric knowledge. Target object, required inputs, endpoint binding, and
external effects are marked unresolved when evidence is insufficient.

### 3.5 Automatic Validation

Validation has three layers.

**Ontology validation**

- domain/range and datatype compatibility;
- property ownership and relation-path validity;
- state-predicate consistency;
- no contradictory effects for equivalent functions.

**Cross-artifact validation**

- OpenAPI, prose, examples, and traces agree on required inputs;
- response fields support declared outputs;
- error codes support negative preconditions;
- observed read/write sets support operation kind and effects.

**Executable validation**

- synthesize requests from examples and ontology instances;
- invoke a sandbox, mock service, or replay harness;
- check serialization, accepted requests, response projection, error behavior,
  and observed state transitions.

### 3.6 Local Repair and Self-Consistency

Validation failures are translated into field-level repair tasks. The system
regenerates only implicated alignments or predicates. Multiple independently
sampled candidates are compared by evidence support and executable outcomes,
not majority vote alone. Repair stops when the contract passes all mandatory
checks, reaches a cycle, or exhausts its budget.

### 3.7 Calibrated Autonomous Publication

A publication score combines:

- evidence diversity;
- ontology consistency;
- cross-artifact agreement;
- executable test coverage;
- residual unresolved critical fields;
- model disagreement.

Thresholds are calibrated on a development set. Candidates above the publish
threshold enter the Function Layer automatically; candidates below an abstain
threshold are rejected; intermediate candidates remain unresolved. The method
contains no human-review branch.

### 3.8 Incremental Update

Artifact changes invalidate only dependent functions. The evidence graph
identifies affected fields, replays relevant tests, and republishes a new
Function Layer version. This tests whether autonomous construction can support
ontology evolution rather than one-time extraction.

## 4. Experiment

### 4.1 Datasets and Gold Standard

The evaluation combines:

- ToolFactory API Extraction Benchmark for heterogeneous endpoint
  documentation [@ni2025toolfactory];
- API KG and parameter-dependency data from Explore--Construct--Filter and
  In-N-Out [@sun2025apikg; @lee2025innout];
- public OpenAPI repositories with executable mocks;
- low-frequency or incomplete documentation settings from CloudAPIBench and
  OpaqueToolsBench;
- a new Autonomous Function Layer benchmark with object bindings,
  parameter roles, preconditions, effects, errors, evidence, and test cases.

Experts construct the hidden gold set but never participate in system
inference. The distinction is essential: zero human intervention describes the
construction algorithm, not the evaluation process.

### 4.2 Object-Layer Conditions

Three input conditions are evaluated:

1. gold Object Layer;
2. automatically generated Object Layer;
3. controlled noisy Object Layer.

Noise injection includes renamed types, missing properties, wrong
domain/range, merged classes, split classes, and incorrect relation edges.

### 4.3 Baselines

- rule-based OpenAPI conversion;
- direct LLM document-to-tool extraction;
- ToolFactory-style extraction;
- API KG construction without ontology integration;
- sequential object-then-function alignment;
- full method without execution validation;
- full method without joint object correction;
- full method without abstention;
- full autonomous method.

Human-in-the-loop ontology engineering is included as an upper-reference cost
baseline, not as a competing autonomous method.

### 4.4 Metrics

**Discovery and contract quality**

- function discovery precision, recall, and F1;
- endpoint and parameter exact match;
- target-object and property-link accuracy;
- parameter-role F1;
- precondition, effect, and error-contract F1;
- full-function exact match.

**Autonomous construction**

- published coverage;
- error rate among automatically published functions;
- selective risk and risk-coverage area;
- expected calibration error;
- unsupported-claim rate;
- construction time and model/tool cost.

**Executability**

- valid invocation rate;
- response-to-object projection accuracy;
- state-transition consistency;
- generated-test fault detection.

**Robustness to Object Layer noise**

- absolute degradation;
- degradation slope as noise increases;
- object-error amplification ratio.

**Downstream utility**

- workflow function-grounding accuracy;
- executable workflow rate;
- downstream task success using the generated Function Layer.

### 4.5 Automatic Publication Protocol

Publication thresholds are frozen before testing. Results report a
risk-coverage curve rather than a single selected operating point. The primary
comparison fixes published coverage and compares error, then fixes error
tolerance and compares coverage.

### 4.6 Statistical Analysis

Endpoint-level comparisons use document-cluster bootstrap intervals. Paired
executability outcomes use McNemar tests. Noise experiments use mixed-effects
regression with method, noise type, and intensity as fixed effects and API
document as a random effect. Downstream workflow results are paired over
identical workflows.

## 5. Analysis Plan

### 5.1 Main Claim

The autonomous-construction claim is supported only if the method:

1. exceeds tool-schema baselines on ontology semantics and executability;
2. publishes non-trivial coverage at a predeclared error bound;
3. degrades more slowly under Object Layer noise;
4. supports downstream workflow composition.

High field F1 with low autonomous accepted coverage is not sufficient.

### 5.2 Error Propagation

Errors are traced across:

```text
artifact parsing
-> object/function alignment
-> contract generation
-> validation
-> publication
-> workflow composition
```

The analysis distinguishes method failure, missing evidence, defective
Object Layer, and non-executable test infrastructure.

### 5.3 Evidence Contribution

Ablations quantify the marginal value of OpenAPI, prose, examples, traces, and
execution. If execution dominates all other evidence, the paper becomes an API
testing method rather than ontology construction. If ontology constraints do
not improve downstream composition, the Function Layer claim must be reduced.

### 5.4 Autonomous versus Human Construction

The comparison reports quality, coverage, latency, and expert minutes. The
paper does not need to outperform experts in absolute semantic quality. It must
show a defensible autonomous operating region and identify cases where
abstention is necessary.

### 5.5 Limitations

Automatic publication does not imply guaranteed correctness. The empirical risk
bound depends on benchmark representativeness, test coverage, and calibration
stability. The method may fail when all artifacts share the same error or when
effects cannot be observed in a sandbox.

## 6. Conclusion

This paper treats Atomic Function extraction as a missing component of
automatic operational ontology construction. The contribution is not a
single-document schema extractor, but a no-review construction process that
jointly aligns objects and functions, validates semantics through independent
evidence and execution, and exposes a measurable coverage--risk boundary.
