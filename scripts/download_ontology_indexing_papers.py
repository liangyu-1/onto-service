#!/usr/bin/env python3
"""Download open-access papers for ontology indexing research."""

from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "papers" / "ontology_indexing"
PDF_DIR = OUT_DIR / "pdf"
README = OUT_DIR / "README.md"


OPEN_PAPERS = [
    {
        "category": "ontology semantic indexing",
        "filename": "1312.4425_ontology_based_model_indexing_retrieval.pdf",
        "title": "An Ontology-based Model for Indexing and Retrieval",
        "published": "arXiv preprint, 2013-12",
        "url": "https://arxiv.org/pdf/1312.4425v1",
    },
    {
        "category": "ontology semantic indexing",
        "filename": "1409.0921_generalized_framework_ontology_based_ir_public_transportation.pdf",
        "title": "A Generalized Framework for Ontology-Based Information Retrieval: Application to a Public-Transportation System",
        "published": "arXiv preprint, 2014-09",
        "url": "https://arxiv.org/pdf/1409.0921v1",
    },
    {
        "category": "ontology semantic indexing",
        "filename": "1201.5102_ontologies_indexing_searching_video_courses.pdf",
        "title": "Conception and Use of Ontologies for Indexing and Searching by Semantic Contents of Video Courses",
        "published": "arXiv preprint, 2012-01",
        "url": "https://arxiv.org/pdf/1201.5102v1",
    },
    {
        "category": "ontology semantic indexing",
        "filename": "1003.1460_ontology_based_query_expansion_wsd.pdf",
        "title": "Ontology Based Query Expansion Using Word Sense Disambiguation",
        "published": "arXiv preprint, 2010-03",
        "url": "https://arxiv.org/pdf/1003.1460v1",
    },
    {
        "category": "ontology semantic indexing",
        "filename": "1703.07381_statistical_multimedia_ir_using_ontology.pdf",
        "title": "Improving Statistical Multimedia Information Retrieval Model by using Ontology",
        "published": "arXiv preprint, 2017-03",
        "url": "https://arxiv.org/pdf/1703.07381v1",
    },
    {
        "category": "industrial knowledge indexing",
        "filename": "2012.09049_knowledge_graphs_manufacturing_production_slr.pdf",
        "title": "Knowledge Graphs in Manufacturing and Production: A Systematic Literature Review",
        "published": "arXiv preprint, 2020-12",
        "url": "https://arxiv.org/pdf/2012.09049",
    },
    {
        "category": "industrial knowledge indexing",
        "filename": "2404.06571_kg_enrich_chatgpt_manufacturing_service_discovery.pdf",
        "title": "Building A Knowledge Graph to Enrich ChatGPT Responses in Manufacturing Service Discovery",
        "published": "arXiv preprint, 2024-04",
        "url": "https://arxiv.org/pdf/2404.06571v1",
    },
    {
        "category": "industrial knowledge indexing",
        "filename": "2506.13026_kg_llm_manufacturing_process_planning.pdf",
        "title": "Knowledge Graph Fusion with Large Language Models for Accurate, Explainable Manufacturing Process Planning",
        "published": "arXiv preprint, 2025-06",
        "url": "https://arxiv.org/pdf/2506.13026v1",
    },
    {
        "category": "industrial knowledge indexing",
        "filename": "2507.22619_manufacturing_knowledge_access_llm_context_prompting.pdf",
        "title": "Enhancing Manufacturing Knowledge Access with LLMs and Context-aware Prompting",
        "published": "arXiv preprint, 2025-07",
        "url": "https://arxiv.org/pdf/2507.22619v1",
    },
    {
        "category": "industrial knowledge indexing",
        "filename": "2602.01858_soprag_industrial_sop_multi_view_graph_experts_retrieval.pdf",
        "title": "SOPRAG: Multi-view Graph Experts Retrieval for Industrial Standard Operating Procedures",
        "published": "arXiv preprint, 2026-02",
        "url": "https://arxiv.org/pdf/2602.01858v1",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2412.05547_kg_retriever_efficient_knowledge_indexing_rag_llms.pdf",
        "title": "KG-Retriever: Efficient Knowledge Indexing for Retrieval-Augmented Large Language Models",
        "published": "arXiv preprint, 2024-12",
        "url": "https://arxiv.org/pdf/2412.05547v1",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2601.16462_graph_anchored_knowledge_indexing_rag.pdf",
        "title": "Graph-Anchored Knowledge Indexing for Retrieval-Augmented Generation",
        "published": "arXiv preprint, 2026-01",
        "url": "https://arxiv.org/pdf/2601.16462v1",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2505.24226_e2graphrag_efficiency_effectiveness.pdf",
        "title": "E^2GraphRAG: Streamlining Graph-based RAG for High Efficiency and Effectiveness",
        "published": "arXiv preprint, 2025-05",
        "url": "https://arxiv.org/pdf/2505.24226v1",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2410.05779_lightrag_simple_fast_rag.pdf",
        "title": "LightRAG: Simple and Fast Retrieval-Augmented Generation",
        "published": "arXiv preprint, 2024-10",
        "url": "https://arxiv.org/pdf/2410.05779v2",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2408.08921_graph_retrieval_augmented_generation_survey.pdf",
        "title": "Graph Retrieval-Augmented Generation: A Survey",
        "published": "arXiv preprint, 2024-08",
        "url": "https://arxiv.org/pdf/2408.08921",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2405.16933_pg_rag_self_learning_knowledge_retrieval_indexer.pdf",
        "title": "PG-RAG: Empowering LLMs to Set up a Knowledge Retrieval Indexer via Self-Learning",
        "published": "arXiv preprint, 2024-05",
        "url": "https://arxiv.org/pdf/2405.16933v1",
    },
    {
        "category": "kg/graphrag indexing",
        "filename": "2502.09304_ket_rag_multi_granular_indexing_graphrag.pdf",
        "title": "KET-RAG: Cost-Efficient Multi-Granular Indexing Framework for Graph-RAG",
        "published": "arXiv preprint, 2025-02",
        "url": "https://arxiv.org/pdf/2502.09304v1",
    },
    {
        "category": "trust/version/evolution indexing",
        "filename": "2510.08109_versionrag_version_aware_rag_evolving_documents.pdf",
        "title": "VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents",
        "published": "arXiv preprint, 2025-10",
        "url": "https://arxiv.org/pdf/2510.08109v1",
    },
]


