# New Required Readings for Action-Layer Papers

Date: 2026-06-09

This folder contains papers newly searched and downloaded for the three action-layer papers. The selection is intentionally narrow: papers are included only if they affect the writing order, novelty boundary, methodology, or experimental design.

## Recommended Writing Order

1. **Paper 3: action-layer verification and repair for LLM agents**
   This should be written first because the benchmark, baselines, and negative findings are already concrete. The new literature also shows that runtime enforcement is now an active research area, so the paper must be positioned carefully.

2. **Paper 2: SOP/action extraction from unstructured documents**
   This should be written second because it can provide the upstream source of ActionBank/action schemas. Its main risk is being absorbed by BPM/process extraction literature, so the paper must emphasize ontology-grounded action intermediate representation rather than generic BPMN generation.

3. **Paper 1: action indexing**
   This should be written last. Current tool retrieval and API graph papers already cover much of the obvious retrieval space. A strong version of this paper must show why action indexing differs from ordinary tool retrieval: object binding, precondition/effect matching, policy constraints, state-aware admissibility, and graph-structured action composition.

## Must-Read First

### Paper 3: Verification, Policy, and Runtime Control

1. `paper3_agent_c_temporal_constraints_2025.pdf`
   - Title: *Enforcing Temporal Constraints for LLM Agents*
   - URL: https://arxiv.org/abs/2512.23738
   - Why read: closest competitor to action-layer runtime verification. It uses formal temporal constraints and SMT-style enforcement. Your paper must distinguish itself from this work.

2. `paper3_solver_aided_policy_compliance_2026.pdf`
   - Title: *Solver-Aided Verification of Policy Compliance in Tool-Augmented LLM Agents*
   - URL: https://arxiv.org/abs/2603.20449
   - Why read: directly overlaps with policy compliance on tool calls and tau-bench-style evaluation. This is a serious related work item, not optional.

3. `paper3_verifier_tax_2026.pdf`
   - Title: *The Verifier Tax: Horizon Dependent Safety Success Tradeoffs in Tool Using LLM Agents*
   - URL: https://arxiv.org/abs/2603.19328
   - Why read: gives a strong explanation for your own result: violation reduction may not translate into significant success improvement because agents often fail to recover after intervention.

4. `paper3_agentspec_2025.pdf`
   - Title: *AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents*
   - URL: https://arxiv.org/abs/2503.18666
   - Why read: runtime enforcement DSL. Useful for framing your verifier, but also a threat to novelty if your contribution is only “rules block unsafe actions.”

5. `paper3_progent_2025.pdf`
   - Title: *Progent: Programmable Privilege Control for LLM Agents*
   - URL: https://arxiv.org/abs/2504.11703
   - Why read: tool-level privilege control and policy enforcement. Useful contrast: security/privilege policy versus ontology-grounded action admissibility.

### Paper 2: SOP, Procedure, and Workflow Extraction

1. `paper2_agent_s_sop_automation_2025.pdf`
   - Title: *Agent-S: LLM Agentic workflow to automate Standard Operating Procedures*
   - URL: https://arxiv.org/abs/2503.15520
   - Why read: directly uses SOPs as agent workflows. Important for defining what your SOP-to-action layer adds beyond SOP automation.

2. `paper2_paged_procedural_graph_extraction_2024.pdf`
   - Title: *PAGED: A Benchmark for Procedural Graphs Extraction from Documents*
   - URL: https://arxiv.org/abs/2408.03630
   - Why read: procedural graph extraction benchmark. Useful for action sequence, constraint, and graph evaluation design.

3. `paper2_dialog_workflow_extraction_2025.pdf`
   - Title: *Turning Conversations into Workflows: A Framework to Extract and Evaluate Dialog Workflows for Service AI Agents*
   - URL: https://arxiv.org/abs/2502.17321
   - Why read: very relevant if you use customer-service dialogue or SOP-like data. It also provides a useful workflow evaluation protocol through simulation.

4. `paper2_process_model_representation_2025.pdf`
   - Title: *What is the Best Process Model Representation? A Comparative Analysis for Process Modeling with Large Language Models*
   - URL: https://arxiv.org/abs/2507.11356
   - Why read: helps justify why your intermediate representation should not simply be BPMN. You need an action-oriented IR with object binding, preconditions, effects, and policies.

5. `paper2_bpmn_generation_parallelism_2025.pdf`
   - Title: *Leveraging Machine Learning and Enhanced Parallelism Detection for BPMN Model Generation from Text*
   - URL: https://arxiv.org/abs/2507.08362
   - Why read: useful for understanding the BPMN baseline space and the difficulty of gateways/parallelism.

### Paper 1: Action Indexing and Tool Retrieval

1. `paper1_in_n_out_api_graph_2025.pdf`
   - Title: *In-N-Out: A Parameter-Level API Graph Dataset for Tool Agents*
   - URL: https://arxiv.org/abs/2509.01560
   - Why read: most relevant to action indexing because it models parameter-level API dependencies. Your action index should learn from this but extend to ontology/state/policy constraints.

2. `paper1_tool_to_agent_retrieval_2025.pdf`
   - Title: *Tool-to-Agent Retrieval: Bridging Tools and Agents for Scalable LLM Multi-Agent Systems*
   - URL: https://arxiv.org/abs/2511.01854
   - Why read: relevant to hierarchical retrieval from tools to agents. Useful for designing action-to-object/action-to-agent retrieval.

3. `paper1_toolgen_2024.pdf`
   - Title: *ToolGen: Unified Tool Retrieval and Calling via Generation*
   - URL: https://arxiv.org/abs/2410.03439
   - Why read: strong baseline idea for large-scale tool retrieval/calling. Your action indexing must clarify why explicit ontology-grounded retrieval is preferable or complementary.

4. `paper1_fittext_memetic_tool_retrieval_2026.pdf`
   - Title: *FitText: Evolving Agent Tool Ecologies via Memetic Retrieval*
   - URL: https://arxiv.org/abs/2605.02411
   - Why read: shows dynamic retrieval inside the agent loop. Useful contrast to static action indexing.

5. `paper1_llm_wiki_retrieval_as_reasoning_2026.pdf`
   - Title: *Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki*
   - URL: https://arxiv.org/abs/2605.25480
   - Why read: not action-specific, but useful for arguing that retrieval for agents is shifting from flat chunk lookup to structured traversal.

## Critical Takeaways

1. **Paper 3 must be repositioned against formal/runtime enforcement work.**
   The strongest novelty is not “we block invalid actions.” Existing work is already close. The defensible angle is ontology-grounded action admissibility plus empirical analysis of repair failure modes.

2. **Paper 2 should avoid being a BPMN generation paper.**
   BPMN/process extraction literature is already mature. The better claim is extraction of executable action-layer representations from SOP-like unstructured data.

3. **Paper 1 needs a stronger index definition.**
   Ordinary vector retrieval over action descriptions is not enough. The index must include action-object binding, parameter dependencies, precondition/effect compatibility, policy constraints, and possibly state-conditioned retrieval.

4. **Your three papers should share one conceptual spine.**
   Paper 2 produces action schemas from text, Paper 1 indexes and retrieves action schemas, and Paper 3 verifies and repairs action execution. The action layer is the common object of study.

