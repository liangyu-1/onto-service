#!/usr/bin/env python3
"""Preflight checks for official tau2 paired experiments.

These checks are deliberately conservative: they verify the local experiment
artifacts and the minimum runtime dependencies before starting expensive tau2
simulations. They do not replace official reward validation after the run.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank  # noqa: E402


ACTION_BANK_PATH = BASE_DIR / "data/action_bank/retail_action_bank.json"
ACTION_IR_PATH = BASE_DIR / "data/action_ir/retail_action_ir.json"


def ok(message: str) -> Dict[str, Any]:
    return {"ok": True, "message": message}


def fail(message: str) -> Dict[str, Any]:
    return {"ok": False, "message": message}


def check_action_bank(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return fail(f"ActionBank file not found: {path}")
    try:
        action_bank = ActionBank.from_json(path)
    except Exception as exc:
        return fail(f"ActionBank failed to parse: {exc}")
    actions = action_bank.list_actions()
    if not actions:
        return fail("ActionBank contains no actions")
    required = {
        "find_user_id_by_email",
        "find_user_id_by_name_zip",
        "get_user_details",
        "get_order_details",
        "transfer_to_human_agents",
    }
    missing = sorted(required - set(actions))
    if missing:
        return fail(f"ActionBank is missing required retail actions: {missing}")
    return ok(f"ActionBank loaded with {len(actions)} actions")


def action_bank_snapshot(action_bank: ActionBank) -> Dict[str, Any]:
    return {
        "actions": [
            {
                "action_id": schema.action_id,
                "description": schema.description,
                "parameters": schema.parameters,
                "preconditions": schema.preconditions,
                "effects": schema.effects,
                "constraints": schema.constraints,
                "target_object": schema.target_object,
                "action_kind": schema.action_kind,
                "grounding_mode": schema.grounding_mode,
                "parameter_semantics": schema.parameter_semantics,
                "target_binding": schema.target_binding,
                "ontology_action_id": schema.ontology_action_id,
                "target_type_id": schema.target_type_id,
                "control_flow": schema.control_flow,
            }
            for schema in sorted(action_bank.schemas.values(), key=lambda item: item.action_id)
        ],
        "predicate_providers": action_bank.predicate_providers,
    }


def check_action_ir_projection(action_ir_path: pathlib.Path, action_bank_path: pathlib.Path) -> Dict[str, Any]:
    if not action_ir_path.exists():
        return fail(f"Action IR file not found: {action_ir_path}")
    try:
        projected = ActionBank.from_action_ir_json(action_ir_path)
        committed = ActionBank.from_json(action_bank_path)
    except Exception as exc:
        return fail(f"Action IR projection failed: {exc}")
    if action_bank_snapshot(projected) != action_bank_snapshot(committed):
        return fail(
            "ActionBank is not the deterministic projection of the canonical Action IR. "
            "Run compile_action_ir_to_action_bank.py and inspect the diff."
        )
    return ok(f"Action IR projects to ActionBank with {len(projected.list_actions())} actions")


def check_agent_module() -> Dict[str, Any]:
    try:
        module = importlib.import_module("tau2_ontology_agent")
    except Exception as exc:
        return fail(f"tau2_ontology_agent import failed: {exc}")
    missing = []
    for name in (
        "create_schema_baseline_agent",
        "create_ontology_prompt_agent",
        "create_state_only_agent",
        "create_ontology_lite_agent",
        "create_typed_admissibility_agent",
        "create_ontology_guided_agent",
        "build_agent_class",
    ):
        if not hasattr(module, name):
            missing.append(name)
    if missing:
        return fail(f"tau2_ontology_agent is missing factories: {missing}")
    return ok("tau2_ontology_agent imports and exposes all factories")


def check_tau2_import() -> Dict[str, Any]:
    missing = []
    for module_name in (
        "tau2",
        "tau2.agent.base_agent",
        "tau2.data_model.message",
        "tau2.data_model.simulation",
        "tau2.registry",
        "tau2.runner",
    ):
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            missing.append(f"{module_name}: {exc}")
    if missing:
        return fail("tau2 runtime import failed: " + "; ".join(missing))
    return ok("tau2 runtime imports succeeded")


def check_model_endpoint(base_url: str, model: str, api_key: str, timeout: float) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return fail(f"model endpoint check failed for {url}: {exc}")
    models = payload.get("data", [])
    model_ids = [str(item.get("id")) for item in models if isinstance(item, dict)]
    normalized_model_ids = {model_id.lower() for model_id in model_ids}
    if model.lower() not in normalized_model_ids:
        return fail(f"model {model!r} not found at {url}; available={model_ids}")
    return ok(f"model endpoint reachable and contains {model}")


def run_checks(args: argparse.Namespace) -> List[Dict[str, Any]]:
    checks = [
        {"name": "action_bank", **check_action_bank(pathlib.Path(args.action_bank))},
        {
            "name": "action_ir_projection",
            **check_action_ir_projection(pathlib.Path(args.action_ir), pathlib.Path(args.action_bank)),
        },
        {"name": "agent_module", **check_agent_module()},
    ]
    if not args.skip_tau2_import_check:
        checks.append({"name": "tau2_import", **check_tau2_import()})
    if not args.skip_model_check:
        checks.append({
            "name": "model_endpoint",
            **check_model_endpoint(args.agent_base_url, args.agent_model, args.api_key, args.timeout),
        })
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight official tau2 experiment dependencies.")
    parser.add_argument("--agent-model", default="gemma4-31b")
    parser.add_argument("--agent-base-url", default="http://172.16.22.79:9999/v1")
    parser.add_argument("--api-key", default="EMPTY")
    parser.add_argument("--action-bank", default=str(ACTION_BANK_PATH))
    parser.add_argument("--action-ir", default=str(ACTION_IR_PATH))
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--skip-tau2-import-check", action="store_true")
    parser.add_argument("--skip-model-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = run_checks(args)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            status = "OK" if result["ok"] else "FAIL"
            print(f"[{status}] {result['name']}: {result['message']}")

    if not all(result["ok"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
