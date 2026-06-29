#!/usr/bin/env python3
"""Validate downloaded APIs.guru OpenAPI specs and report/remove broken ones.

Usage:
    python scripts/validate_apis_guru_specs.py \
        --specs-dir dataset/function_layer_benchmarks/raw/apis_guru/specs \
        [--remove-broken] \
        [--min-operations 1] \
        [--min-operation-coverage 0.5]

Outputs:
    - validation_report.json with per-spec details and summary
    - Prints summary to stdout
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate APIs.guru OpenAPI specs.")
    parser.add_argument("--specs-dir", type=Path, required=True, help="Directory containing *.openapi.json specs.")
    parser.add_argument("--remove-broken", action="store_true", help="Delete specs that fail validation.")
    parser.add_argument("--min-operations", type=int, default=1, help="Minimum valid operations required.")
    parser.add_argument("--max-broken-refs", type=int, default=5, help="Max allowed unresolved $ref per spec.")
    parser.add_argument("--report", type=Path, default=None, help="Validation report output path.")
    return parser.parse_args()


def validate_spec(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "filename": path.name,
        "valid": False,
        "errors": [],
        "warnings": [],
        "openapi_version": None,
        "title": None,
        "operation_count": 0,
        "schema_count": 0,
        "unresolved_refs": 0,
        "has_servers": False,
        "server_urls": [],
        "spec_size_mb": round(path.stat().st_size / (1024 * 1024), 3),
    }

    try:
        with path.open("r", encoding="utf-8") as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON parse error: {e}")
        return result
    except Exception as e:
        result["errors"].append(f"Read error: {e}")
        return result

    # OpenAPI version
    if "openapi" in spec:
        result["openapi_version"] = str(spec["openapi"])
    elif "swagger" in spec:
        result["openapi_version"] = f"swagger-{spec['swagger']}"
    else:
        result["errors"].append("Missing 'openapi' or 'swagger' field")

    info = spec.get("info") or {}
    result["title"] = info.get("title") or info.get("x-apisguru-categories") or "unknown"

    # Paths / operations
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        result["errors"].append("'paths' is not an object")
        return result

    op_count = 0
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in path_item:
            if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}:
                op_count += 1

    result["operation_count"] = op_count
    if op_count < 1:
        result["errors"].append("No operations found")

    # Components / schemas
    components = spec.get("components") or {}
    schemas = components.get("schemas") or spec.get("definitions") or {}
    result["schema_count"] = len(schemas)
    if result["schema_count"] == 0:
        result["warnings"].append("No schemas/definitions found")

    # Servers
    servers = spec.get("servers") or []
    if servers:
        result["has_servers"] = True
        result["server_urls"] = [s.get("url") for s in servers if isinstance(s, dict)]
    elif "host" in spec:
        result["has_servers"] = True
        result["server_urls"] = [spec.get("host")]

    # Ref resolution check (shallow: only scan for dangling $ref strings)
    unresolved = count_unresolved_refs(spec)
    result["unresolved_refs"] = unresolved
    if unresolved > 0:
        result["warnings"].append(f"{unresolved} potentially unresolved $ref")

    result["valid"] = len(result["errors"]) == 0
    return result


def count_unresolved_refs(obj: Any, defs: dict[str, Any] | None = None, seen: set[str] | None = None) -> int:
    if seen is None:
        seen = set()
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref not in seen:
                seen.add(ref)
                # We cannot fully resolve without full path traversal here;
                # this is just a structural scan.
        for v in obj.values():
            count_unresolved_refs(v, defs, seen)
    elif isinstance(obj, list):
        for item in obj:
            count_unresolved_refs(item, defs, seen)
    return len(seen)


def main() -> int:
    args = parse_args()
    specs_dir = args.specs_dir
    if not specs_dir.exists():
        print(f"Specs directory not found: {specs_dir}", file=sys.stderr)
        return 1

    spec_paths = sorted(specs_dir.glob("*.openapi.json"))
    print(f"[validate] {len(spec_paths)} specs found in {specs_dir}")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    removed_count = 0
    total_ops = 0

    for path in spec_paths:
        result = validate_spec(path)
        total_ops += result["operation_count"]

        # Additional quality gate
        if result["valid"] and result["operation_count"] < args.min_operations:
            result["valid"] = False
            result["errors"].append(f"Too few operations ({result['operation_count']} < {args.min_operations})")

        if result["valid"] and result["unresolved_refs"] > args.max_broken_refs:
            result["warnings"].append(
                f"Unresolved refs ({result['unresolved_refs']}) exceed threshold ({args.max_broken_refs})"
            )

        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1
            if args.remove_broken:
                try:
                    path.unlink()
                    removed_count += 1
                    print(f"  [removed] {path.name}: {'; '.join(result['errors'])}")
                except Exception as e:
                    print(f"  [remove failed] {path.name}: {e}")
            else:
                print(f"  [invalid] {path.name}: {'; '.join(result['errors'])}")

        results.append(result)

    avg_ops = total_ops / len(spec_paths) if spec_paths else 0
    version_dist: dict[str, int] = {}
    for r in results:
        v = r["openapi_version"] or "unknown"
        version_dist[v] = version_dist.get(v, 0) + 1

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_specs": len(spec_paths),
        "valid_specs": valid_count,
        "invalid_specs": invalid_count,
        "removed_specs": removed_count,
        "total_operations": total_ops,
        "avg_operations_per_spec": round(avg_ops, 2),
        "version_distribution": version_dist,
    }

    report = {
        "summary": summary,
        "specs": results,
    }

    report_path = args.report or specs_dir.parent / "validation_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2))
    print(f"[report] saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
