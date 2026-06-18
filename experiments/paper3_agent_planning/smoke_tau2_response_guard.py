#!/usr/bin/env python3
"""Smoke tests for premature generic response guard."""
from __future__ import annotations

import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

from tau2_admissibility import repair_hints  # noqa: E402
from tau2_ontology_agent import premature_response_violations  # noqa: E402


def main() -> None:
    rejected = [
        {
            "candidate": {"action": "cancel_pending_order", "arguments": {"order_id": "#O-1"}},
            "violations": ["CONFIRMATION_REQUIRED: cancel_pending_order requires explicit user confirmation"],
            "repair_hints": ["Ask the user for explicit confirmation in `message_to_user` before issuing the mutating action."],
        }
    ]
    generic = {
        "action": "respond_to_user",
        "arguments": {},
        "message_to_user": "I cannot complete this request with the available tools.",
    }
    violations = premature_response_violations(generic, rejected, gate_enabled=True)
    if not violations or not violations[0].startswith("PREMATURE_RESPONSE:"):
        raise AssertionError(f"expected premature response violation, got {violations}")
    hints = repair_hints(generic, violations)
    if not any("prerequisite" in hint for hint in hints):
        raise AssertionError(f"expected repair hint for premature response, got {hints}")

    informative = {
        "action": "respond_to_user",
        "arguments": {},
        "message_to_user": "Your order #O-1 has been cancelled and the refund was issued.",
    }
    if premature_response_violations(informative, rejected, gate_enabled=True):
        raise AssertionError("informative user response should not be blocked")

    if premature_response_violations(generic, rejected, gate_enabled=False):
        raise AssertionError("schema/prompt-only modes should not apply the gate response guard")

    print("tau2 response guard smoke tests passed")


if __name__ == "__main__":
    main()
