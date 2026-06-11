# Research Plan: Industrial Ontology Enrichment and SOP-to-Action Extraction

Date scope: recent four years means 2022-05-14 to 2026-05-14.

This note covers two research ideas:

1. Extract knowledge from BoM, BoP, SysML and related industrial documents/models, then semantically enrich an ontology generated from metadata.
2. Extract Standard Operating Procedure (SOP) from Chinese or English unstructured data, then generate an action layer for an ontology system.

## Executive Judgment

The second idea is easier to evaluate with public data. SOP/process extraction has PET, WONDERBREAD, SOPBench, SOP-Bench, BREX/BPRF and several procedural-graph datasets or benchmarks.

The first idea is more industrially valuable but harder to benchmark. Public BoM/BoP/SysML-style data usually appears as standards, templates, model examples, or information models rather than paired "metadata ontology + document enrichment gold labels". This means the research needs a carefully constructed benchmark, probably by combining public industrial metadata models with manually annotated document evidence.

Recommended positioning:

- Short paper / first experiment: SOP-to-action, because evaluation is clearer.
- Stronger industrial research line: metadata-first ontology plus document semantic enrichment, but it needs your own benchmark construction.
- Best combined direction: use metadata to create the ontology backbone, use SOP/document extraction to add semantic enrichment and action candidates.

## Idea 1: Metadata Ontology + Document Semantic Enrichment

### Research Question

Can unstructured or semi-structured industrial sources enrich a metadata-derived ontology with definitions, aliases, rules, constraints, state semantics, process knowledge, evidence links, and action-relevant semantics without corrupting the ontology backbone?

### What Counts as "Metadata Ontology"

Possible metadata sources:

- database schemas
- API schemas
- OPC UA NodeSets
- AAS submodel templates
- SysML v2 textual models
- AutomationML files
- BoM and BoP tables
- MES/PLM/ERP object models

The metadata-derived ontology should produce:

- classes/object types
- properties
- relations
- enum values
- lifecycle states
- IDs, labels, provenance

### What Counts as "Semantic Enrichment"

Do not let document extraction freely create the formal ontology. Put extracted content into an enrichment layer:

| Enrichment Type | Example |
|---|---|
| definition | WorkOrder means a production task issued for a material and operation. |
| alias | WorkOrder = 工单 = 生产任务单 = WO |
| state semantics | REWORK_REQUIRED means quality failed and rework is needed. |
| business rule | temperature > 80 C requires stopEquipment. |
| constraint | welding current must be 110-130 A. |
| procedure | stop machine, create work order, inspect cooling system. |
| role policy | quality inspector approves inspection result. |
| evidence | source document, page, section, text span, confidence. |

### Public Data / Benchmark Candidates

| Dataset / Source | Use | Strength | Weakness |
|---|---|---|---|
| Text2KGBench, https://github.com/cenguix/Text2KGBench | Ontology-constrained KG extraction from text. | Has ontology + sentences + expected facts. Good for measuring ontology conformance. | General-domain, not industrial. |
| OntoEKG, https://github.com/LiberAI/OntoEKG | End-to-end ontology construction from unstructured enterprise text. | Provides code and small enterprise-domain evaluation setup. | Small; exact industrial BoM/BoP/SysML relevance is limited. |
| AAS Submodel Templates, https://github.com/admin-shell-io/submodel-templates/tree/main/published | Industrial metadata templates for assets, BoM-like hierarchy, maintenance, quality, process parameters. | Strong fit for industrial metadata ontology. | Mostly templates, not text-to-enrichment gold labels. |
| OPC UA NodeSets, https://github.com/OPCFoundation/UA-Nodeset | Industrial information models in XML/CSV. | Good structured metadata source; many domains. | Not unstructured documents. Need extra docs or generated enrichment labels. |
| SysML v2 Release examples, https://github.com/Systems-Modeling/SysML-v2-Release | SysML textual models, model libraries, examples. | Good for model-to-ontology conversion. | Limited public domain-specific industrial scenarios. |
| AutomationML RobotCell example, https://www.automationml.org/news/example-file-of-a-robotcell/ | Plant engineering XML with robot-cell model data. | Useful semi-structured engineering model. | Small example, not a labeled benchmark. |
| Manufacturing Service KG dataset from Li & Starly 2024 | Manufacturing services, certifications, location, websites. | Industrial KG from structured/unstructured web data. | More supplier/service discovery than BoM/BoP/SysML. |

