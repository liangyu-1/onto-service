#!/usr/bin/env python3
"""Batch-generate per-spec draft ontology and overlay for APIs.guru specs.

Outputs one directory per API under:
    dataset/function_layer_benchmarks/generated/apis_guru/<api_name>/

Files per API:
    ontology.draft.json
    ontology_overlay.draft.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from draft_object_ontology import OntologyDraftBuilder, iter_openapi_specs
from draft_ontology_overlay import build_object_index, build_property_index, draft_overlay, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch draft ontology/overlay for APIs.guru specs.")
    parser.add_argument(
        "--specs",
        default="dataset/function_layer_benchmarks/raw/apis_guru/specs",
        help="Directory containing *.openapi.json specs.",
    )
    parser.add_argument(
        "--output",
        default="dataset/function_layer_benchmarks/generated/apis_guru",
        help="Root output directory.",
    )
    parser.add_argument(
        "--max-specs",
        type=int,
        default=0,
        help="If >0, only process the first N specs (useful for testing).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip specs that already have ontology.draft.json.",
    )
    return parser.parse_args()


def api_name_from_path(path: Path) -> str:
    return path.stem.replace(".openapi", "")


def main() -> None:
    args = parse_args()
    specs_dir = Path(args.specs)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    specs = list(iter_openapi_specs(specs_dir))
    if args.max_specs > 0:
        specs = specs[: args.max_specs]

    summary = {
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "api_summaries": [],
    }

    total = len(specs)
    print(f"Processing {total} specs from {specs_dir}")

    for i, (source_id, spec) in enumerate(specs, 1):
        source_path = Path(source_id)
        api_name = api_name_from_path(source_path)
        api_dir = output_root / api_name
        ontology_path = api_dir / "ontology.draft.json"
        overlay_path = api_dir / "ontology_overlay.draft.jsonl"

        if args.skip_existing and ontology_path.exists():
            summary["skipped"] += 1
            if i % 100 == 0:
                print(f"[{i}/{total}] skipped {api_name}")
            continue

        api_dir.mkdir(parents=True, exist_ok=True)
        start = time.time()

        try:
            builder = OntologyDraftBuilder(name=f"{api_name}_ontology_draft")
            builder.add_openapi(api_name, spec)
            ontology = builder.to_dict()
            with ontology_path.open("w", encoding="utf-8") as f:
                json.dump(ontology, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")

            object_index = build_object_index(ontology)
            property_index = build_property_index(ontology)
            overlays = []
            for path, method, operation in iter_operations(spec):
                overlays.append(
                    draft_overlay(source_path.name, spec, path, method, operation, object_index, property_index)
                )
            with overlay_path.open("w", encoding="utf-8") as f:
                for row in overlays:
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                    f.write("\n")

            elapsed = time.time() - start
            summary["processed"] += 1
            summary["api_summaries"].append(
                {
                    "api": api_name,
                    "objects": len(ontology["object_types"]),
                    "relations": len(ontology["relations"]),
                    "overlays": len(overlays),
                    "elapsed_sec": round(elapsed, 2),
                }
            )
            if i % 50 == 0 or i <= 5:
                print(
                    f"[{i}/{total}] {api_name}: {len(ontology['object_types'])} objects, "
                    f"{len(overlays)} overlays ({elapsed:.2f}s)"
                )
        except Exception as e:
            summary["errors"] += 1
            print(f"[{i}/{total}] ERROR {api_name}: {e}")

    summary_path = output_root / "batch_draft_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        json.dumps(
            {
                "processed": summary["processed"],
                "skipped": summary["skipped"],
                "errors": summary["errors"],
                "summary_path": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def iter_operations(openapi: dict[str, Any]):
    http_methods = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
    for path, path_item in (openapi.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() in http_methods and isinstance(operation, dict):
                yield str(path), method.lower(), operation


if __name__ == "__main__":
    main()