LINK_ONLY_PAPERS = [
    {
        "category": "ontology semantic indexing",
        "title": "Semantically enhanced Information Retrieval: An ontology-based approach",
        "url": "https://www.sciencedirect.com/science/article/pii/S1570826810000910",
        "published": "Journal of Web Semantics, Volume 9 Issue 4, 2011-12",
        "note": "ScienceDirect page; direct PDF may require institutional access.",
    },
    {
        "category": "ontology semantic indexing",
        "title": "An ontology-based retrieval system using semantic indexing",
        "url": "https://www.sciencedirect.com/science/article/abs/pii/S030643791100113X",
        "published": "Information Systems, Volume 37 Issue 4, 2012-06",
        "note": "ScienceDirect page; direct PDF may require institutional access.",
    },
    {
        "category": "industrial knowledge indexing",
        "title": "i-Dataquest: A heterogeneous information retrieval tool using data graph for the manufacturing industry",
        "url": "https://www.sciencedirect.com/science/article/pii/S0166361521000415",
        "published": "Computers in Industry, Volume 132, 2021-11",
        "note": "ScienceDirect page; direct PDF may require institutional access.",
    },
    {
        "category": "industrial knowledge indexing",
        "title": "A Knowledge Graph for Industry 4.0",
        "url": "https://link.springer.com/chapter/10.1007/978-3-030-49461-2_27",
        "published": "ESWC 2020 / LNCS 12123, published 2020-05-27",
        "note": "Springer page; use institutional access or author's copy if available.",
    },
    {
        "category": "trust/version/evolution indexing",
        "title": "Named Graphs, Provenance and Trust",
        "url": "https://www.sciencedirect.com/science/article/pii/S1570826805000235",
        "published": "Web Semantics, Volume 3 Issue 4, 2005-12",
        "note": "ScienceDirect page; direct PDF may require institutional access.",
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
        "60",
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
        "# Ontology Indexing Papers",
        "",
        "This folder is scoped to ontology indexing, industrial knowledge indexing, KG/GraphRAG indexing, and version/trust-aware indexing.",
        "",
        "Critical note: not every paper here is an ontology-indexing paper. Several GraphRAG and industrial KG papers are included because they define current indexing baselines that an ontology-indexing paper must compare against.",
        "",
        "## Downloaded PDFs",
        "",
    ]
    for item in results:
        if item["status"] == "downloaded":
            lines.append(f"- [{item['title']}](pdf/{item['filename']})")
            lines.append(f"  Category: {item['category']}")
            lines.append(f"  Published: {item['published']}")
            lines.append(f"  Source: {item['url']}")
            lines.append(f"  Check: {item['message']}")
            lines.append("")

    lines.extend(["## Failed Direct PDF Downloads", ""])
    failed = [item for item in results if item["status"] != "downloaded"]
    if failed:
        for item in failed:
            lines.append(f"- {item['title']}")
            lines.append(f"  Category: {item['category']}")
            lines.append(f"  Published: {item['published']}")
            lines.append(f"  Source: {item['url']}")
            lines.append(f"  Reason: {item['message']}")
            lines.append("")
    else:
        lines.append("- None")
        lines.append("")

    lines.extend(["## Link-Only Items", ""])
    for item in LINK_ONLY_PAPERS:
        lines.append(f"- [{item['title']}]({item['url']})")
        lines.append(f"  Category: {item['category']}")
        lines.append(f"  Published: {item['published']}")
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
                "category": paper["category"],
                "title": paper["title"],
                "published": paper["published"],
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