Important limitation: I did not find a clean public benchmark that directly contains paired BoM/BoP/SysML metadata and gold semantic enrichment labels. A publishable experiment likely needs benchmark construction.

### Recent Papers

| Year | Paper | Relevance |
|---|---|---|
| 2022 | Natural Language Processing for Systems Engineering: Automatic Generation of SysML Diagrams | Text to SysML diagrams from specifications/manuals/reports; relevant to SysML extraction. |
| 2022 | Towards Ontology Reshaping for KG Generation with User-in-the-Loop: Applied to Bosch Welding | Industrial KG schema reshaping from ontology to data-oriented schema; strong metadata/ontology fit. |
| 2022 | Query-based Industrial Analytics over Knowledge Graphs with Ontology Reshaping | Industrial analytics over KGs; evaluates ontology reshaping with Bosch data. |
| 2023 | Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | Core benchmark for ontology-constrained extraction. |
| 2023 | Construction of Knowledge Graphs: State and Challenges | Survey; useful for positioning KG construction pipelines and quality assurance. |
| 2023 | Enhancing Knowledge Graph Construction Using Large Language Models | LLM-based KG and ontology creation from raw text. |
| 2023 | Semantic Modelling of Organizational Knowledge as a Basis for Enterprise Data Governance 4.0 | Metadata-driven enterprise governance with semantic web principles. |
| 2024 | Generation of Asset Administration Shell with Large Language Model Agents | LLM agents for AAS generation, relevant to industrial digital twin semantic models. |
| 2024 | Building A Knowledge Graph to Enrich ChatGPT Responses in Manufacturing Service Discovery | Manufacturing service KG from structured/unstructured sources; public dataset of 13k+ manufacturers reported. |
| 2024 | Automated Extraction and Creation of FBS Design Reasoning Knowledge Graphs from Structured Data in Product Catalogues | Product catalog/spec data to FBS ontology KG; close to BoM/design metadata enrichment. |
| 2025 | OntoRAG: Enhancing QA through Automated Ontology Derivation from Unstructured Knowledge Bases | Ontology derivation from electrical relay documents; directly relevant to document-to-ontology pipelines. |
| 2026 | LLM-Driven Ontology Construction for Enterprise Knowledge Graphs | Extracts classes/properties and hierarchy from enterprise text; reports fuzzy-match ontology F1. |
| 2026 | TRACE-KG for Context-Enriched Knowledge Graphs from Complex Documents | Schema induction plus traceable KG from complex documents; relevant to evidence-backed enrichment. |
| 2026 | From Prompt to Graph: Comparing LLM-Based IE Strategies in Domain-Specific Ontology Development | Manufacturing/casting ontology construction with LLM extraction strategies. |
| 2026 | Ontology-Compliant Knowledge Graphs | Ontology compliance, matching, alignment and metrics; useful for evaluation. |

### Experiment Design

#### Task Definition

Input:

- metadata ontology backbone, e.g. from AAS/OPC UA/SysML/DDL
- document corpus, e.g. manuals, submodel descriptions, maintenance instructions, quality templates, SOPs

Output:

- semantic enrichment annotations linked to ontology elements
- each annotation must include evidence span and review status

Suggested output schema:

```json
{
  "target_kind": "ObjectType|Property|Relation|State|Action",
  "target_id": "Equipment.temperature",
  "enrichment_type": "definition|alias|rule|constraint|procedure|state_semantics|role_policy",
  "content": {},
  "evidence": {
    "document_id": "",
    "page": null,
    "section": "",
    "text_span": ""
  },
  "confidence": 0.0
}
```

#### Baselines

1. Metadata-only ontology: no document enrichment.
2. Text-only LLM ontology extraction: ignores metadata backbone.
3. Metadata + vector RAG: retrieve chunks by ontology labels and ask LLM to summarize.
4. Ontology-constrained extraction: extract only enrichment types grounded to existing ontology elements.
5. Ontology-constrained extraction + verifier: add SHACL/JSON-schema checks, evidence checks, and contradiction detection.
6. Human-in-the-loop active learning: sample uncertain mappings for human correction.

#### Metrics

