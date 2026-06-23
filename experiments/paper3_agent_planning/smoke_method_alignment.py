#!/usr/bin/env python3
"""Method-level checks for ActionBank semantics, runtime state, and repair."""
from __future__ import annotations

import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank  # noqa: E402
from argument_grounder import ArgumentGrounder  # noqa: E402
from ontology_repair import OntologyRepairPlanner  # noqa: E402
from runtime_ontology import reconstruct_runtime_state  # noqa: E402
from tau2_admissibility import Tau2AdmissibilityChecker  # noqa: E402


def assert_prefix(violations: list[str], prefix: str) -> None:
    if not any(item.startswith(prefix) for item in violations):
        raise AssertionError(f"expected {prefix!r}, got {violations}")


def assert_no_prefix(violations: list[str], prefix: str) -> None:
    if any(item.startswith(prefix) for item in violations):
        raise AssertionError(f"unexpected {prefix!r}, got {violations}")


def tool_call(name: str, arguments: dict) -> dict:
    return {"role": "assistant", "tool_calls": [{"name": name, "arguments": arguments}]}


def tool_result(content, error: bool = False) -> dict:
    return {"role": "tool", "content": content, "error": error}


def main() -> None:
    action_bank = ActionBank.from_json(BASE_DIR / "data/action_bank/retail_action_bank.json")
    checker = Tau2AdmissibilityChecker(
        action_bank.list_actions(),
        action_bank,
        enabled=True,
        enforce_conditions=True,
    )

    exchange = action_bank.get("exchange_delivered_order_items")
    if exchange is None:
        raise AssertionError("missing exchange action")
    if exchange.target_binding != {"parameter": "order_id", "role": "target_identifier"}:
        raise AssertionError(f"target binding was not projected: {exchange.target_binding}")
    if exchange.parameter_semantics["new_item_ids"]["role"] != "replacement_items":
        raise AssertionError(f"parameter role was not projected: {exchange.parameter_semantics}")
    if not exchange.parameter_semantics["payment_method_id"]["required"]:
        raise AssertionError("required parameter semantics were not projected")
    if not exchange.parameter_semantics["new_item_ids"]["ontology_property_id"]:
        raise AssertionError("ontology property binding was not projected")

    auth_providers = {
        provider["action_id"]
        for provider in action_bank.providers_for("user_authenticated == true")
    }
    if not {"find_user_id_by_email", "find_user_id_by_name_zip"} <= auth_providers:
        raise AssertionError(f"authentication providers missing: {auth_providers}")
    status_providers = {
        provider["action_id"]
        for provider in action_bank.providers_for("order.status known")
    }
    if "get_order_details" not in status_providers:
        raise AssertionError(f"order-status provider missing: {status_providers}")

    messages = [
        tool_call("find_user_id_by_email", {"email": "a@example.com"}),
        tool_result("user-1"),
        tool_call("get_order_details", {"order_id": "#A"}),
        tool_result({
            "order_id": "#A",
            "user_id": "user-1",
            "status": "pending",
            "items": [{"item_id": "item-a", "product_id": "product-a"}],
            "payment_history": [{"payment_method_id": "pay-1"}],
        }),
        tool_call("get_order_details", {"order_id": "#B"}),
        tool_result({
            "order_id": "#B",
            "user_id": "user-1",
            "status": "delivered",
            "items": [{"item_id": "item-b", "product_id": "product-b"}],
            "payment_history": [{"payment_method_id": "pay-1"}],
        }),
        {
            "role": "assistant",
            "content": "Please confirm the return for order #B.",
            "raw_data": {
                "selected_candidate": {
                    "action": "respond_to_user",
                    "_repair_reason": "CONFIRMATION_REQUIRED",
                    "_repair_for": "return_delivered_order_items",
                    "_repair_arguments": {
                        "order_id": "#B",
                        "item_ids": ["item-b"],
                        "payment_method_id": "pay-1",
                    },
                }
            },
        },
        {"role": "user", "content": "Yes, return it."},
    ]
    state = reconstruct_runtime_state(messages, action_bank)
    if not state.user_authenticated:
        raise AssertionError("successful authentication result was not represented")
    if state.order_status("#A") != "pending" or state.order_status("#B") != "delivered":
        raise AssertionError(f"order states were not bound by id: {state.orders}")

    wrong_order_return = checker.verify_candidate(
        {
            "action": "return_delivered_order_items",
            "arguments": {
                "order_id": "#A",
                "item_ids": ["item-a"],
                "payment_method_id": "pay-1",
            },
        },
        [],
        runtime_state=state,
    )
    assert_prefix(wrong_order_return, "ORDER_STATUS_UNVERIFIED:")
    assert_prefix(wrong_order_return, "CONFIRMATION_REQUIRED:")

    confirmed_return = checker.verify_candidate(
        {
            "action": "return_delivered_order_items",
            "arguments": {
                "order_id": "#B",
                "item_ids": ["item-b"],
                "payment_method_id": "pay-1",
            },
        },
        [],
        runtime_state=state,
    )
    assert_no_prefix(confirmed_return, "ORDER_STATUS_UNVERIFIED:")
    assert_no_prefix(confirmed_return, "CONFIRMATION_REQUIRED:")
    assert_no_prefix(confirmed_return, "ROLE_BINDING:")

    proactive_messages = [
        *messages[:6],
        {
            "role": "assistant",
            "content": "Please confirm these two item exchanges.",
            "raw_data": {
                "selected_candidate": {
                    "action": "respond_to_user",
                    "confirmation_for": {
                        "action": "exchange_delivered_order_items",
                        "arguments": {
                            "order_id": "W0000001",
                            "item_ids": ["source-2", "source-1"],
                            "new_item_ids": ["target-2", "target-1"],
                            "payment_method_id": "pay-1",
                        },
                    },
                }
            },
        },
        {"role": "user", "content": "Yes."},
    ]
    proactive_state = reconstruct_runtime_state(proactive_messages, action_bank)
    if not proactive_state.has_confirmation(
        "exchange_delivered_order_items",
        {
            "order_id": "#W0000001",
            "item_ids": ["source-1", "source-2"],
            "new_item_ids": ["target-1", "target-2"],
            "payment_method_id": "pay-1",
        },
    ):
        raise AssertionError("proactive confirmation intent or canonical item mapping was lost")
    if proactive_state.has_confirmation(
        "exchange_delivered_order_items",
        {
            "order_id": "#W0000001",
            "item_ids": ["source-1", "source-2"],
            "new_item_ids": ["target-1", "target-2"],
            "payment_method_id": "pay-2",
        },
    ):
        raise AssertionError("confirmation must not authorize a changed payment method")

    missing_intent = checker.verify_candidate(
        {
            "action": "respond_to_user",
            "arguments": {},
            "message_to_user": "Please confirm that I should proceed with the order return.",
        },
        [],
        runtime_state=state,
    )
    assert_prefix(missing_intent, "CONFIRMATION_INTENT_REQUIRED:")

    rejected_confirmation_state = reconstruct_runtime_state(
        [
            proactive_messages[-2],
            {"role": "user", "content": "No, do not proceed."},
        ],
        action_bank,
    )
    if rejected_confirmation_state.confirmations:
        raise AssertionError("explicit rejection must clear the pending confirmation")

    state.products["product-b"] = {
        "product_id": "product-b",
        "variants": {
            "item-b": {"available": True},
            "item-b-new": {"available": True},
        },
    }
    role_grounded = ArgumentGrounder().ground(
        "renamed_exchange_action",
        {
            "order_id": "#B",
            "item_ids": "item-b",
            "new_item_ids": "item-b-new",
            "payment_method_id": "pay-1",
        },
        state.to_dialogue_state(),
        state.to_grounding_db(),
        schema=exchange,
    )
    if role_grounded.violations:
        raise AssertionError(f"role-driven grounding should not depend on action name: {role_grounded}")
    if role_grounded.arguments["item_ids"] != ["item-b"]:
        raise AssertionError(f"source item role was not normalized: {role_grounded.arguments}")

    failed_state = reconstruct_runtime_state(
        [
            tool_call("find_user_id_by_email", {"email": "missing@example.com"}),
            tool_result("not found", error=True),
        ],
        action_bank,
    )
    if failed_state.user_authenticated:
        raise AssertionError("failed lookup must not authenticate the user")
    if failed_state.has_successful_call(
        "find_user_id_by_email",
        {"email": "missing@example.com"},
    ):
        raise AssertionError("failed lookup must not become duplicate evidence")

    planner = OntologyRepairPlanner(action_bank, action_bank.list_actions())
    status_repair = planner.plan(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#C", "reason": "no longer needed"},
        },
        ["ORDER_STATUS_UNVERIFIED: cancel_pending_order requires order #C status pending"],
        state,
        "",
    )
    if status_repair is None or status_repair.get("action") != "get_order_details":
        raise AssertionError(f"predicate provider did not yield order lookup: {status_repair}")
    if status_repair.get("_missing_predicate") != "order.status known":
        raise AssertionError(f"repair did not preserve missing predicate: {status_repair}")

    confirmation_repair = planner.plan(
        {
            "action": "cancel_pending_order",
            "arguments": {"order_id": "#A", "reason": "no longer needed"},
        },
        ["CONFIRMATION_REQUIRED: cancel_pending_order requires explicit user confirmation"],
        state,
        "",
    )
    if confirmation_repair is None or confirmation_repair.get("action") != "respond_to_user":
        raise AssertionError(f"semantic confirmation provider was not used: {confirmation_repair}")
    if confirmation_repair.get("_provider_action") != "ask_for_confirmation":
        raise AssertionError(f"confirmation repair lost ontology provider: {confirmation_repair}")
    if confirmation_repair.get("confirmation_for", {}).get("action") != "cancel_pending_order":
        raise AssertionError(f"confirmation repair lost structured intent: {confirmation_repair}")
    repair_violations = checker.verify_candidate(
        confirmation_repair,
        [],
        runtime_state=state,
    )
    assert_no_prefix(repair_violations, "CONFIRMATION_INTENT_REQUIRED:")

    print("method alignment smoke tests passed")


if __name__ == "__main__":
    main()
