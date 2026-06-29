# Ontology Function/Workflow/Execution Paper Drafts

These drafts use a standard two-column LaTeX conference-like skeleton. They were initially planned as ACM `acmart` drafts, but this workspace's TeX Live installation does not include `acmart.cls`, so the current files are made self-contained with standard LaTeX packages.

The nearest suitable venues checked on 2026-06-03 include:

| Venue | Deadline | Notes |
| --- | --- | --- |
| EMNLP 2026 Industry Track | 2026-06-16 AoE | Suitable for deployed NLP systems and industrial language applications. |
| EMNLP 2026 System Demonstrations | 2026-07-10 AoE | Suitable if the work is framed as a working system/demo. |
| REALM @ EMNLP 2026 | 2026-07-20 AoE | Suitable for the agent planning paper. |
| AAAI-27 Main Track | Abstract 2026-07-21, full paper 2026-07-28 AoE | Suitable for the planning paper if experiments are strong. |
| WSDM 2027 Full Papers | Abstract 2026-08-17, full paper 2026-08-24 AoE | A workable two-column template for the current drafts; not a claim that WSDM is the final target. |

Chosen working target: WSDM 2027-style research drafts. For an official ACM/WSDM submission, install the ACM `acmart` package and switch the preamble back to the official template.

Current three-paper research line:

- Paper 1: **Autonomous Construction of Ontology Function Layers from Operational Artifacts**.
- Paper 2: **Inducing Executable Ontology Workflow Skills from Procedural Documents**.
- Paper 3: **Adversarially Robust and Controllable Execution of Ontology Workflows**.

The file names still contain earlier working labels for compatibility with existing compile commands. The manuscript titles inside the `.tex` files are authoritative.

The current experiment split is:

- Server A: Paper 2 workflow induction + Paper 3 robust execution.
- Server B: Paper 1 autonomous Function Layer construction.

Paper 2 and Paper 3 should first be evaluated with gold or curated Function/Workflow inputs. Paper 1 outputs should be used later as a cascade setting, not as the only evidence for Paper 2 or Paper 3.

Important limitation: these are research-paper drafts, not submission-ready papers. They specify methods, datasets, and metrics, but they do not claim experimental results before the experiments are run.
