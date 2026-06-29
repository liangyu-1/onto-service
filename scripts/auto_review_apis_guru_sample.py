#!/usr/bin/env python3
"""Semi-automatically review a diverse sample of APIs.guru draft overlays.

Produces reviewed benchmark files:
    ontology.reviewed.json
    ontology_overlay.reviewed.jsonl
    gold_functions.reviewed.jsonl

Review is rule-based; output should be treated as "silver" labels and spot-checked
before being reported as gold.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-review a sample of APIs.guru overlays.")
    parser.add_argument(
        "--draft-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru",
        help="Root directory containing per-api draft folders.",
    )
    parser.add_argument(
        "--sample-file",
        default=None,
        help="Optional JSON list of api names to include. If omitted, uses internal sampling.",
    )
    parser.add_argument(
        "--max-overlays-per-api",
        type=int,
        default=20,
        help="Maximum reviewed overlays per API.",
    )
    parser.add_argument(
        "--output-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample",
        help="Output directory for aggregated reviewed files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    draft_root = Path(args.draft_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    if args.sample_file:
        selected_apis = json.load(Path(args.sample_file).open())["apis"]
    else:
        selected_apis = select_diverse_sample(draft_root, target_total=50)
        sample_path = output_root / "selected_apis.json"
        with sample_path.open("w", encoding="utf-8") as f:
            json.dump({"apis": selected_apis, "count": len(selected_apis)}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Selected {len(selected_apis)} APIs -> {sample_path}")

    reviewed_overlays: list[dict[str, Any]] = []
    reviewed_objects: dict[str, dict[str, Any]] = {}
    gold_functions: list[dict[str, Any]] = []

    for api_name in selected_apis:
        api_dir = draft_root / api_name
        ontology_path = api_dir / "ontology.draft.json"
        overlay_path = api_dir / "ontology_overlay.draft.jsonl"
        if not ontology_path.exists() or not overlay_path.exists():
            print(f"SKIP missing draft for {api_name}")
            continue

        ontology = json.load(ontology_path.open(encoding="utf-8"))
        overlays = [json.loads(line) for line in overlay_path.open(encoding="utf-8") if line.strip()]

        scored = [(score_overlay(ov), ov) for ov in overlays]
        scored.sort(key=lambda x: -x[0])

        api_reviewed: list[dict[str, Any]] = []
        for score, ov in scored:
            if len(api_reviewed) >= args.max_overlays_per_api:
                break
            reviewed = apply_auto_review(ov, score)
            if reviewed["review_status"] == "reviewed":
                api_reviewed.append(reviewed)

        # Write per-api reviewed files
        api_out = output_root / api_name
        api_out.mkdir(parents=True, exist_ok=True)

        used_object_ids = collect_bound_object_ids(api_reviewed)
        api_objects = {obj["id"]: obj for obj in ontology["object_types"] if obj["id"] in used_object_ids}

        # Inject inferred properties referenced by overlays but missing from draft ontology
        inject_missing_properties(api_objects, api_reviewed)

        for obj_id, obj in api_objects.items():
            reviewed_objects[obj_id] = merge_object(reviewed_objects.get(obj_id), obj)

        reviewed_ontology = {
            "metadata": {
                "name": f"{api_name}_reviewed",
                "kind": "reviewed_object_ontology",
                "warning": "Auto-reviewed silver labels. Spot-check before use as gold.",
                "source_api": api_name,
            },
            "object_types": sorted(api_objects.values(), key=lambda o: o["id"]),
        }
        with (api_out / "ontology.reviewed.json").open("w", encoding="utf-8") as f:
            json.dump(reviewed_ontology, f, ensure_ascii=False, indent=2)
            f.write("\n")

        with (api_out / "ontology_overlay.reviewed.jsonl").open("w", encoding="utf-8") as f:
            for row in api_reviewed:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                f.write("\n")

        api_gold = [overlay_to_gold(row) for row in api_reviewed]
        with (api_out / "gold_functions.reviewed.jsonl").open("w", encoding="utf-8") as f:
            for row in api_gold:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                f.write("\n")

        reviewed_overlays.extend(api_reviewed)
        gold_functions.extend(api_gold)
        print(f"{api_name}: reviewed {len(api_reviewed)} overlays")

    # Aggregated files
    agg_ontology = {
        "metadata": {
            "name": "apis_guru_reviewed_sample",
            "kind": "reviewed_object_ontology",
            "warning": "Aggregated silver labels across sampled APIs. Spot-check before use as gold.",
            "api_count": len(selected_apis),
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
        "selected_apis": len(selected_apis),
        "reviewed_overlays": len(reviewed_overlays),
        "reviewed_object_types": len(reviewed_objects),
        "gold_functions": len(gold_functions),
        "output_root": str(output_root),
    }
    with (output_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def select_diverse_sample(draft_root: Path, target_total: int) -> list[str]:
    """Select a diverse sample across size tiers, deduplicating multi-version APIs."""
    summary = json.load((draft_root / "batch_draft_summary.json").open(encoding="utf-8"))
    items = summary["api_summaries"]

    # Deduplicate by base name, keep the one with most overlays
    groups: dict[str, dict[str, Any]] = {}
    for it in items:
        name = it["api"]
        base = name.split("_")[0] if "_" in name else name
        base = re.sub(r"\.(com|net|org|io|gov|edu|dev|local|ai|app|co\.\w+)$", "", base)
        if base not in groups or it["overlays"] > groups[base]["overlays"]:
            groups[base] = it

    unique = list(groups.values())

    # Filter out APIs with too few or too many overlays
    candidates = [it for it in unique if 5 <= it["overlays"] <= 500 and 3 <= it["objects"] <= 400]

    # Tiers by overlay count
    def tier(it: dict[str, Any]) -> str:
        o = it["overlays"]
        if o <= 15:
            return "small"
        if o <= 40:
            return "medium"
        if o <= 120:
            return "large"
        return "xlarge"

    tiers = {"small": [], "medium": [], "large": [], "xlarge": []}
    for it in candidates:
        tiers[tier(it)].append(it)

    # Pick evenly across tiers
    per_tier = target_total // len(tiers)
    selected: list[str] = []
    for tname, titems in tiers.items():
        titems.sort(key=lambda x: -x["overlays"])
        picked = titems[:per_tier]
        selected.extend([it["api"] for it in picked])

    # Fill remaining slots with highest-overlay APIs not yet selected
    remaining = [it for it in candidates if it["api"] not in set(selected)]
    remaining.sort(key=lambda x: -x["overlays"])
    selected.extend([it["api"] for it in remaining[: target_total - len(selected)]])

    return sorted(selected)


def score_overlay(ov: dict[str, Any]) -> float:
    """Higher score = more likely to be a clean, reviewable function."""
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

    # Penalize generic / noisy operationIds
    noisy = {"api", "v1", "v2", "v3", "callback", "webhook", "event", "health", "ping", "openapi", "swagger"}
    if any(token in op_id_lower for token in noisy):
        score -= 1.5

    # Prefer clean REST paths
    segments = [s for s in path.split("/") if s]
    if 1 <= len(segments) <= 5:
        score += 1.0
    if len(segments) > 6:
        score -= 1.0

    # Prefer paths with identifiable resource pattern
    if re.search(r"^/[A-Za-z0-9_\-]+(\/\{[^}]+\})?(/[A-Za-z0-9_\-]+)?$", path):
        score += 1.0

    errors = ov.get("error_contract", [])
    if errors and any(e.startswith(("400", "404", "409")) for e in errors):
        score += 0.5

    return score


def apply_auto_review(ov: dict[str, Any], score: float) -> dict[str, Any]:
    """Promote high-confidence drafts to reviewed status; otherwise keep draft."""
    reviewed = json.loads(json.dumps(ov))  # deep copy
    kind = reviewed.get("operation_kind", "external")
    bound = reviewed.get("bound_object_types", [])
    params = reviewed.get("parameter_bindings", [])
    outputs = reviewed.get("output_bindings", [])
    path = reviewed.get("endpoint_binding", {}).get("path", "")

    # Clean bound objects: keep only those supported by path or params/outputs
    reviewed["bound_object_types"] = clean_bound_objects(bound, path, params, outputs)
    bound = reviewed["bound_object_types"]

    # Fix obvious identifier/output semantics
    reviewed["parameter_bindings"] = fix_identifier_semantics(params, bound)
    reviewed["output_bindings"] = fix_output_semantics(outputs, bound)

    confidence_checks = [
        kind in {"read", "create", "update", "delete"},
        1 <= len(bound) <= 3,
        len(params) >= 1,
        outputs or kind == "delete",
        score >= 2.0,
        len(path.split("/")) <= 7,
    ]

    if all(confidence_checks):
        reviewed["review_status"] = "reviewed"
        reviewed["review_note"] = (
            "Auto-reviewed: clear REST pattern, bound object types, "
            "and identifiable parameters/outputs. Spot-check before use as gold."
        )
        # Add heuristic preconditions/effects
        reviewed["preconditions"] = infer_preconditions(reviewed)
        reviewed["effects"] = infer_effects(reviewed)
    else:
        reviewed["review_status"] = "draft"
        reviewed["review_note"] = "Below auto-review confidence threshold; needs manual review."

    return reviewed


def clean_bound_objects(
    bound_objects: list[str], path: str, params: list[dict[str, Any]], outputs: list[dict[str, Any]]
) -> list[str]:
    """Remove bound object types not supported by path segments, params, or bindings."""
    if not bound_objects:
        return bound_objects

    path_segments = {normalize_name(singularize(s.strip("{}"))) for s in path.split("/") if s and not s.startswith("{")}
    id_hints = {object_hint_from_param(p["name"]) for p in params if p.get("semantic_role") == "identifier" or p.get("location") == "path"}
    output_hints = {normalize_name(o.get("name", "")) for o in outputs}
    output_object_refs = {normalize_name(o.get("ontology_property", "")) for o in outputs if o.get("ontology_property")}
    param_object_refs = set()
    for p in params:
        prop = p.get("ontology_property")
        if not prop:
            continue
        if "." not in prop:
            param_object_refs.add(normalize_name(prop))
        else:
            param_object_refs.add(normalize_name(prop.split(".", 1)[0]))

    kept = []
    for obj in bound_objects:
        norm = normalize_name(obj)
        checks = [path_segments, id_hints, output_hints, output_object_refs, param_object_refs]
        if any(norm in group for group in checks):
            kept.append(obj)
            continue
        # Also accept if object is a substring of a path segment (e.g. "Item" in "items")
        for seg in path_segments:
            if norm in seg or seg in norm:
                kept.append(obj)
                break

    # Fallback: if nothing kept, keep original to avoid empty
    return kept if kept else bound_objects[:3]


def fix_identifier_semantics(params: list[dict[str, Any]], bound_objects: list[str]) -> list[dict[str, Any]]:
    """Heuristic: path params named {Object}Uuid/Id/Key are identifiers."""
    fixed = []
    bound_norms = {normalize_name(obj): obj for obj in bound_objects}
    for p in params:
        name = p.get("name", "")
        norm = normalize_name(name)
        # Check suffix patterns
        suffix_match = None
        for suffix in ("uuid", "id", "key", "identifier", "name"):
            if norm.endswith(suffix):
                prefix = norm[: -len(suffix)]
                if prefix in bound_norms:
                    suffix_match = bound_norms[prefix]
                    break
        if suffix_match and p.get("location") == "path":
            p = {**p, "semantic_role": "identifier"}
            if not p.get("ontology_property"):
                p["ontology_property"] = f"{suffix_match}.{name}"
        fixed.append(p)
    return fixed


def fix_output_semantics(outputs: list[dict[str, Any]], bound_objects: list[str]) -> list[dict[str, Any]]:
    """Heuristic: if output name resembles a bound object type, link it."""
    if not outputs or not bound_objects:
        return outputs
    fixed = []
    bound_norms = {normalize_name(obj): obj for obj in bound_objects}
    for o in outputs:
        name = o.get("name", "")
        norm = normalize_name(name)
        # Strip common wrappers (underscores already removed by normalize_name)
        for prefix in ("full", "created", "updated", "deleted", "listof", "arrayof"):
            if norm.startswith(prefix):
                norm = norm[len(prefix):]
                break
        if norm.endswith("s") and len(norm) > 3:
            norm = norm[:-1]
        if not o.get("ontology_property") and norm in bound_norms:
            o = {**o, "ontology_property": bound_norms[norm]}
        fixed.append(o)
    return fixed


def inject_missing_properties(
    api_objects: dict[str, dict[str, Any]], overlays: list[dict[str, Any]]
) -> None:
    """Ensure every ontology_property referenced by an overlay exists in the ontology."""
    for ov in overlays:
        for group in ("parameter_bindings", "output_bindings"):
            for binding in ov.get(group, []):
                prop = binding.get("ontology_property")
                if not prop or "." not in prop:
                    continue
                object_id, prop_name = prop.split(".", 1)
                obj = api_objects.get(object_id)
                if not obj:
                    continue
                existing = {p["id"] for p in obj.get("properties", [])}
                if prop_name not in existing:
                    obj.setdefault("properties", []).append(
                        {
                            "id": prop_name,
                            "type": binding.get("type", "string"),
                            "aliases": [prop_name],
                            "required": binding.get("required", False),
                            "evidence": [
                                {
                                    "source_type": "inferred_from_overlay",
                                    "source_reference": ov.get("overlay_id", ""),
                                    "claim": f"Inferred property {prop_name} from binding",
                                }
                            ],
                        }
                    )


def merge_object(existing: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    """Merge two object type definitions, keeping all distinct properties."""
    if not existing:
        return new
    existing_props = {p["id"]: p for p in existing.get("properties", [])}
    for p in new.get("properties", []):
        if p["id"] not in existing_props:
            existing.setdefault("properties", []).append(p)
            existing_props[p["id"]] = p
    # Merge aliases
    existing["aliases"] = sorted(set(existing.get("aliases", [])) | set(new.get("aliases", [])))
    # Keep review_status as draft if either is draft
    if existing.get("review_status") == "reviewed" and new.get("review_status") != "reviewed":
        existing["review_status"] = new.get("review_status", "draft")
    return existing


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def infer_preconditions(ov: dict[str, Any]) -> list[str]:
    """Infer simple state preconditions from operation kind and parameters."""
    kind = ov.get("operation_kind", "")
    bound = ov.get("bound_object_types", [])
    params = ov.get("parameter_bindings", [])
    path = ov.get("endpoint_binding", {}).get("path", "")
    pre: list[str] = []
    if kind in {"read", "update", "delete"} and bound:
        id_params = [p for p in params if p.get("semantic_role") == "identifier"]
        if id_params:
            # Prefer object matching the last path segment's identifier
            primary_obj = pick_primary_object(bound, path, id_params[-1]["name"])
            for p in id_params:
                hint = object_hint_from_param(p["name"])
                obj = next((b for b in bound if normalize_name(b) == hint), primary_obj)
                pre.append(f"{obj}.id == {p['name']}")
                pre.append(f"{obj} exists")
    return pre


def pick_primary_object(bound_objects: list[str], path: str, last_id_param: str) -> str:
    """Pick the most likely primary object for the operation."""
    # Try matching last_id_param prefix to a bound object
    hint = object_hint_from_param(last_id_param)
    for obj in bound_objects:
        if normalize_name(obj) == hint:
            return obj
    # Try matching last non-parameter path segment
    segments = [s.strip("{}") for s in path.split("/") if s and not s.startswith("{")]
    if segments:
        last_seg = normalize_name(singularize(segments[-1]))
        for obj in bound_objects:
            if normalize_name(obj) == last_seg:
                return obj
    return bound_objects[0]


def object_hint_from_param(param_name: str) -> str:
    norm = normalize_name(param_name)
    for suffix in ("uuid", "id", "key", "identifier"):
        if norm.endswith(suffix):
            return norm[: -len(suffix)]
    return norm


def singularize(text: str) -> str:
    if text.endswith("ies") and len(text) > 3:
        return text[:-3] + "y"
    if text.endswith("ses"):
        return text[:-2]
    if text.endswith("s") and not text.endswith("ss") and len(text) > 3:
        return text[:-1]
    return text


def infer_effects(ov: dict[str, Any]) -> list[str]:
    """Infer simple state effects from operation kind."""
    kind = ov.get("operation_kind", "")
    bound = ov.get("bound_object_types", [])
    if not bound:
        return []
    obj = bound[0]
    if kind == "create":
        return [f"{obj} created"]
    if kind == "update":
        return [f"{obj} updated"]
    if kind == "delete":
        return [f"{obj} deleted"]
    return []


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
        "description": ov["evidence"][0].get("claim", "") if ov.get("evidence") else "",
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
                "semantic_role": "target_object",
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


if __name__ == "__main__":
    main()