| Metric | Meaning |
|---|---|
| Entity linking precision/recall/F1 | Did extracted text semantics attach to the correct ontology element? |
| Enrichment type accuracy | Was a rule, alias, definition, constraint, etc. classified correctly? |
| Evidence correctness | Does the text span actually support the enrichment? |
| Schema conformance | Does output respect ontology target types and allowed enrichment schema? |
| SHACL violation count | Does the enriched graph violate formal constraints? |
| Competency question improvement | Does enrichment improve answers to domain questions vs metadata-only ontology? |
| Retrieval improvement | Does alias/definition enrichment improve document retrieval hit rate? |
| Human approval rate | Percentage of extracted enrichments accepted by reviewers. |
| Hallucination rate | Extracted claims not supported by source evidence. |

#### Benchmark Construction Plan

1. Select 3 public metadata sources:
   - AAS submodel templates: maintenance, process parameters, quality control, BoM hierarchy.
   - OPC UA NodeSets: machine tool, robotics, devices, sensors.
   - SysML v2 examples: requirements, blocks, ports, actions, states.
2. Build metadata-derived ontology automatically.
3. Collect paired public documents:
   - template specifications
   - model documentation
   - maintenance instructions
   - public manuals or standard descriptions
4. Annotate 200-500 enrichment items:
   - 50 definitions
   - 50 aliases
   - 50 rules/constraints
   - 50 state/process semantics
   - 50 procedures/actions if available
5. Evaluate the baselines above.

### Expected Contribution

The publishable novelty is not "LLM extracts ontology from documents". That is already crowded. A stronger claim is:

Metadata-derived ontology is structurally reliable but semantically thin. We propose an evidence-grounded semantic enrichment layer that preserves the metadata ontology backbone while adding document-derived semantics, with formal validation and human-review hooks.

## Idea 2: SOP Extraction to Ontology Action Layer

### Research Question

Can an SOP extracted from Chinese or English unstructured documents be transformed into ontology actions with objects, roles, parameters, preconditions, effects, state transitions, evidence, and executable validation?

### Target Representation

Do not directly generate platform-specific actions. Generate an intermediate action IR:

```json
{
  "action_name": "submitQualityFailure",
  "target_object": "WorkOrder",
  "actor_role": "QualityInspector",
  "parameters": [
    {"name": "failure_reason", "type": "string", "required": true}
  ],
  "preconditions": [
    "WorkOrder.status == 'IN_INSPECTION'"
  ],
  "effects": [
    "create NonconformanceRecord",
    "set WorkOrder.status = 'REWORK_REQUIRED'"
  ],
  "exceptions": [],
  "evidence": {
    "document_id": "",
    "text_span": ""
  }
}
```

### Public Data / Benchmark Candidates

| Dataset / Source | Use | Strength | Weakness |
|---|---|---|---|
| PET, https://huggingface.co/datasets/patriziobellan/PET | English process extraction from text. | Annotated activities, gateways, actors and flow information. Local copy exists in `papers/datasets/data`. | Small: 45 examples. |
| WONDERBREAD, https://github.com/HazyResearch/wonderbread | SOP generation from workflow demonstrations; action traces + written SOPs. | 2,928 demonstrations, 598 workflows, includes SOPs, recordings, traces, keyframes. | Web workflow domain, not industrial shop floor. |
| SOPBench, https://github.com/Leezekun/SOPBench | Agent following SOP and constraints. | 903 test cases, 167 tools/functions, executable verifiers and trajectories. | Focus is SOP following, not raw document extraction. |
| SOP-Bench, https://github.com/amazon-science/SOP-Bench | Complex industrial SOP execution benchmark. | 2,000+ tasks across 12 domains, natural language SOP, tools, test cases. | Synthetic/human-AI authored; license and exact version should be checked. |
| BREX, https://huggingface.co/datasets/XiaopiYu/BREX | Chinese business rule flow extraction. | 409 documents, 2,855 rules, sequential/conditional/parallel dependencies. | Rule-flow benchmark, not full SOP-to-action. |
| BPRF / Business as Rulesual paper | Chinese business process rules. | 50 docs and 326 `<Condition, Action>` rules in earlier paper version. | Dataset naming/version appears to have evolved toward BREX. |
| PAGED | Procedural graph extraction from documents. | Directly relevant benchmark for procedure-to-graph. | I did not verify a primary open dataset repository. |
| PcMSP | Scientific/materials procedure extraction. | 305 synthesis procedures with entities/relations; useful for procedural graphs. | Domain-specific scientific text. |
| FlaMBé, https://zenodo.org/records/10050681 | Biomedical workflow extraction. | 55 full papers, workflow tuples, tool sequence/context annotations. | Biomedical; not business/industrial SOP. |
| FlowExtract, https://github.com/guille-gil/FlowExtract | Maintenance flowchart extraction. | Relevant to industrial troubleshooting diagrams. | Public repo appears code-first; source industrial data may be redacted/proprietary. |

