#!/usr/bin/env python3
"""Promote the highest-confidence reviewed overlays to gold status.

Reads the output of auto_review_apis_guru_all.py and produces a gold-format
dataset under:

    dataset/function_layer_benchmarks/generated/apis_guru/gold_all/

All promoted records keep their original content but change review_status to
"gold" and add an auto-promotion note.  This is **not** equivalent to the
manual gold curation done for the 3 pilot APIs; it is an automated best-effort
gold-compatible dataset for experiments at scale.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote reviewed overlays to gold.")
    parser.add_argument(
        "--reviewed-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru/reviewed_all",
        help="Directory containing per-api reviewed folders.",
    )
    parser.add_argument(
        "--output-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru/gold_all",
        help="Output directory for gold files.",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=5.0,
        help="Minimum auto-review score to promote to gold.",
    )
    parser.add_argument(
        "--max-gold-per-api",
        type=int,
        default=10,
        help="Maximum gold functions promoted per API.",
    )
    parser.add_argument(
        "--max-bound-objects",
        type=int,
        default=2,
        help="Only promote overlays with at most this many bound object types.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reviewed_root = Path(args.reviewed_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    api_names = sorted(
        d.name for d in reviewed_root.iterdir()
        if d.is_dir() and (d / "ontology_overlay.reviewed.jsonl").exists()
    )

    gold_overlays: list[dict[str, Any]] = []
    gold_objects: dict[str, dict[str, Any]] = {}
    gold_functions: list[dict[str, Any]] = []

    for api_name in api_names:
        api_dir = reviewed_root / api_name
        ontology = json.load((api_dir / "ontology.reviewed.json").open(encoding="utf-8"))
        overlays = [json.loads(line) for line in (api_dir / "ontology_overlay.reviewed.jsonl").open(encoding="utf-8") if line.strip()]

        scored = [(score_overlay(ov), ov) for ov in overlays if ov.get("review_status") == "reviewed"]
        scored.sort(key=lambda x: -x[0])

        api_gold_overlays: list[dict[str, Any]] = []
        for score, ov in scored:
            if len(api_gold_overlays) >= args.max_gold_per_api:
                break
            if score < args.score_threshold:
                break
            bound = ov.get("bound_object_types", [])
            if len(bound) > args.max_bound_objects:
                continue
            kind = ov.get("operation_kind", "")
            params = ov.get("parameter_bindings", [])
            path = ov.get("endpoint_binding", {}).get("path", "")
            segments = [s for s in path.split("/") if s]
            if len(segments) > 6:
                continue
            if kind in {"read", "update", "delete"} and not any(p.get("semantic_role") == "identifier" for p in params):
                continue

            promoted = json.loads(json.dumps(ov))
            promoted["review_status"] = "gold"
            promoted["review_note"] = (
                "Auto-promoted to gold: high-confidence REST pattern, "
                f"score={score:.1f}, bound_objects={bound}. "
                "Spot-check before treating as manually curated gold."
            )
            api_gold_overlays.append(promoted)

        if not api_gold_overlays:
            continue

        api_out = output_root / api_name
        api_out.mkdir(parents=True, exist_ok=True)

        used_object_ids = collect_bound_object_ids(api_gold_overlays)
        api_objects = {obj["id"]: _to_gold_object(obj) for obj in ontology["object_types"] if obj["id"] in used_object_ids}

        for obj_id, obj in api_objects.items():
            gold_objects[obj_id] = merge_object(gold_objects.get(obj_id), obj)

        gold_ontology = {
            "metadata": {
                "name": f"{api_name}_gold",
                "kind": "gold_object_ontology",
                "source_api": api_name,
                "review_status": "gold",
                "warning": "Auto-promoted gold labels. Not manually curated like the 3-pilot set.",
            },
            "object_types": sorted(api_objects.values(), key=lambda o: o["id"]),
        }
        with (api_out / "ontology.gold.json").open("w", encoding="utf-8") as f:
            json.dump(gold_ontology, f, ensure_ascii=False, indent=2)
            f.write("\n")

        with (api_out / "ontology_overlay.gold.jsonl").open("w", encoding="utf-8") as f:
            for row in api_gold_overlays:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                f.write("\n")

        api_gold_funcs = [overlay_to_gold(row) for row in api_gold_overlays]
        with (api_out / "gold_functions.gold.jsonl").open("w", encoding="utf-8") as f:
            for row in api_gold_funcs:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                f.write("\n")

        gold_overlays.extend(api_gold_overlays)
        gold_functions.extend(api_gold_funcs)
        print(f"{api_name}: promoted {len(api_gold_overlays)} to gold")

    # Aggregate
    agg_ontology = {
        "metadata": {
            "name": "apis_guru_gold_all",
            "kind": "gold_object_ontology",
            "review_status": "gold",
            "warning": "Auto-promoted gold labels across all APIs. Mixes rule-based silver promotions with any existing manual pilot golds.",
            "api_count": len(api_names),
            "overlay_count": len(gold_overlays),
        },
        "object_types": sorted(gold_objects.values(), key=lambda o: o["id"]),
    }
    with (output_root / "ontology.gold.json").open("w", encoding="utf-8") as f:
        json.dump(agg_ontology, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with (output_root / "ontology_overlay.gold.jsonl").open("w", encoding="utf-8") as f:
        for row in gold_overlays:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    with (output_root / "gold_functions.gold.jsonl").open("w", encoding="utf-8") as f:
        for row in gold_functions:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    summary = {
        "api_count": len(api_names),
        "gold_apis": len([d for d in output_root.iterdir() if d.is_dir() and (d / "ontology_overlay.gold.jsonl").exists()]),
        "gold_overlays": len(gold_overlays),
        "gold_object_types": len(gold_objects),
        "gold_functions": len(gold_functions),
        "output_root": str(output_root),
    }
    with (output_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _to_gold_object(obj: dict[str, Any]) -> dict[str, Any]:
    """Convert a reviewed object type to gold format."""
    gold = json.loads(json.dumps(obj))
    gold["review_status"] = "gold"
    return gold


def score_overlay(ov: dict[str, Any]) -> float:
    """Same scoring function used by auto_review_apis_guru_all.py."""
    score = 0.0
    kind = ov.get("operation_kind", "external")
    if kind in {"read", "create", "update"}:
        score += 3.0
    elif kind == "delete":
        score += 2.0
    else:
        score -= 2.0

    bound = ov.get("bound_object_types", [])
    if 1 <= len(bound) <= 3:
        score += 2.0
    elif len(bound) > 3:
        score -= 1.0
    else:
        score -= 1.5

    params = ov.get("parameter_bindings", [])
    if params:
        score += 1.0
    if any(p.get("semantic_role") == "identifier" for p in params):
        score += 1.0

    outputs = ov.get("output_bindings", [])
    if outputs:
        score += 1.0

    path = ov.get("endpoint_binding", {}).get("path", "")
    op_id = ov.get("endpoint_binding", {}).get("operation_id", "")
    op_id_lower = op_id.lower()

    noisy = {"api", "v1", "v2", "v3", "callback", "webhook", "event", "health", "ping", "openapi", "swagger"}
    if any(token in op_id_lower for token in noisy):
        score -= 1.5

    segments = [s for s in path.split("/") if s]
    if 1 <= len(segments) <= 5:
        score += 1.0
    if len(segments) > 6:
        score -= 1.0

    if re.search(r"^/[A-Za-z0-9_\-]+(\/\{[^}]+\})?(/[A-Za-z0-9_\-]+)?$", path):
        score += 1.0

    errors = ov.get("error_contract", [])
    if errors and any(e.startswith(("400", "404", "409")) for e in errors):
        score += 0.5

    return score


def merge_object(existing: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        return new
    existing_props = {p["id"]: p for p in existing.get("properties", [])}
    for p in new.get("properties", []):
        if p["id"] not in existing_props:
            existing.setdefault("properties", []).append(p)
            existing_props[p["id"]] = p
    existing["aliases"] = sorted(set(existing.get("aliases", [])) | set(new.get("aliases", [])))
    return existing


def collect_bound_object_ids(overlays: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for ov in overlays:
        ids.update(ov.get("bound_object_types", []))
        for p in ov.get("parameter_bindings", []):
            prop = p.get("ontology_property") or ""
            if "." in prop:
                ids.add(prop.split(".", 1)[0])
        for o in ov.get("output_bindings", []):
            prop = o.get("ontology_property") or ""
            if prop and "." not in prop:
                ids.add(prop)
            elif "." in prop:
                ids.add(prop.split(".", 1)[0])
    return ids


def overlay_to_gold(ov: dict[str, Any]) -> dict[str, Any]:
    return {
        "function_id": ov["candidate_function_id"],
        "endpoint_binding": ov["endpoint_binding"],
        "operation_kind": ov["operation_kind"],
        "description": ov.get("review_note", evidence_claim(ov)),
        "bound_object_types": ov["bound_object_types"],
        "inputs": [
            {
                "name": p["name"],
                "type": p["type"],
                "semantic_role": p["semantic_role"],
                "ontology_property": p.get("ontology_property"),
                "required": p["required"],
            }
            for p in ov.get("parameter_bindings", [])
        ],
        "outputs": [
            {
                "name": o["name"],
                "type": o["type"],
                "semantic_role": o.get("semantic_role", "target_object"),
                "ontology_property": o.get("ontology_property"),
                "required": False,
            }
            for o in ov.get("output_bindings", [])
        ],
        "preconditions": ov.get("preconditions", []),
        "effects": ov.get("effects", []),
        "error_contract": ov.get("error_contract", []),
        "evidence": ov.get("evidence", []),
    }


def evidence_claim(overlay: dict[str, Any]) -> str:
    evidence = overlay.get("evidence", [])
    if evidence and isinstance(evidence[0], dict):
        return str(evidence[0].get("claim", ""))
    return str(overlay.get("review_note", ""))


if __name__ == "__main__":
    main()
