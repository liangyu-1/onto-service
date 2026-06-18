#!/usr/bin/env python3
"""Check that canonical Action IR projects to the committed runtime ActionBank."""
from __future__ import annotations

import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank  # noqa: E402


def canonical(data: dict) -> dict:
    return {
        "actions": sorted(
            data.get("actions", []),
            key=lambda item: item["action_id"],
        )
    }


def main() -> None:
    ir_path = BASE_DIR / "data/action_ir/retail_action_ir.json"
    bank_path = BASE_DIR / "data/action_bank/retail_action_bank.json"
    projected = ActionBank.from_action_ir_json(ir_path)
    projected_path = pathlib.Path("/private/tmp/retail_action_bank.projected.json")
    projected.save(projected_path)

    with open(projected_path) as f:
        projected_data = json.load(f)
    with open(bank_path) as f:
        committed_data = json.load(f)

    if canonical(projected_data) != canonical(committed_data):
        raise AssertionError(
            "retail_action_bank.json is not the deterministic projection of retail_action_ir.json. "
            "Run compile_action_ir_to_action_bank.py and inspect the diff."
        )
    print("action IR projection smoke test passed")


if __name__ == "__main__":
    main()