### Recent Papers

| Year | Paper | Relevance |
|---|---|---|
| 2023 | Large Language Models can accomplish Business Process Management Tasks | LLMs for BPM tasks including process model mining from text. |
| 2023 | Procedural Text Mining with Large Language Models | Extract procedures from unstructured PDF text using ontology/few-shot prompts. |
| 2024 | WONDERBREAD | BPM benchmark with SOP generation, QA, validation and improvement tasks. |
| 2024 | PAGED: A Benchmark for Procedural Graphs Extraction from Documents | Procedure graph extraction benchmark; evaluates LLMs and baselines. |
| 2024 | Human Evaluation of Procedural Knowledge Graph Extraction from Text with LLMs | Extract steps/actions/objects/equipment/time into procedural KG. |
| 2025 | SOP-Agent | Represents SOP as decision graph to guide domain-specific agents. |
| 2025 | Agent-S | Agentic workflow to automate SOPs in customer care with API/user environments. |
| 2025 | SOPBench | Evaluates language agents following SOPs/constraints with executable environments. |
| 2025 | Business as Rulesual / BPRF | Chinese business rule extraction and dependency modeling. |
| 2025 | SOP-Bench: Complex Industrial SOPs | Industrial-style SOP execution benchmark for LLM agents. |
| 2026 | JourneyBench | Customer-support benchmark for policy/SOP adherence using graph representations. |
| 2026 | SOPRAG | Industrial SOP retrieval with entity/causal/flow graph experts. |
| 2026 | Procedural Knowledge Extraction from Industrial Troubleshooting Guides Using VLMs | VLM extraction from industrial troubleshooting diagrams. |
| 2026 | FlowExtract | Hybrid CV/OCR/arrow-tracing extraction from maintenance flowcharts. |
| 2026 | SAGE | Graph-guided service-agent evaluation from unstructured SOPs to dynamic dialogue graphs. |
| 2026 | SupChain-Bench | Supply-chain SOP/tool orchestration benchmark. |

### Experiment Design

#### Task Decomposition

1. SOP detection:
   - identify whether a document chunk contains a procedure/SOP.
2. Step extraction:
   - extract ordered steps and nested steps.
3. Semantic role extraction:
   - actor, object, input, output, equipment, material, parameter, quality check.
4. Control-flow extraction:
   - sequential, conditional, parallel, loop, exception.
5. State/action extraction:
   - map step to target object, preconditions, effects.
6. Ontology action generation:
   - generate action IR with parameters, permissions, validation and effects.
7. Executable verification:
   - test generated actions in a simulator or rule engine.

#### Baselines

1. Direct LLM extraction to JSON.
2. Two-stage extraction: SOP graph first, actions second.
3. Ontology-constrained extraction: use object/action schema from metadata ontology.
4. Self-refine graph extraction: extract, verify, repair.
5. Code/pseudocode grounding: convert SOP rules into executable pseudo-code before action IR.
6. RAG baseline: retrieve document chunks and ask an agent to follow SOP without structured action generation.

#### Metrics

| Stage | Metric |
|---|---|
| SOP detection | document/chunk classification F1 |
| Step extraction | step precision/recall/F1, ordering accuracy |
| Role/object extraction | entity F1, slot filling F1 |
| Control flow | dependency F1, graph edit distance |
| Action IR | exact/fuzzy match on action name, target object, parameters, preconditions, effects |
| Evidence | percentage of actions with correct source span |
| Execution | task pass rate, tool-call accuracy, invalid-action rate |
| Safety/compliance | forbidden action rate, missed precondition rate |
| Multilingual | Chinese-English cross-lingual performance drop |

#### Concrete Experimental Tracks

Track A: English text-to-process

- Dataset: PET.
- Output: process graph and action candidates.
- Main metric: entity/relation/control-flow F1.

Track B: Chinese business rule flow

- Dataset: BREX or BPRF.
- Output: condition-action rules and dependencies.
- Main metric: rule tuple F1 and dependency F1.

