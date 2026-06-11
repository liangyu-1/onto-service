#!/usr/bin/env python3
"""Download open-access papers for ontology-enhanced IR research."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "papers" / "ontology_ir"
PDF_DIR = OUT_DIR / "pdf"
README = OUT_DIR / "README.md"


OPEN_PAPERS = [
    {
        "filename": "1312.4425_ontology_based_model_indexing_retrieval.pdf",
        "title": "An Ontology-based Model for Indexing and Retrieval",
        "url": "https://arxiv.org/pdf/1312.4425v1",
    },
    {
        "filename": "1207.5745_semantic_ir_using_ontology_university_domain.pdf",
        "title": "Semantic Information Retrieval Using Ontology In University Domain",
        "url": "https://arxiv.org/pdf/1207.5745v1",
    },
    {
        "filename": "1807.07966_ontological_features_keywords_text_retrieval.pdf",
        "title": "Exploring Combinations of Ontological Features and Keywords for Text Retrieval",
        "url": "https://arxiv.org/pdf/1807.07966v1",
    },
    {
        "filename": "1511.01259_wikipedia_ontology_based_ir_local_experts.pdf",
        "title": "Transforming Wikipedia into an Ontology-based Information Retrieval Search Engine for Local Experts using a Third-Party Taxonomy",
        "url": "https://arxiv.org/pdf/1511.01259v2",
    },
    {
        "filename": "2603.21139_ontology_driven_personalized_ir_xml.pdf",
        "title": "Ontology-driven personalized information retrieval for XML documents",
        "url": "https://arxiv.org/pdf/2603.21139v1",
    },
    {
        "filename": "2306.10300_faceted_ontological_principles_educational_domain.pdf",
        "title": "Reorganizing Educational Institutional Domain using Faceted Ontological Principles",
        "url": "https://arxiv.org/pdf/2306.10300v1",
    },
    {
        "filename": "2307.13427_semantic_ir_ontology_engineering_review.pdf",
        "title": "Comprehensive Review on Semantic Information Retrieval and Ontology Engineering",
        "url": "https://arxiv.org/pdf/2307.13427v1",
    },
    {
        "filename": "1411.3761_hybrid_domain_specific_ir_ontology_rules.pdf",
        "title": "A Hybrid Approach to Finding Relevant Social Media Content for Complex Domain Specific Information Needs",
        "url": "https://arxiv.org/pdf/1411.3761v1",
    },
    {
        "filename": "1709.08880_similarity_between_ontology_concepts.pdf",
        "title": "An enhanced method to compute the similarity between concepts of ontology",
        "url": "https://arxiv.org/pdf/1709.08880v1",
    },
    {
        "filename": "2502.18992_ontologyrag_biomedical_code_mapping.pdf",
        "title": "OntologyRAG: Better and Faster Biomedical Code Mapping with Retrieval-Augmented Generation Leveraging Ontology Knowledge Graphs and Large Language Models",
        "url": "https://arxiv.org/pdf/2502.18992v1",
    },
    {
        "filename": "2023_cl_4_2_measuring_attribution_nlg.pdf",
        "title": "Measuring Attribution in Natural Language Generation Models",
        "url": "https://aclanthology.org/2023.cl-4.2.pdf",
    },
    {
        "filename": "2305.14627_alce_llm_citations.pdf",
        "title": "Enabling Large Language Models to Generate Text with Citations",
        "url": "https://arxiv.org/pdf/2305.14627",
    },
    {
        "filename": "2309.15217_ragas_rag_evaluation.pdf",
        "title": "RAGAS: Automated Evaluation of Retrieval Augmented Generation",
        "url": "https://arxiv.org/pdf/2309.15217",
    },
    {
        "filename": "2311.09476_ares_rag_evaluation.pdf",
        "title": "ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems",
        "url": "https://arxiv.org/pdf/2311.09476",
    },
    {
        "filename": "2412.15235_og_rag_ontology_grounded_rag.pdf",
        "title": "OG-RAG: Ontology-Grounded Retrieval-Augmented Generation",
        "url": "https://arxiv.org/pdf/2412.15235",
    },
    {
        "filename": "2404.16130_graphrag_local_to_global.pdf",
        "title": "From Local to Global: A Graph RAG Approach to Query-Focused Summarization",
        "url": "https://arxiv.org/pdf/2404.16130",
    },
    {
        "filename": "2408.08921_graph_rag_survey.pdf",
        "title": "Graph Retrieval-Augmented Generation: A Survey",
        "url": "https://arxiv.org/pdf/2408.08921",
    },
    {
        "filename": "pav_provenance_authoring_versioning.pdf",
        "title": "PAV ontology: provenance, authoring and versioning",
        "url": "https://jbiomedsem.biomedcentral.com/counter/pdf/10.1186/2041-1480-4-37.pdf",
    },
]


LINK_ONLY_PAPERS = [
    {
        "title": "A review of ontology based query expansion",
        "url": "https://www.sciencedirect.com/science/article/pii/S0306457306001476",
        "note": "ScienceDirect page; may require institutional access.",
    },
    {
        "title": "Semantically enhanced Information Retrieval: An ontology-based approach",
        "url": "https://www.sciencedirect.com/science/article/pii/S1570826810000910",
        "note": "ScienceDirect page; may require institutional access.",
    },
    {
        "title": "An ontology-based retrieval system using semantic indexing",
        "url": "https://www.sciencedirect.com/science/article/abs/pii/S030643791100113X",
        "note": "ScienceDirect page; may require institutional access.",
    },
    {
        "title": "Mimir: An open-source semantic search framework",
        "url": "https://www.sciencedirect.com/science/article/abs/pii/S1570826814001036",
        "note": "ScienceDirect page; may require institutional access.",
    },
    {
        "title": "SemOIR: An ontology-based semantic information retrieval system",
        "url": "https://experts.illinois.edu/en/publications/semoir-an-ontology-based-semantic-information-retrieval-system/",
        "note": "Metadata page; direct open PDF not found in this script.",
    },
    {
        "title": "Named Graphs, Provenance and Trust",
        "url": "https://www.sciencedirect.com/science/article/pii/S1570826805000235",
        "note": "ScienceDirect page; may require institutional access.",
    },
    {
        "title": "PROV-O: The PROV Ontology",
        "url": "https://www.w3.org/TR/prov-o/",
        "note": "W3C Recommendation is published as HTML; no stable PDF URL.",
    },
    {
        "title": "ProVe: Automated provenance verification of knowledge graphs against textual sources",
        "url": "https://journals.sagepub.com/doi/10.3233/SW-233467",
        "note": "Journal page; may require institutional access.",
    },
    {
        "title": "TREC 2020 Health Misinformation Track",
        "url": "https://pages.nist.gov/trec-browser/trec29/misinfo/overview",
        "note": "Benchmark overview page, not a single paper PDF.",
    },
    {
        "title": "Ontology-based RAG for GenAI-supported Additive Manufacturing",
        "url": "https://www.nist.gov/node/1855761",
        "note": "NIST page; direct paper PDF not encoded here.",
    },
    {
        "title": "Query expansion using the UMLS Metathesaurus",
        "url": "https://pubmed.ncbi.nlm.nih.gov/9357673/",
        "note": "PubMed record; direct open PDF not encoded here.",
    },
    {
        "title": "Evaluation of query expansion using MeSH in PubMed",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2747526/",
        "note": "Open PMC article; use page if PDF path changes.",
    },
    {
        "title": "Improving EHR search using UMLS-based query expansion through random walks",
        "url": "https://pubmed.ncbi.nlm.nih.gov/24768598/",
        "note": "PubMed record; direct open PDF not encoded here.",
    },
    {
        "title": "SemEHR: A general-purpose semantic search system to surface semantic data from clinical notes",
        "url": "https://pubmed.ncbi.nlm.nih.gov/29361077/",
        "note": "PubMed record; direct open PDF not encoded here.",
    },
]


def download(url: str, path: Path) -> tuple[bool, str]:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    cmd = [
        "curl",
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--max-time",
        "45",
        "--connect-timeout",
        "10",
        "--retry",
        "1",
        "--user-agent",
        "Mozilla/5.0 (compatible; onto-service paper downloader)",
        "--output",
        str(tmp_path),
        url,
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        if tmp_path.exists():
            tmp_path.unlink()
        return False, proc.stderr.strip() or f"curl exited with {proc.returncode}"

    data = tmp_path.read_bytes()
    if not data.startswith(b"%PDF"):
        tmp_path.unlink()
        return False, "downloaded content is not a PDF"

    tmp_path.replace(path)
    digest = hashlib.sha256(data).hexdigest()[:12]
    return True, f"{len(data)} bytes, sha256={digest}"


def write_readme(results: list[dict[str, str]]) -> None:
    lines = [
        "# Ontology-Enhanced IR Papers",
        "",
        "This folder contains open-access papers downloaded for ontology-enhanced information retrieval, trustworthy input, provenance, attribution, and RAG evaluation research.",
        "",
        "## Downloaded PDFs",
        "",
    ]
    for item in results:
        if item["status"] == "downloaded":
            lines.append(f"- [{item['title']}](pdf/{item['filename']})")
            lines.append(f"  Source: {item['url']}")
            lines.append(f"  Check: {item['message']}")
            lines.append("")

    lines.extend(["## Not Downloaded Automatically", ""])
    for item in results:
        if item["status"] != "downloaded":
            lines.append(f"- {item['title']}")
            lines.append(f"  Source: {item['url']}")
            lines.append(f"  Reason: {item['message']}")
            lines.append("")

    lines.extend(["## Link-Only Items", ""])
    for item in LINK_ONLY_PAPERS:
        lines.append(f"- [{item['title']}]({item['url']})")
        lines.append(f"  Note: {item['note']}")
        lines.append("")

    README.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []
    for index, paper in enumerate(OPEN_PAPERS, 1):
        target = PDF_DIR / paper["filename"]
        if target.exists() and target.stat().st_size > 0:
            message = f"already exists, {target.stat().st_size} bytes"
            status = "downloaded"
        else:
            print(f"[{index}/{len(OPEN_PAPERS)}] {paper['title']}", flush=True)
            ok, message = download(paper["url"], target)
            status = "downloaded" if ok else "failed"
            if not ok and target.exists():
                target.unlink()
            time.sleep(0.5)

        results.append(
            {
                "title": paper["title"],
                "url": paper["url"],
                "filename": paper["filename"],
                "status": status,
                "message": message,
            }
        )

    write_readme(results)
    downloaded = sum(1 for item in results if item["status"] == "downloaded")
    failed = len(results) - downloaded
    print(f"Downloaded/open PDFs available: {downloaded}")
    print(f"Failed direct PDF downloads: {failed}")
    print(f"Report: {README}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
