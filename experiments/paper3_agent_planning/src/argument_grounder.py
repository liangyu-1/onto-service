"""Ontology-grounded argument normalization for retail actions.

The verifier decides whether an action is admissible in the current state. This
module handles a different problem: binding LLM-proposed arguments to concrete
objects in the local ontology/database before verification and execution.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from state_manager import DialogueState


ADDRESS_FIELDS = ("address1", "address2", "city", "country", "state", "zip")
PAYMENT_ACTIONS = {
    "modify_pending_order_items",
    "return_delivered_order_items",
    "exchange_delivered_order_items",
}


@dataclass
class GroundingResult:
    arguments: Dict[str, Any]
    changes: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)


class ArgumentGrounder:
    """Ground action arguments against known users, orders, products and items."""

    def ground(
        self,
        action_name: str,
        arguments: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
    ) -> GroundingResult:
        args = copy.deepcopy(arguments or {})
        changes: List[str] = []
        violations: List[str] = []

        self._ground_user_lookup(action_name, args, db, changes)
        self._ground_user_id(action_name, args, state, db, changes, violations)
        self._ground_order_id(action_name, args, state, db, changes, violations)
        self._ground_address(action_name, args, state, db, changes, violations)
        self._ground_payment_method(action_name, args, state, db, changes, violations)
        self._ground_item_lists(action_name, args, state, db, changes, violations)

        return GroundingResult(arguments=args, changes=changes, violations=violations)

    def _ground_user_lookup(
        self,
        action_name: str,
        args: Dict[str, Any],
        db: Dict[str, Any],
        changes: List[str],
    ) -> None:
        if action_name != "find_user_id_by_name_zip":
            return
        first = args.get("first_name")
        last = args.get("last_name")
        zip_code = str(args.get("zip", ""))
        if not first or not last or not zip_code:
            return
        for user in db.get("users", {}).values():
            name = user.get("name", {})
            addr = user.get("address", {})
            if (
                str(name.get("first_name", "")).lower() == str(first).lower()
                and str(name.get("last_name", "")).lower() == str(last).lower()
                and str(addr.get("zip", "")) == zip_code
            ):
                exact_first = name.get("first_name")
                exact_last = name.get("last_name")
                if args.get("first_name") != exact_first:
                    changes.append(f"first_name:{args.get('first_name')}->{exact_first}")
                    args["first_name"] = exact_first
                if args.get("last_name") != exact_last:
                    changes.append(f"last_name:{args.get('last_name')}->{exact_last}")
                    args["last_name"] = exact_last
                return

    def _ground_user_id(
        self,
        action_name: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        if action_name not in {"get_user_details", "modify_user_address"}:
            return
        user_id = args.get("user_id")
        if user_id in db.get("users", {}):
            return
        if state.user_id and state.user_id in db.get("users", {}):
            changes.append(f"user_id:{user_id}->{state.user_id}")
            args["user_id"] = state.user_id
            return
        if user_id:
            violations.append(f"GROUNDING: user_id {user_id} does not exist")
        else:
            violations.append("GROUNDING: missing user_id")

    def _ground_order_id(
        self,
        action_name: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        if "order_id" not in args:
            if self._needs_order(action_name) and len(state.cached_orders) == 1:
                order_id = next(iter(state.cached_orders))
                changes.append(f"order_id:<missing>->{order_id}")
                args["order_id"] = order_id
            elif self._needs_order(action_name):
                violations.append("GROUNDING: missing order_id")
            return

        original = args.get("order_id")
        grounded = self._canonical_order_id(original, db)
        if grounded and grounded != original:
            changes.append(f"order_id:{original}->{grounded}")
            args["order_id"] = grounded
        elif not grounded and self._needs_order(action_name):
            violations.append(f"GROUNDING: order_id {original} does not exist")

    def _ground_address(
        self,
        action_name: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        if action_name not in {"modify_user_address", "modify_pending_order_address"}:
            return

        address = self._extract_address(args, state, db)
        if address:
            if args.get("address") != address:
                changes.append("address:normalized")
            args["address"] = address
            for field_name in ADDRESS_FIELDS:
                args.pop(field_name, None)
            return

        violations.append("GROUNDING: missing resolvable address")

    def _ground_payment_method(
        self,
        action_name: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        if action_name not in PAYMENT_ACTIONS:
            return
        payment_method_id = args.get("payment_method_id")
        valid_methods = self._payment_methods_for(args.get("order_id"), state, db)
        if payment_method_id:
            if not valid_methods or payment_method_id in valid_methods:
                return
            violations.append(
                f"GROUNDING: payment_method_id {payment_method_id} is not bound to order/user context"
            )
            return
        if len(valid_methods) == 1:
            selected = valid_methods[0]
            changes.append(f"payment_method_id:<missing>->{selected}")
            args["payment_method_id"] = selected
        elif valid_methods:
            violations.append(f"GROUNDING: ambiguous payment_method_id candidates {valid_methods}")
        else:
            violations.append("GROUNDING: missing payment_method_id")

    def _ground_item_lists(
        self,
        action_name: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        if action_name not in {
            "modify_pending_order_items",
            "return_delivered_order_items",
            "exchange_delivered_order_items",
        }:
            return
        for key in ("item_ids", "new_item_ids"):
            if key in args and isinstance(args[key], str):
                args[key] = [args[key]]
                changes.append(f"{key}:string->list")

        item_ids = args.get("item_ids")
        if not isinstance(item_ids, list) or not item_ids:
            violations.append("GROUNDING: missing item_ids")
            return

        order = self._order_for(args.get("order_id"), state, db)
        if order:
            order_item_ids = {str(item.get("item_id")) for item in order.get("items", [])}
            missing = [item_id for item_id in item_ids if str(item_id) not in order_item_ids]
            if missing:
                violations.append(f"GROUNDING: item_ids not in order {missing}")

        if action_name in {"modify_pending_order_items", "exchange_delivered_order_items"}:
            new_item_ids = args.get("new_item_ids")
            if not isinstance(new_item_ids, list) or not new_item_ids:
                violations.append("GROUNDING: missing new_item_ids")
            elif len(new_item_ids) != len(item_ids):
                violations.append("GROUNDING: len(item_ids) != len(new_item_ids)")
            else:
                unknown = [item_id for item_id in new_item_ids if not self._find_variant(str(item_id), db)]
                if unknown:
                    violations.append(f"GROUNDING: new_item_ids not found {unknown}")

    def _extract_address(
        self,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        address = args.get("address")
        if isinstance(address, dict):
            source_order = address.get("source_order") or address.get("from_order")
            if source_order:
                order = self._order_for(self._canonical_order_id(source_order, db) or source_order, state, db)
                if order and isinstance(order.get("address"), dict):
                    return copy.deepcopy(order["address"])
            source_user = address.get("source_user") or address.get("from_user")
            if source_user and source_user in db.get("users", {}):
                user_address = db["users"][source_user].get("address")
                if isinstance(user_address, dict):
                    return copy.deepcopy(user_address)
            if all(field_name in address for field_name in ("address1", "city", "state", "zip")):
                return {k: address.get(k, "") for k in ADDRESS_FIELDS if k in address}

        flat = {k: args.get(k) for k in ADDRESS_FIELDS if k in args}
        if all(flat.get(k) for k in ("address1", "city", "state", "zip")):
            return flat

        user_id = args.get("user_id") or state.user_id
        user = db.get("users", {}).get(user_id) if user_id else None
        if user and isinstance(user.get("address"), dict):
            return copy.deepcopy(user["address"])
        return None

    def _canonical_order_id(self, order_id: Any, db: Dict[str, Any]) -> Optional[str]:
        if order_id is None:
            return None
        value = str(order_id)
        orders = db.get("orders", {})
        if value in orders:
            return value
        if not value.startswith("#") and f"#{value}" in orders:
            return f"#{value}"
        if value.startswith("#") and value[1:] in orders:
            return value[1:]
        lowered = value.lower().lstrip("#")
        for oid in orders:
            if str(oid).lower().lstrip("#") == lowered:
                return oid
        return None

    def _needs_order(self, action_name: str) -> bool:
        return action_name in {
            "get_order_details",
            "cancel_pending_order",
            "modify_pending_order_address",
            "modify_pending_order_items",
            "modify_pending_order_payment",
            "return_delivered_order_items",
            "exchange_delivered_order_items",
        }

    def _order_for(
        self,
        order_id: Any,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        canonical = self._canonical_order_id(order_id, db)
        if canonical and canonical in state.cached_orders:
            return state.cached_orders[canonical]
        if canonical and canonical in db.get("orders", {}):
            return db["orders"][canonical]
        return None

    def _payment_methods_for(
        self,
        order_id: Any,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> List[str]:
        methods: List[str] = []
        order = self._order_for(order_id, state, db)
        if order:
            for payment in order.get("payment_history", []):
                payment_id = payment.get("payment_method_id")
                if payment_id and payment_id not in methods:
                    methods.append(payment_id)
            if methods:
                return methods

        user_id = state.user_id
        user = db.get("users", {}).get(user_id) if user_id else None
        if user:
            for payment_id in user.get("payment_methods", {}).keys():
                if payment_id not in methods:
                    methods.append(payment_id)
        return methods

    def _find_variant(self, item_id: str, db: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        for product_id, product in db.get("products", {}).items():
            variants = product.get("variants", {})
            if item_id in variants:
                return product_id, variants[item_id]
        return None
