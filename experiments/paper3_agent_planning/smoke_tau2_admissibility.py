#!/usr/bin/env python3
"""Smoke tests for tau2 ontology admissibility checks.

These checks intentionally avoid importing tau2. They validate the method
component that differentiates the ontology-guided agent from the schema-only
agent before official tau2 simulations are run.
"""
from __future__ import annotations

import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank  # noqa: E402
from tau2_admissibility import Tau2AdmissibilityChecker, deterministic_repair_candidate, repair_hints  # noqa: E402


def assert_contains(violations: list[str], prefix: str) -> None:
    if not any(v.startswith(prefix) for v in violations):
        raise AssertionError(f"expected violation prefix {prefix!r}, got {violations}")


def main() -> None:
    action_bank = ActionBank.from_json(BASE_DIR / "data/action_bank/retail_action_bank.json")
    tool_names = {
        "find_user_id_by_name_zip",
        "find_user_id_by_email",
        "get_user_details",
        "get_order_details",
        "cancel_pending_order",
        "respond_to_user",
        "official_tool_absent_from_action_bank",
    }
    checker = Tau2AdmissibilityChecker(tool_names, action_bank, enabled=True)

    missing_zip = checker.verify_candidate(
        {
            "action": "find_user_id_by_name_zip",
            "arguments": {"first_name": "Jane", "last_name": "Doe"},
        },
        [],
    )
    assert_contains(missing_zip, "MISSING_PARAMETER: find_user_id_by_name_zip.zip")
    zip_completion = deterministic_repair_candidate(
        {
            "action": "find_user_id_by_name_zip",
            "arguments": {"first_name": "Jane", "last_name": "Doe"},
        },
        missing_zip,
        tool_names,
        context_text="first name: Jane; last name: Doe; zip: 02139",
    )
    if zip_completion is None or zip_completion.get("arguments", {}).get("zip") != "02139":
        raise AssertionError(f"expected zip argument completion, got {zip_completion}")

    missing_email = checker.verify_candidate(
        {"action": "find_user_id_by_email", "arguments": {}},
        [],
        context_text="email: jane@example.com",
    )
    assert_contains(missing_email, "MISSING_PARAMETER: find_user_id_by_email.email")
    email_completion = deterministic_repair_candidate(
        {"action": "find_user_id_by_email", "arguments": {}},
        missing_email,
        tool_names,
        context_text="email: jane@example.com",
    )
    if email_completion is None or email_completion.get("arguments", {}).get("email") != "jane@example.com":
        raise AssertionError(f"expected email argument completion, got {email_completion}")

    unknown_action = checker.verify_candidate(
        {"action": "invent_refund_tool", "arguments": {}},
        [],
    )
    assert_contains(unknown_action, "UNKNOWN_ACTION:")

    absent_from_action_layer = checker.verify_candidate(
        {"action": "official_tool_absent_from_action_bank", "arguments": {}},
        [],
    )
    assert_contains(absent_from_action_layer, "NOT_IN_ACTION_LAYER:")

    duplicate = checker.verify_candidate(
        {
            "action": "find_user_id_by_email",
            "arguments": {"email": "jane@example.com"},
        },
        [{"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}}],
    )
    assert_contains(duplicate, "DUPLICATE:")

    no_message = checker.verify_candidate(
        {"action": "respond_to_user", "arguments": {}, "message_to_user": ""},
        [],
    )
    assert_contains(no_message, "COMMUNICATE:")

    valid = checker.verify_candidate(
        {
            "action": "find_user_id_by_name_zip",
            "arguments": {"first_name": "Jane", "last_name": "Doe", "zip": "02139"},
        },
        [],
    )
    if valid:
        raise AssertionError(f"expected admissible action, got {valid}")

    premature_cancel = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        [],
        context_text="user asks to cancel order #O-100",
    )
    assert_contains(premature_cancel, "AUTHENTICATION_REQUIRED:")
    assert_contains(premature_cancel, "CONFIRMATION_REQUIRED:")
    assert_contains(premature_cancel, "ORDER_STATUS_UNVERIFIED:")
    hints = repair_hints(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        premature_cancel,
    )
    expected_hint_fragments = ["find_user_id", "message_to_user", "get_order_details"]
    for fragment in expected_hint_fragments:
        if not any(fragment in hint for hint in hints):
            raise AssertionError(f"expected repair hint containing {fragment!r}, got {hints}")
    auth_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        premature_cancel,
        tool_names,
        context_text="customer email is jane@example.com and asks to cancel order #O-100",
    )
    if auth_repair is None or auth_repair.get("action") != "find_user_id_by_email":
        raise AssertionError(f"expected email authentication repair, got {auth_repair}")
    repeated_auth_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        premature_cancel,
        tool_names,
        context_text="customer email is jane@example.com and asks to cancel order #O-100",
        history_tool_calls=[{"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}}],
    )
    if repeated_auth_repair is not None:
        raise AssertionError(f"expected repeated auth repair suppression, got {repeated_auth_repair}")
    name_zip_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        premature_cancel,
        tool_names,
        context_text="first name: Jane; last name: Doe; zip: 02139; please cancel order #O-100",
    )
    if name_zip_repair is None or name_zip_repair.get("action") != "find_user_id_by_name_zip":
        raise AssertionError(f"expected name_zip authentication repair, got {name_zip_repair}")
    if name_zip_repair.get("arguments") != {"first_name": "Jane", "last_name": "Doe", "zip": "02139"}:
        raise AssertionError(f"unexpected name_zip arguments: {name_zip_repair}")
    no_guess_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        premature_cancel,
        tool_names,
        context_text="Jane Doe from 02139 wants to cancel order #O-100",
    )
    if no_guess_repair is not None:
        raise AssertionError(f"name_zip repair should require explicit labels, got {no_guess_repair}")

    lite_checker = Tau2AdmissibilityChecker(
        tool_names,
        action_bank,
        enabled=True,
        enforce_conditions=False,
    )
    lite_cancel = lite_checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        [],
        context_text="user asks to cancel order #O-100",
    )
    if lite_cancel:
        raise AssertionError(f"lite gate should not enforce semantic preconditions, got {lite_cancel}")

    invalid_reason = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "changed my mind"},
        },
        [
            {"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}},
        ],
        context_text="tool result: order_id #O-100 has status pending. user: yes, cancel it",
    )
    assert_contains(invalid_reason, "INVALID_REASON:")

    needs_status = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-101", "reason": "no longer needed"},
        },
        [
            {"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}},
        ],
        context_text="user is authenticated and said: yes, cancel it",
    )
    assert_contains(needs_status, "ORDER_STATUS_UNVERIFIED:")
    status_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-101", "reason": "no longer needed"},
        },
        needs_status,
        tool_names,
    )
    if status_repair is None or status_repair.get("action") != "get_order_details":
        raise AssertionError(f"expected get_order_details deterministic repair, got {status_repair}")
    missing_order_id = checker.verify_candidate(
        {"action": "get_order_details", "arguments": {}},
        [{"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}}],
        context_text="please check order #O-555",
    )
    assert_contains(missing_order_id, "MISSING_PARAMETER: get_order_details.order_id")
    order_completion = deterministic_repair_candidate(
        {"action": "get_order_details", "arguments": {}},
        missing_order_id,
        tool_names,
        context_text="please check order #O-555",
    )
    if order_completion is None or order_completion.get("arguments", {}).get("order_id") != "#O-555":
        raise AssertionError(f"expected order_id argument completion, got {order_completion}")
    ambiguous_order_completion = deterministic_repair_candidate(
        {"action": "get_order_details", "arguments": {}},
        missing_order_id,
        tool_names,
        context_text="compare orders #O-555 and #O-556",
    )
    if ambiguous_order_completion is not None:
        raise AssertionError(f"expected no completion for multiple order ids, got {ambiguous_order_completion}")

    missing_order_and_auth = checker.verify_candidate(
        {"action": "cancel_pending_order", "arguments": {"reason": "no longer needed"}},
        [],
        context_text="email: jane@example.com; please cancel order #O-777",
    )
    assert_contains(missing_order_and_auth, "MISSING_PARAMETER: cancel_pending_order.order_id")
    assert_contains(missing_order_and_auth, "AUTHENTICATION_REQUIRED:")
    priority_repair = deterministic_repair_candidate(
        {"action": "cancel_pending_order", "arguments": {"reason": "no longer needed"}},
        missing_order_and_auth,
        tool_names,
        context_text="email: jane@example.com; please cancel order #O-777",
    )
    if priority_repair is None or priority_repair.get("action") != "find_user_id_by_email":
        raise AssertionError(f"expected authentication before business-argument completion, got {priority_repair}")
    repeated_status_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-101", "reason": "no longer needed"},
        },
        needs_status,
        tool_names,
        history_tool_calls=[
            {"action": "get_order_details", "arguments": {"order_id": "#O-101"}},
        ],
    )
    if repeated_status_repair is not None:
        raise AssertionError(f"expected repeated status repair suppression, got {repeated_status_repair}")

    needs_confirmation = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-102", "reason": "no longer needed"},
        },
        [{"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}}],
        context_text="tool result: order_id #O-102 has status pending",
    )
    assert_contains(needs_confirmation, "CONFIRMATION_REQUIRED:")
    vague_yes = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-102", "reason": "no longer needed"},
        },
        [{"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}}],
        context_text="tool result: order_id #O-102 has status pending. user: yes",
    )
    assert_contains(vague_yes, "CONFIRMATION_REQUIRED:")
    explicit_yes = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-102", "reason": "no longer needed"},
        },
        [{"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}}],
        context_text="tool result: order_id #O-102 has status pending. user: yes, cancel it",
    )
    if explicit_yes:
        raise AssertionError(f"expected explicit yes confirmation to pass, got {explicit_yes}")
    confirmation_repair = deterministic_repair_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-102", "reason": "no longer needed"},
        },
        needs_confirmation,
        tool_names,
    )
    if confirmation_repair is None or confirmation_repair.get("action") != "respond_to_user":
        raise AssertionError(f"expected respond_to_user confirmation repair, got {confirmation_repair}")
    if "confirm" not in confirmation_repair.get("message_to_user", "").lower():
        raise AssertionError(f"expected confirmation prompt text, got {confirmation_repair}")

    grounded_cancel = checker.verify_candidate(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#O-100", "reason": "no longer needed"},
        },
        [
            {"action": "find_user_id_by_email", "arguments": {"email": "jane@example.com"}},
        ],
        context_text="tool result: order_id #O-100 has status pending. user: yes, cancel it",
    )
    if grounded_cancel:
        raise AssertionError(f"expected grounded cancel to be admissible, got {grounded_cancel}")

    disabled_checker = Tau2AdmissibilityChecker(tool_names, action_bank, enabled=False)
    bypassed = disabled_checker.verify_candidate(
        {"action": "invent_refund_tool", "arguments": {}},
        [],
    )
    if bypassed:
        raise AssertionError(f"schema-mode checker should bypass violations, got {bypassed}")

    print("tau2 admissibility smoke tests passed")


if __name__ == "__main__":
    main()
