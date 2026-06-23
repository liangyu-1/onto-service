# Action Layer Paper Drafts

These drafts use a standard two-column LaTeX conference-like skeleton. They were initially planned as ACM `acmart` drafts, but this workspace's TeX Live installation does not include `acmart.cls`, so the current files are made self-contained with standard LaTeX packages.

The nearest suitable venues checked on 2026-06-03 include:

| Venue | Deadline | Notes |
| --- | --- | --- |
| EMNLP 2026 Industry Track | 2026-06-16 AoE | Suitable for deployed NLP systems and industrial language applications. |
| EMNLP 2026 System Demonstrations | 2026-07-10 AoE | Suitable if the work is framed as a working system/demo. |
| REALM @ EMNLP 2026 | 2026-07-20 AoE | Suitable for the agent planning paper. |
| AAAI-27 Main Track | Abstract 2026-07-21, full paper 2026-07-28 AoE | Suitable for the planning paper if experiments are strong. |
| WSDM 2027 Full Papers | Abstract 2026-08-17, full paper 2026-08-24 AoE | Best unified template for retrieval, indexing, and agentic systems. |

Chosen working target: WSDM 2027-style research papers. For an official ACM/WSDM submission, install the ACM `acmart` package and switch the preamble back to the official template.

Current three-paper research line:

- Paper 1, provisional title: **Collaborative Action Ontogenesis: A Multi-Agent Human-in-the-Loop Framework for Building and Evolving Ontology Action Layers**.
- Paper 2: **Ontology-Grounded Action Extraction from Unstructured Procedural Documents**.
- Paper 3: **Ontology-Grounded Action Semantics for Policy-Constrained LLM Agents**.

`paper1_action_indexing_wsdm2027.tex` is now a legacy candidate draft. Action indexing may remain a component for candidate discovery, but it is no longer the planned first paper unless later experiments justify an independent retrieval contribution. A new Paper 1 manuscript should be written only after the collaborative proposal-validation-consensus framework and its evaluation protocol are fixed.

Important limitation: these are research-paper drafts, not submission-ready papers. The result tables intentionally contain placeholders instead of fabricated numbers.
