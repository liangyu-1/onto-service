# Recent Related Work Reading Guide

Scope note: this guide focuses on papers from 2024-2026. A few early-2024 papers are slightly outside a strict rolling 24-month window from 2026-06-04, but they are kept because they are foundational for RAG retrieval evaluation, GraphRAG, and agent benchmarks.

## Priority A: Read Deeply

| Topic | Paper | Local PDF | Why it matters |
|---|---|---|---|
| Retrieval evaluation | Salemi and Zamani, 2024, Evaluating Retrieval Quality in RAG | `references/salemi_2024_erag.pdf` | Use this to design evaluation beyond Recall@k. The key lesson is that retrieval should be judged by downstream utility, not only query-document relevance. |
| Retrieval failure analysis | Cuconasu et al., 2024, The Power of Noise | `references/cuconasu_2024_power_of_noise.pdf` | Important counterexample for naive retrieval assumptions. It supports the claim that action retrieval must optimize executability and task utility, not just semantic relevance. |
| Adaptive retrieval | Rathee et al., 2025, QUAM | `references/rathee_2025_quam.pdf` | Closest IR-side inspiration for graph-aware adaptive retrieval. Useful for designing action-neighborhood expansion and reranking under limited budget. |
| Tool/action retrieval | Zheng et al., 2024, ToolRerank | `references/zheng_2024_toolrerank.pdf` | Directly relevant to action indexing because it treats tool selection as retrieval plus hierarchy-aware reranking. Map its tool hierarchy idea to ontology action taxonomy. |
| Query-action alignment | Zhang et al., 2024, Data-Efficient Massive Tool Retrieval | `references/zhang_2024_massive_tool_retrieval.pdf` | Useful for low-resource action retrieval. The query-tool alignment formulation can be adapted to query-action alignment. |
| SOP/action extraction | Rula and D'Souza, 2024, Procedural Extraction from Documents | `references/rula_2024_procedural_extraction.pdf` | Closest paper to your SOP-action extraction idea. It uses ontology-informed in-context learning and exposes hallucination/layout/ontology-application risks. |
| Process extraction | Neuberger et al., 2024, Universal Prompting Strategy for Process Model Information Extraction | `references/neuberger_2024_universal_prompting_process_extraction.pdf` | Strong baseline design for extracting activities, actors, and relations from process text. Adapt it, but extend output to Action IR. |
| Stateful tool agents | Lu et al., 2024, ToolSandbox | `references/lu_2024_toolsandbox.pdf` | Important for paper three. It evaluates stateful tool execution and intermediate milestones, which is close to ontology action planning validation. |
| Agent domain policy | Yao et al., 2024, tau-bench | `references/yao_2024_tau_bench.pdf` | Good benchmark model for tool-agent-user interaction under domain policies. Useful for action precondition, policy, and constraint evaluation. |
| Enterprise agents | Drouin et al., 2024, WorkArena | `references/drouin_2024_workarena.pdf` | Strong motivation for enterprise action planning, although it is web-agent oriented rather than ontology-action oriented. |

## Priority B: Read for Method Components

| Topic | Paper | Local PDF | Use |
|---|---|---|---|
| Graph retrieval | Edge et al., 2024, GraphRAG | `references/edge_2024_graphrag.pdf` | Background for graph-based indexing and community/global retrieval. Do not copy its task setting directly. |
| Efficient graph RAG | Guo et al., 2024, LightRAG | `references/guo_2024_lightrag.pdf` | Useful for incremental graph-plus-vector retrieval design. |
| Graph memory | Gutierrez et al., 2024, HippoRAG | `references/gutierrez_2024_hipporag.pdf` | Useful for spreading-activation style retrieval over action/object/state graphs. |
| KG-guided RAG | Zhu et al., 2025, KG2RAG | `references/zhu_2025_kg2rag.pdf` | Useful for seed retrieval plus KG expansion and organization. |
| Ontology RAG | Tiwari et al., 2025, OntoRAG | `references/tiwari_2025_ontorag.pdf` | Useful contrast: it derives ontologies from documents, while your paper two assumes an ontology and extracts/grounds actions. |
| Process modeling | Kourani et al., 2024, Process Modeling With LLMs | `references/kourani_2024_process_modeling_llms.pdf` | Baseline for LLM-assisted process model generation. Use its validation ideas, but do not equate BPMN generation with Action IR extraction. |
| Process mining benchmark | Berti et al., 2024, PM-LLM-Benchmark | `references/berti_2024_pm_llm_benchmark.pdf` | Auxiliary evaluation inspiration for process-specific LLM competence. |
| Semantics-aware process mining | Rebmann et al., 2024 | `references/rebmann_2024_semantics_process_mining.pdf` | Useful for evaluating semantic understanding of processes, not enough for ontology-grounded action validation. |
| Stateful multi-turn tool use | Wang et al., 2025, DialogTool | `references/wang_2025_dialogtool.pdf` | Useful for long-horizon stateful tool-use evaluation in paper three. |
| Interactive API worlds | Trivedi et al., 2024, AppWorld | `references/trivedi_2024_appworld.pdf` | Useful benchmark style for API-rich agent tasks. |
| Planning benchmark | Xie et al., 2024, TravelPlanner | `references/xie_2024_travelplanner.pdf` | Useful for multi-constraint planning evaluation, but less directly tied to ontology action layers. |

## Priority C: Background Only

| Topic | Paper | Local PDF | Reason |
|---|---|---|---|
| Retrieval toolkit | Abdallah et al., 2025, Rankify | `references/abdallah_2025_rankify.pdf` | Useful for reproducible evaluation infrastructure, not a core research idea. |
| Ontology learning survey | Du et al., 2024 | `references/du_2024_ontology_learning_review.pdf` | Use for related work framing only. |
| Ontology embeddings | Wang et al., 2024, EIKE | `references/wang_2024_eike.pdf` | Useful if you later design action/ontology embeddings; not central to current SOP-action method. |

## Recommended Reading Order

1. Read `salemi_2024_erag.pdf`, `cuconasu_2024_power_of_noise.pdf`, and `rathee_2025_quam.pdf` first to solidify the action-indexing evaluation logic.
2. Read `zheng_2024_toolrerank.pdf` and `zhang_2024_massive_tool_retrieval.pdf` next to translate tool retrieval into ontology action retrieval.
3. Read `rula_2024_procedural_extraction.pdf` and `neuberger_2024_universal_prompting_process_extraction.pdf` for paper two's SOP-to-Action-IR extraction method.
4. Read `lu_2024_toolsandbox.pdf`, `yao_2024_tau_bench.pdf`, and `drouin_2024_workarena.pdf` for paper three's agent planning evaluation design.