Track C: SOP-to-agent/action execution

- Dataset: SOPBench or SOP-Bench.
- Output: ontology action IR plus executable tool plan.
- Main metric: verifier pass rate, tool-call precision, precondition/effect correctness.

Track D: Multimodal workflow-to-SOP/action

- Dataset: WONDERBREAD.
- Output: SOP and action graph from recording/action trace.
- Main metric: SOP generation quality, step recall, demo validation F1, action trace alignment.

Track E: Industrial diagram-to-SOP/action

- Dataset: FlowExtract examples or synthetic/annotated flowchart set.
- Output: graph nodes, edges, decisions, action IR.
- Main metric: node/edge F1 and graph topology accuracy.

### Suggested Model Architecture

```text
Document
  -> parser/OCR/layout extractor
  -> chunker with section/table/figure awareness
  -> SOP/procedure detector
  -> ontology-aware extractor
  -> procedural graph builder
  -> verifier/repair loop
  -> action IR generator
  -> rule engine/simulator
  -> human review queue
```

### Key Design Choice

Do not train the system to directly output "Palantir action" or "iDME operation". Use a platform-independent action IR first. Platform-specific action generation should be a final compiler step.

## Combined Research Method

The two ideas can be unified:

```text
metadata -> ontology backbone
documents/SOPs -> semantic enrichment + procedure graph
procedure graph -> ontology action IR
action IR -> executable operation / workflow / lifecycle transition
```

### Combined Hypotheses

H1: Metadata-derived ontology improves SOP extraction by constraining object types, states, parameters and roles.

H2: Document-derived semantic enrichment improves ontology usefulness in retrieval, QA and action synthesis compared with metadata-only ontology.

H3: SOP-to-action generation with explicit intermediate graphs and verification reduces hallucinated or unsafe actions compared with direct LLM generation.

H4: Chinese rule-flow data and English process data can share one language-independent action IR, but extraction prompts and entity linking require language-specific adaptation.

## Recommended First Experiment

Start with a narrow, publishable prototype:

Title idea:

Evidence-Grounded SOP-to-Action Extraction with Metadata-Constrained Ontology Enrichment.

Minimum viable experiment:

1. Build a small ontology from metadata:
   - WorkOrder, Equipment, Operation, Material, InspectionResult, Role, State.
2. Use PET and BREX:
   - PET for English process flow.
   - BREX for Chinese condition-action dependencies.
3. Generate a unified intermediate representation:
   - steps, roles, objects, conditions, actions, dependencies, evidence.
4. Add ontology constraints:
   - target object must exist in ontology.
   - action must have actor, precondition, effect, evidence.
5. Compare:
   - direct LLM
   - schema-constrained LLM
   - ontology-constrained LLM
   - ontology-constrained + verifier/repair
6. Evaluate:
   - extraction F1
   - dependency F1
   - action IR correctness
   - evidence correctness
   - verifier pass rate

This is more controllable than trying to solve full BoM/BoP/SysML enrichment immediately.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Public industrial BoM/BoP data scarcity | Hard to benchmark idea 1 directly. | Use AAS/OPC UA/SysML examples and build manual gold labels. |
| LLM creates plausible but unsupported semantics | Unsafe ontology/action pollution. | Require evidence span and review status for every output. |
| Text-only ontology extraction duplicates metadata concepts | Ontology bloat. | Treat document extraction as enrichment candidates, not formal class creation. |
| SOP datasets are not industrial shop-floor SOPs | Domain gap. | Use SOP-Bench/FlowExtract and create small industrial-style internal benchmark if possible. |
| Chinese/English schema mismatch | Poor multilingual transfer. | Use language-neutral IR and separate lexical/entity-linking layers. |
| Action generation is hard to evaluate without simulator | Weak claims. | Use SOPBench/SOP-Bench executable verifiers and simple custom simulators. |

## Final Recommendation

If the goal is a fast research result, do idea 2 first. It has public datasets and executable evaluation.

If the goal is a stronger industrial ontology thesis, do idea 1 as the long-term line, but frame it as evidence-grounded semantic enrichment of a metadata ontology rather than full ontology extraction from documents.

The strongest research story is the combination:

1. metadata builds the trusted ontology backbone;
2. documents add semantic enrichment with evidence;
3. SOP extraction creates procedural graphs;
4. procedural graphs compile into action IR;
5. action IR is verified against ontology constraints and executable test cases.

