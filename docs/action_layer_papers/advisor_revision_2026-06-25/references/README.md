# Downloaded Reading Set

The PDFs in this directory were selected for the revised three-paper design.
They are not all equally authoritative. Recent 2026 arXiv papers are useful for
novelty boundaries and experiment ideas but should not be treated as established
consensus.

## Priority 1: Direct Competitors

### Paper 1

- `paper1_toolfactory_2025.pdf`
  - Direct competitor for extracting AI-compatible tools from heterogeneous API
    documentation.
  - The revised Paper 1 must demonstrate ontology-object binding,
    precondition/effect semantics, abstention, and executable validation beyond
    ToolFactory.
- `paper1_ontology_to_tools_2026.pdf`
  - Studies compilation in the reverse direction, from ontology semantics to
    executable tools.
  - Useful for defining what an ontology-bound function contract must support.
- `paper1_autoschemakg_2025.pdf`
  - Direct evidence that schema induction and KG construction can be operated
    without manual intervention.
  - Paper 1 must extend autonomous construction from descriptive schemas to an
    executable ontology Function Layer.
- `paper1_automated_api_kg_2025.pdf`
  - Fully automated API knowledge-graph schema induction and filtering.
  - A close baseline for automated API semantics, but it does not construct
    object-bound preconditions, effects, and executable publication decisions.

### Paper 2

- `paper2_paged_2024.pdf`
  - Main procedural-graph extraction benchmark.
  - Read its graph representation, split protocol, metrics, and self-refinement
    baseline.
- `paper2_universal_prompting_2024.pdf`
  - Strong process-element extraction baseline.
  - Relevant to activity, actor, and relation extraction but not sufficient for
    executable function grounding.
- `paper2_agent_s_2025.pdf`
  - Closest SOP-to-agent workflow system.
  - The revised Paper 2 must distinguish offline skill induction from direct
    natural-language SOP execution.
- `paper2_formal_skill_2026.pdf`
  - Defines structured runtime skills with executable logic and state machines.
  - Useful as a target-representation competitor.

### Paper 3

- `paper3_agentdojo_2024.pdf`
  - Primary dynamic benchmark for utility under indirect prompt injection.
- `paper3_injecagent_2024.pdf`
  - Tool-integrated indirect prompt-injection benchmark.
- `paper3_agent_security_bench_2024.pdf`
  - Broad attack taxonomy and Net Resilient Performance metric.
- `paper3_adaptive_attacks_2025.pdf`
  - Demonstrates that fixed-attack evaluation overstates defense robustness.
- `paper3_toolhijacker_2025.pdf`
  - Direct attack against tool retrieval and selection through malicious tool
    descriptions.
- `paper3_agentspec_2025.pdf`
  - Runtime enforcement with structured rules.
- `paper3_agent_c_2025.pdf`
  - Formal temporal constraint enforcement and compliant alternative
    generation.
- `paper3_verifier_tax_2026.pdf`
  - Directly motivates the success-conformance trade-off after blocking.
- `paper3_reliability_bench_2026.pdf`
  - Provides production-like perturbations and reliability surfaces.
- `paper3_robust_agent_compensation_2026.pdf`
  - Direct competitor for compensation and recovery after side effects.

## Priority 2: Benchmark and Failure Analysis

- `paper2_sop_bench_2025.pdf`
  - Industrial SOP execution benchmark and tool-registry stress test.
- `paper3_tau_bench_2024.pdf`
  - Stateful customer-service execution benchmark already supported by the
    repository.
- `paper3_agentproof_2026.pdf`
  - Static workflow-graph verification; useful for separating static defects
    from runtime failures.
- `paper3_solver_policy_2026.pdf`
  - Solver-aided policy compliance; relevant to formal/runtime baselines.

## Priority 3: Supporting Evidence

- `paper1_cloud_api_bench_2024.pdf`
  - API hallucination and selective documentation retrieval.
- `paper1_opaque_tools_bench_2026.pdf`
  - Incomplete tool documentation and interaction-based refinement.
- `paper3_progent_2025.pdf`
  - Programmable privilege control and security-policy enforcement.

## Recommended Reading Order

1. ToolFactory
2. AutoSchemaKG
3. Explore-Construct-Filter API KG
4. PAGED
5. Agent-S
6. SOP-Bench
7. AgentDojo
8. InjecAgent
9. Agent Security Bench
10. Adaptive Attacks
11. ToolHijacker
12. AgentSpec
13. Agent-C
14. Verifier Tax
15. ReliabilityBench
