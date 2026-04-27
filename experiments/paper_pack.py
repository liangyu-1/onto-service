from __future__ import annotations

import pathlib
from typing import Any, Dict, List

from experiments.common import RESULTS_DIR, read_json, read_jsonl, write_csv, write_json


def _collect_latest(prefix: str) -> pathlib.Path | None:
    candidates = sorted([p for p in RESULTS_DIR.glob(f"{prefix}_*") if p.is_dir()])
    return candidates[-1] if candidates else None


def build_paper_artifact_pack(out_dir: pathlib.Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = {
        "exp1_exp2": _collect_latest("exp1_exp2"),
        "exp3_counterfactual": _collect_latest("exp3_counterfactual"),
        "exp4_generalization": _collect_latest("exp4_generalization"),
        "exp5_drift": _collect_latest("exp5_drift"),
    }

    index: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []
    for name, path in latest.items():
        if path is None:
            continue
        index.append({"experiment": name, "path": str(path)})
        summary = path / "summary.json"
        if summary.exists():
            body = read_json(summary)
            for row in body.get("summaries", []):
                enriched = dict(row)
                enriched["experiment"] = name
                summary_rows.append(enriched)

    write_json(out_dir / "artifact_index.json", {"experiments": index})
    if summary_rows:
        write_csv(
            out_dir / "summary.csv",
            summary_rows,
            [
                "experiment",
                "policy",
                "steps",
                "avg_regret",
                "cnu",
                "utr",
                "hit_rate",
                "latency_p50_ms",
                "latency_p95_ms",
                "avg_rebuild_ms",
                "avg_storage_overhead_mb",
                "bias_rate",
                "consistency_violation_rate",
            ],
        )

    readme = [
        "# Paper Artifact Pack",
        "",
        "This package indexes the latest outputs from exp1-exp5.",
        "",
        "## Included Experiments",
    ]
    for item in index:
        readme.append(f"- {item['experiment']}: `{item['path']}`")
    readme.append("")
    readme.append("## Core Output Files")
    readme.append("- `artifact_index.json`: pointers to experiment runs")
    readme.append("- `summary.csv`: merged policy metrics across experiments")
    (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    return {"index": index, "summary_rows": len(summary_rows)}

