#!/usr/bin/env python3
"""Aggregate per-API reviewed ontology/overlay/gold files into combined files.

Use this after manually editing per-API reviewed overlays, so the aggregate
files stay in sync without re-running auto-review heuristics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate per-API reviewed files.")
    parser.add_argument(
        "--sample-file",
        default="dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/selected_apis.json",
        help="JSON file with selected API names.",
    )
    parser.add_argument(
        "--input-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample",
        help="Root directory containing per-api reviewed folders.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Output directory for aggregated files. Defaults to input-root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_root = Path(args.input_root)
    output_root = Path(args.output_root) if args.output_root else input_root
    output_root.mkdir(parents=True, exist_ok=True)

    selected = json.load(Path(args.sample_file).open(encoding="utf-8"))
    apis = selected.get("apis", [])

    reviewed_overlays: list[dict[str, Any]] = []
    reviewed_objects: dict[str, dict[str, Any]] = {}
    gold_functions: list[dict[str, Any]] = []

    for api_name in apis:
        api_dir = input_root / api_name
        ontology_path = api_dir / "ontology.reviewed.json"
        overlay_path = api_dir / "ontology_overlay.reviewed.jsonl"
        gold_path = api_dir / "gold_functions.reviewed.jsonl"

        if not ontology_path.exists() or not overlay_path.exists() or not gold_path.exists():
            print(f"SKIP missing reviewed files for {api_name}")
            continue

        ontology = json.load(ontology_path.open(encoding="utf-8"))
        for obj in ontology.get("object_types", []):
            obj_id = obj["id"]
            if obj_id not in reviewed_objects:
                reviewed_objects[obj_id] = obj
            else:
                # Merge properties so injected properties from different APIs are preserved
                existing = reviewed_objects[obj_id]
                existing_props = {p["id"]: p for p in existing.get("properties", [])}
                for p in obj.get("properties", []):
                    if p["id"] not in existing_props:
                        existing.setdefault("properties", []).append(p)
                        existing_props[p["id"]] = p

        for line in overlay_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                reviewed_overlays.append(json.loads(line))

        for line in gold_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                gold_functions.append(json.loads(line))

    agg_ontology = {
        "metadata": {
            "name": "apis_guru_reviewed_sample",
            "kind": "reviewed_object_ontology",
            "warning": "Aggregated reviewed labels across sampled APIs.",
            "api_count": len(apis),
            "overlay_count": len(reviewed_overlays),
        },
        "object_types": sorted(reviewed_objects.values(), key=lambda o: o["id"]),
    }
    with (output_root / "ontology.reviewed.json").open("w", encoding="utf-8") as f:
        json.dump(agg_ontology, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with (output_root / "ontology_overlay.reviewed.jsonl").open("w", encoding="utf-8") as f:
        for row in reviewed_overlays:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    with (output_root / "gold_functions.reviewed.jsonl").open("w", encoding="utf-8") as f:
        for row in gold_functions:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    summary = {
        "apis": len(apis),
        "reviewed_overlays": len(reviewed_overlays),
        "reviewed_object_types": len(reviewed_objects),
        "gold_functions": len(gold_functions),
        "output_root": str(output_root),
    }
    with (output_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
