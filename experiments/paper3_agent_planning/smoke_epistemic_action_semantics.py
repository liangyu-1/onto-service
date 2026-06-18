#!/usr/bin/env python3
"""Smoke tests for epistemic-vs-mutating action semantics."""
from __future__ import annotations

import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank  # noqa: E402
from tau2_admissibility import Tau2AdmissibilityChecker  # noqa: E402


def assert_no_prefix(violations: list[str], prefix: str) -> None:
    if any(item.startswith(prefix) for item in violations):
        raise AssertionError(f"unexpected violation prefix {prefix!r}: {violations}")


def assert_prefix(violations: list[str], prefix: str) -> None:
    if not any(item.startswith(prefix) for item in violations):
        raise AssertionError(f"expected violation prefix {prefix!r}: {violations}")


def main() -> None:
    action_bank = ActionBank.from_json(BASE_DIR / "data/action_bank/retail_action_bank.json")
    tool_names = set(action_bank.list_actions())
    checker = Tau2AdmissibilityChecker(tool_names, action_bank, enabled=True)

    order_read = action_bank.get("get_order_details")
    if order_read is None or order_read.action_kind != "epistemic" or order_read.grounding_mode != "weak":
        raise AssertionError(f"get_order_details should be epistemic/weak, got {order_read}")

    cancel = action_bank.get("cancel_pending_order")
    if cancel is None or cancel.action_kind != "mutate" or cancel.grounding_mode != "strong":
        raise AssertionError(f"cancel_pending_order should be mutate/strong, got {cancel}")

    admissible_read = checker.verify_candidate(
        {"action": "get_order_details", "arguments": {"order_id": "#W1234567"}},
        [{"action": "find_user_id_by_name_zip", "arguments": {"first_name": "A", "last_name": "B", "zip": "02139"}}],
        context_text="user authenticated; user asks for order #W1234567",
    )
    assert_no_prefix(admissible_read, "ORDER_STATUS_UNVERIFIED:")

    product_read = checker.verify_candidate(
        {"action": "get_product_details", "arguments": {"product_id": "9523456873"}},
        [{"action": "find_user_id_by_name_zip", "arguments": {"first_name": "A", "last_name": "B", "zip": "02139"}}],
        context_text="user authenticated; product id 9523456873 was listed by catalog lookup",
    )
    assert_no_prefix(product_read, "ORDER_STATUS_UNVERIFIED:")

    unauthenticated_read = checker.verify_candidate(
        {"action": "get_order_details", "arguments": {"order_id": "#W1234567"}},
        [],
        context_text="user asks for order #W1234567",
    )
    assert_prefix(unauthenticated_read, "AUTHENTICATION_REQUIRED:")

    premature_write = checker.verify_candidate(
        {"action": "cancel_pending_order", "arguments": {"order_id": "#W1234567", "reason": "no longer needed"}},
        [{"action": "find_user_id_by_name_zip", "arguments": {"first_name": "A", "last_name": "B", "zip": "02139"}}],
        context_text="user authenticated and wants to cancel #W1234567",
    )
    assert_prefix(premature_write, "ORDER_STATUS_UNVERIFIED:")
    assert_prefix(premature_write, "CONFIRMATION_REQUIRED:")

    print("epistemic action semantics smoke tests passed")


if __name__ == "__main__":
    main()
