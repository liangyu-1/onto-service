#!/usr/bin/env python3
"""Auto-review all APIs.guru draft overlays.

Produces reviewed (silver) benchmark files for every API that has a complete
draft ontology + overlay pair:

    dataset/function_layer_benchmarks/generated/apis_guru/reviewed_all/<api>/
    ├── ontology.reviewed.json
    ├── ontology_overlay.reviewed.jsonl
    └── gold_functions.reviewed.jsonl

And aggregate files under reviewed_all/.

Review is rule-based and should be treated as silver labels.  Spots that need
manual curation are marked review_status="draft" and kept alongside the
reviewed rows so users can finish them later.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-review all APIs.guru overlays.")
    parser.add_argument(
        "--draft-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru",
        help="Root directory containing per-api draft folders.",
    )
    parser.add_argument(
        "--output-root",
        default="dataset/function_layer_benchmarks/generated/apis_guru/reviewed_all",
        help="Output directory for aggregated reviewed files.",
    )
    parser.add_argument(
        "--max-overlays-per-api",
        type=int,
        default=20,
        help="Maximum reviewed overlays per API.",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=2.0,
        help="Minimum score for an overlay to be promoted to reviewed.",
    )
    parser.add_argument(
        "--max-apis",
        type=int,
        default=0,
        help="If >0, only process the first N APIs (useful for testing).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    draft_root = Path(args.draft_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    api_names = sorted(_api_names_with_drafts(draft_root))
    if args.max_apis > 0:
        api_names = api_names[: args.max_apis]

    reviewed_overlays: list[dict[str, Any]] = []
    reviewed_objects: dict[str, dict[str, Any]] = {}
    gold_functions: list[dict[str, Any]] = []

    for api_name in api_names:
        api_dir = draft_root / api_name
        ontology_path = api_dir / "ontology.draft.json"
        overlay_path = api_dir / "ontology_overlay.draft.jsonl"

        ontology = json.load(ontology_path.open(encoding="utf-8"))
        overlays = [json.loads(line) for line in overlay_path.open(encoding="utf-8") if line.strip()]

        scored = [(score_overlay(ov), ov) for ov in overlays]
        scored.sort(key=lambda x: -x[0])

        api_reviewed: list[dict[str, Any]] = []
        for score, ov in scored:
            if len(api_reviewed) >= args.max_overlays_per_api:
                break
            reviewed = apply_auto_review(ov, score, args.score_threshold)
            api_reviewed.append(reviewed)

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
        reviewed_count = sum(1 for r in api_reviewed if r["review_status"] == "reviewed")
        print(f"{api_name}: {reviewed_count}/{len(api_reviewed)} reviewed")

    # Aggregated files
    agg_ontology = {
        "metadata": {
            "name": "apis_guru_reviewed_all",
            "kind": "reviewed_object_ontology",
            "warning": "Aggregated silver labels across all APIs. Spot-check before use as gold.",
            "api_count": len(api_names),
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
        "api_count": len(api_names),
        "reviewed_apis": len(api_names),
        "reviewed_overlays": len(reviewed_overlays),
        "reviewed_object_types": len(reviewed_objects),
        "gold_functions": len(gold_functions),
        "output_root": str(output_root),
    }
    with (output_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _api_names_with_drafts(draft_root: Path) -> list[str]:
    """Return API directory names that have both draft ontology and overlay."""
    names: list[str] = []
    for entry in sorted(draft_root.iterdir()):
        if not entry.is_dir():
            continue
        # Skip aggregate output directories
        if entry.name in {"gold", "reviewed_sample", "reviewed_all"}:
            continue
        if (entry / "ontology.draft.json").exists() and (entry / "ontology_overlay.draft.jsonl").exists():
            names.append(entry.name)
    return names


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


def apply_auto_review(ov: dict[str, Any], score: float, score_threshold: float) -> dict[str, Any]:
    """Promote high-confidence drafts to reviewed status; otherwise keep draft."""
    reviewed = json.loads(json.dumps(ov))  # deep copy
    kind = reviewed.get("operation_kind", "external")
    path = reviewed.get("endpoint_binding", {}).get("path", "")

    # Clean bound objects first so downstream helpers can use them
    bound = reviewed.get("bound_object_types", [])
    params = reviewed.get("parameter_bindings", [])
    outputs = reviewed.get("output_bindings", [])
    reviewed["bound_object_types"] = clean_bound_objects(bound, path, params, outputs)
    bound = reviewed["bound_object_types"]

    # Fix semantics using the cleaned bound objects
    reviewed["parameter_bindings"] = fix_parameter_semantics(params, bound, path, kind)
    reviewed["output_bindings"] = fix_output_semantics(outputs, bound)

    confidence_checks = [
        kind in {"read", "create", "update", "delete"},
        1 <= len(bound) <= 3,
        len(params) >= 1,
        outputs or kind == "delete",
        score >= score_threshold,
        len(path.split("/")) <= 7,
    ]

    if all(confidence_checks):
        reviewed["review_status"] = "reviewed"
        reviewed["review_note"] = (
            "Auto-reviewed: clear REST pattern, bound object types, "
            "and identifiable parameters/outputs. Spot-check before use as gold."
        )
        reviewed["preconditions"] = infer_preconditions(reviewed)
        reviewed["effects"] = infer_effects(reviewed)
    else:
        reviewed["review_status"] = "draft"
        reviewed["review_note"] = "Below auto-review confidence threshold; needs manual review."
        reviewed.setdefault("preconditions", [])
        reviewed.setdefault("effects", [])

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
        for seg in path_segments:
            if norm in seg or seg in norm:
                kept.append(obj)
                break

    return kept if kept else bound_objects[:3]


def fix_parameter_semantics(params: list[dict[str, Any]], bound_objects: list[str], path: str, kind: str) -> list[dict[str, Any]]:
    """Set semantic_role and ontology_property for parameters."""
    fixed = []
    bound_norms = {normalize_name(obj): obj for obj in bound_objects}
    primary_obj = bound_objects[0] if bound_objects else None

    for p in params:
        name = p.get("name", "")
        norm = normalize_name(name)
        location = p.get("location", "")
        prop = p.get("ontology_property")

        # Identifier: path params named {Object}Uuid/Id/Key/Identifier/Name
        if location == "path":
            id_obj = _resolve_identifier_object(name, bound_objects, path)
            if id_obj:
                p = {**p, "semantic_role": "identifier", "ontology_property": f"{id_obj}.id"}
            else:
                p = {**p, "semantic_role": "identifier"}
            fixed.append(p)
            continue

        # Request body is payload
        if location == "requestBody":
            p = {**p, "semantic_role": "payload"}
            if not prop and primary_obj:
                p["ontology_property"] = _collapse_wrapper_type(p.get("type", ""), name, bound_objects)
            fixed.append(p)
            continue

        # Query / header parameters
        semantic = _infer_query_semantic(name, p.get("type", ""))
        p = {**p, "semantic_role": semantic}
        if not prop and semantic == "identifier" and bound_norms:
            # e.g. query param named userId
            id_obj = _resolve_identifier_object(name, bound_objects, path)
            if id_obj:
                p["ontology_property"] = f"{id_obj}.id"
        fixed.append(p)

    return fixed


def fix_output_semantics(outputs: list[dict[str, Any]], bound_objects: list[str]) -> list[dict[str, Any]]:
    """Map output bindings to core bound object types where possible."""
    if not outputs or not bound_objects:
        return outputs
    fixed = []
    bound_norms = {normalize_name(obj): obj for obj in bound_objects}
    for o in outputs:
        name = o.get("name", "")
        otype = o.get("type", "")
        norm = normalize_name(name)
        for prefix in ("full", "created", "updated", "deleted", "listof", "arrayof"):
            if norm.startswith(prefix):
                norm = norm[len(prefix):]
                break
        if norm.endswith("s") and len(norm) > 3:
            norm = norm[:-1]

        if not o.get("ontology_property"):
            if norm in bound_norms:
                o = {**o, "ontology_property": bound_norms[norm]}
            elif otype == "array":
                # Try to infer array item type from name
                item_type = _collapse_wrapper_type(otype, name, bound_objects)
                if item_type:
                    o = {**o, "ontology_property": item_type}
            elif len(bound_objects) == 1:
                o = {**o, "ontology_property": bound_objects[0]}

        if "semantic_role" not in o:
            o = {**o, "semantic_role": "target_object"}
        fixed.append(o)
    return fixed


def _resolve_identifier_object(param_name: str, bound_objects: list[str], path: str) -> str | None:
    """Find the object type that a path identifier parameter refers to."""
    if not bound_objects:
        return None
    norm = normalize_name(param_name)
    bound_norms = {normalize_name(obj): obj for obj in bound_objects}

    # Prefix match: vaultUuid -> Vault
    for suffix in ("uuid", "id", "key", "identifier", "name"):
        if norm.endswith(suffix):
            prefix = norm[: -len(suffix)]
            if prefix in bound_norms:
                return bound_norms[prefix]

    # Last path segment singularized
    segments = [s.strip("{}") for s in path.split("/") if s and not s.startswith("{")]
    if segments:
        last_seg = normalize_name(singularize(segments[-1]))
        if last_seg in bound_norms:
            return bound_norms[last_seg]

    return bound_objects[0]


def _collapse_wrapper_type(otype: str, name: str, bound_objects: list[str]) -> str | None:
    """Map wrapper type names like FullItem, CreateItem to the core Item object."""
    if not bound_objects:
        return None
    bound_norms = {normalize_name(obj): obj for obj in bound_objects}
    norm = normalize_name(name)

    # Direct match
    if norm in bound_norms:
        return bound_norms[norm]

    # Strip wrappers
    for prefix in ("full", "create", "update", "patch", "new", "body", "request", "response", "listof", "arrayof"):
        if norm.startswith(prefix):
            norm = norm[len(prefix):]
            break
    if norm.endswith("s") and len(norm) > 3:
        norm = norm[:-1]
    if norm in bound_norms:
        return bound_norms[norm]

    # Array with single object type: default to the primary object
    if otype == "array" and len(bound_objects) == 1:
        return bound_objects[0]

    return bound_objects[0] if len(bound_objects) == 1 else None


def _infer_query_semantic(name: str, ptype: str) -> str:
    """Infer semantic role for query/header parameters."""
    norm = normalize_name(name)
    if norm in {"filter", "q", "query", "search", "keyword", "keywords"}:
        return "filter"
    if any(t in norm for t in ("status", "state", "active", "enabled", "disabled", "published", "archived")):
        return "state"
    if any(t in norm for t in ("at", "date", "time", "from", "to", "since", "until", "created", "updated")):
        return "time"
    if any(t in norm for t in ("count", "limit", "offset", "page", "size", "total", "max", "min")):
        return "measure"
    return "payload"


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
    existing["aliases"] = sorted(set(existing.get("aliases", [])) | set(new.get("aliases", [])))
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
            primary_obj = pick_primary_object(bound, path, id_params[-1]["name"])
            for p in id_params:
                hint = object_hint_from_param(p["name"])
                obj = next((b for b in bound if normalize_name(b) == hint), primary_obj)
                prop = p.get("ontology_property") or f"{obj}.id"
                pre.append(f"{prop} == {p['name']}")
                pre.append(f"{obj} exists")
    return pre


def pick_primary_object(bound_objects: list[str], path: str, last_id_param: str) -> str:
    """Pick the most likely primary object for the operation."""
    hint = object_hint_from_param(last_id_param)
    for obj in bound_objects:
        if normalize_name(obj) == hint:
            return obj
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
    bound = ov.get("bound_objects", ov.get("bound_object_types", []))
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
