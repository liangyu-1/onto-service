# Paper 1 / Paper 2 Related-Work Audit

Date: 2026-06-23

## Bottom Line

Paper 1 and Paper 2 both have substantial prior work. The defensible research
position is not "no one has studied this", but:

- prior work covers collaborative ontology engineering, human-in-the-loop
  knowledge graph expansion, multi-agent extraction, process-model extraction,
  and procedural graph construction;
- no inspected work unifies these components around an executable
  ontology **action layer** with a canonical Action IR, versioned semantic
  patches, governance provenance, and downstream execution feedback;
- this remaining gap is narrower than the current presentation suggests and
  must be tested directly against the strongest adjacent systems.

## Paper 1: Collaborative Action Ontogenesis

### Direct Predecessors

| Work | What it already contributes | What must not be claimed as new | Remaining distinction |
| --- | --- | --- | --- |
| DILIGENT / NeOn ontology engineering methodologies | Distributed contribution, change requests, control-board review, iterative and incremental ontology evolution | Collaborative and iterative ontology engineering | Action-specific patch semantics and executable validation |
| [HyWay: LLM-supported collaborative ontology design](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2025.1676477/full) | Structured expert elicitation, LLM semantic mapping to EMMO/QUDT, iterative expert validation, OWL generation, platform integration | LLM + expert validation for ontology construction | Multi-agent independent evidence, action-layer semantics, execution-trace feedback, explicit conflict benchmark |
| [IDEA2](https://arxiv.org/abs/2604.01344) | LLM-generated competency questions, expert collaborative review, iterative reformulation, consensus and full provenance | Expert-in-the-loop iterative ontology requirements and provenance | Full action-schema patches rather than only competency questions; executable validation |
| [CooperKGC](https://arxiv.org/abs/2312.03022) | Multiple agents for entity, relation and event extraction; iterative selection, correction and aggregation | Multi-agent collaboration for knowledge graph construction | Persistent ontology evolution, human governance, Action IR constraints and runtime feedback |
| [Clinical multi-LLM KG construction](https://arxiv.org/abs/2601.01844) | Schema-constrained RAG, multi-LLM consensus validation, uncertainty, ontology-aligned RDF/OWL and iterative refinement | Multi-LLM consensus for ontology-aligned KG construction | Non-clinical action ontology; patch lifecycle; human ownership; execution-based verification |
| [AutoPKG](https://arxiv.org/abs/2604.16950) | Multi-agent dynamic type/key induction, centralized decision agent, canonical graph consolidation, dynamic-KG metrics and production A/B tests | Multi-agent dynamic ontology/KG construction and central consolidation | Action semantics with preconditions/effects; human dispute workflow; multiple evidence sources; downstream agent admissibility |
| [Agent-OM](https://arxiv.org/abs/2312.00326) | LLM agents, retrieval/matching tools and shared reasoning for ontology alignment on OAEI tracks | Agent-based ontology matching | Construction/evolution of action definitions rather than pairwise ontology alignment |
| [Expanding KGs with Humans in the Loop](https://arxiv.org/abs/2212.05189) | Human-friendly candidate placement, controlled human study, production deployment and measured labor reduction | Human verification as a scalable KG expansion mechanism | Rich action patches and multi-agent conflict, not only parent prediction |
| Mortensen et al. 2016, crowd-assisted ontology verification | Shows crowds can handle easy verification tasks but should assist rather than replace experts | Crowd micro-task verification | Difficulty-aware routing of action-patch verification to agents, crowd and domain owners |

### Consequence for Novelty

Paper 1 cannot defensibly claim:

- the first collaborative ontology engineering method;
- the first LLM-assisted human-in-the-loop ontology workflow;
- the first multi-agent KG construction system;
- the first dynamic ontology/KG evolution framework;
- the first provenance-aware collaborative workflow.

The paper can target the following narrower combined contribution:

1. **Action-ontology patch semantics**: proposals modify actor, target, role
   bindings, preconditions, effects, constraints and control flow, rather than
   only classes, properties or triples.
2. **Semantic/governance separation**: Action IR stores domain semantics;
   Proposal Envelope stores contributors, votes, confidence, disputes and audit.
3. **Multi-source evidence loop**: metadata, procedural documents, API schemas
   and execution traces independently support or challenge a patch.
4. **Executable validation**: candidate patches are tested through type checks,
   counterfactual states and downstream agent/tool traces.
5. **Closed-loop evolution**: runtime failures can reopen an accepted action
   definition, trigger revalidation and produce a new version.

AutoPKG is the strongest threat. Without executable-action semantics,
human-governed disputes, and runtime-triggered revalidation, Paper 1 risks being
an application variant of AutoPKG plus HyWay.

## Paper 2: Ontology-Grounded Action Extraction

### Direct Predecessors

| Work | What it already contributes | What must not be claimed as new | Remaining distinction |
| --- | --- | --- | --- |
| [Text2Event](https://arxiv.org/abs/2106.09232) | End-to-end sequence-to-structure event extraction with schema-constrained decoding | Structured event generation and constrained decoding | Procedural state/control-flow/evidence plus existing-ontology grounding |
| [Creative Procedural-Knowledge Extraction](https://arxiv.org/abs/1904.08587) | Ontology with goal, workflow, action, command and usage; 47,491 annotated actions | Ontology-backed procedural action extraction | Preconditions/effects/constraints, object-role grounding and runtime projection |
| [PET](https://arxiv.org/abs/2203.04860) | Expert annotations for activities, actors, gateways and flow relations | Process-element and flow extraction benchmark | Full Action IR fields and ontology identifiers |
| [PAGED](https://aclanthology.org/2024.acl-long.583/) | Large procedural-graph benchmark; sequential/non-sequential logic; LLM and self-refine baselines | Procedural graph extraction from documents | Typed action semantics, evidence provenance, existing-ontology grounding and ActionBank projection |
| [Universal Prompting Strategy](https://arxiv.org/abs/2407.18540) | LLM extraction of activities, actors and relations; up to 8 F1 improvement over prior methods across three datasets | LLM-based process-information extraction | Beyond BPM elements to executable action schemas |
| [Decomposed Hybrid BPM with LLMs](https://link.springer.com/chapter/10.1007/978-3-031-81375-7_14) | LLM clarification/extraction plus deterministic process-model construction | Hybrid LLM + symbolic model generation | Ontology grounding, action-state semantics and evidence validation |
| [Exploring LLMs for Procedural Extraction](https://sebd2024.unica.it/papers/paper71.pdf) | PDF procedure/step/substep extraction and ontology application through few-shot ICL | Ontology-guided procedural extraction from manuals | Broader Action IR, explicit validation, datasets and downstream utility |
| [Multi-Agent Procedural Graph Extraction](https://arxiv.org/abs/2601.19170) | Builder, structural simulation and semantic agents iteratively refine procedural graphs | Multi-agent structural/logical refinement | Ontology-grounded action records, evidence, state transitions, constraints and executable projection |
| [NL2ProcessOps](https://link.springer.com/chapter/10.1007/978-3-031-70418-5_8) | Text-to-control-flow, tool retrieval and executable code generation with human refinement | Connecting process text to executable artifacts | Canonical ontology action layer and verifier-oriented semantics |
| [Ontology for Maintenance Procedure Documentation](https://journals.sagepub.com/doi/10.3233/AO-230279) | Industrial maintenance procedure ontology aligned to ISO 15926, validated on real procedures and competency questions | Ontological representation of industrial maintenance procedures | Automatic population/extraction of executable actions and runtime grounding |

### Consequence for Novelty

Paper 2 cannot defensibly claim:

- the first action extraction from procedural documents;
- the first text-to-process or procedural-graph extraction;
- the first LLM-based process extraction;
- the first ontology-guided extraction from manuals;
- the first hybrid LLM and symbolic validation pipeline;
- the first link from process text to executable artifacts.

The paper must make the output contract its central distinction:

1. Every extracted record is grounded to an **existing operational ontology**,
   not merely assigned a generated event or BPMN label.
2. The output contains target-object types, semantic parameter roles,
   preconditions, effects, policy constraints and evidence.
3. The method distinguishes evidence-supported fields from unresolved fields.
4. Validation checks type compatibility, referential integrity, control-flow
   consistency and deterministic ActionBank projection.
5. Evaluation includes both extraction metrics and downstream action
   admissibility/planning utility.

The 2026 multi-agent procedural-graph paper is the strongest method threat.
PAGED is the strongest benchmark threat. OMPD is the strongest industrial
ontology representation prior.

## Relationship Between Paper 1 and Paper 2

Paper 2 remains necessary only if it is treated as a strong, independently
evaluated **proposal generator** for Paper 1:

- Paper 2 asks whether a document can be converted into a faithful,
  ontology-grounded Action IR Patch.
- Paper 1 asks whether heterogeneous proposals from Paper 2, metadata agents,
  API agents, execution traces and humans can be validated, reconciled,
  versioned and evolved efficiently.

If Paper 1 itself introduces the document extraction algorithm and evaluates it
on the same datasets, Paper 2 becomes redundant. The separation is defensible
only when Paper 1 treats proposal generators as replaceable and evaluates the
governance loop independently of extraction accuracy.

## Papers to Read First

1. AutoPKG, because it most directly threatens Paper 1's dynamic multi-agent
   construction claim.
2. HyWay, because it provides the closest mature ontology-engineering workflow.
3. CooperKGC, because it establishes multi-agent extraction and correction.
4. IDEA2, because it already combines collaborative feedback, consensus and
   provenance.
5. PAGED, because it defines the strongest procedural-graph benchmark.
6. Multi-Agent Procedural Graph Extraction, because it overlaps with Paper 2's
   proposed refinement architecture.
7. Universal Prompting Strategy, because it is a strong LLM process-extraction
   baseline.
8. OMPD, because it defines an industrial maintenance procedure ontology that
   Action IR must compare against.
