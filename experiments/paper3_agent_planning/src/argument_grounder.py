"""Ontology-grounded argument normalization for retail actions.

The verifier decides whether an action is admissible in the current state. This
module handles a different problem: binding LLM-proposed arguments to concrete
objects in the local ontology/database before verification and execution.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from action_bank import ActionSchema
from state_manager import DialogueState


ADDRESS_FIELDS = ("address1", "address2", "city", "country", "state", "zip")
PAYMENT_ACTIONS = {
    "modify_pending_order_items",
    "return_delivered_order_items",
    "exchange_delivered_order_items",
}

# LLMs sometimes hallucinate parameter names that differ from the ActionBank schema.
PARAMETER_NAME_ALIASES: Dict[str, Dict[str, str]] = {
    "find_user_id_by_name_zip": {"zip_code": "zip", "zipcode": "zip", "postal_code": "zip"},
    "get_order_details": {"order_number": "order_id", "orderId": "order_id"},
    "get_user_details": {"userId": "user_id", "user_id_number": "user_id"},
    "cancel_pending_order": {"order_number": "order_id", "orderId": "order_id"},
    "modify_pending_order_address": {"order_number": "order_id", "orderId": "order_id"},
    "modify_pending_order_items": {"order_number": "order_id", "orderId": "order_id"},
    "modify_pending_order_payment": {"order_number": "order_id", "orderId": "order_id"},
    "return_delivered_order_items": {"order_number": "order_id", "orderId": "order_id"},
    "exchange_delivered_order_items": {"order_number": "order_id", "orderId": "order_id"},
}

# Values that are clearly placeholders and must be rejected.
PLACEHOLDER_VALUES = {
    "user_email", "email_address", "unknown", "none", "n/a", "null", "",
    "order_id", "order_number", "user_id", "item_id", "product_id",
    "first_name", "last_name", "phone_number", "address", "reason",
}


def first(items: Optional[List[str]]) -> Optional[str]:
    return items[0] if items else None


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
        schema: Optional[ActionSchema] = None,
    ) -> GroundingResult:
        args = copy.deepcopy(arguments or {})
        changes: List[str] = []
        violations: List[str] = []

        # 1. Normalize hallucinated parameter names.
        aliases = PARAMETER_NAME_ALIASES.get(action_name, {})
        for raw_key, canonical in aliases.items():
            if raw_key in args:
                args[canonical] = args.pop(raw_key)
                changes.append(f"param_rename:{raw_key}->{canonical}")

        # 2. Detect placeholder values.
        for key, value in list(args.items()):
            if str(value).strip().lower() in PLACEHOLDER_VALUES:
                violations.append(f"PLACEHOLDER_VALUE: {action_name}.{key}={value}")

        if schema is not None:
            self._ground_from_semantic_roles(schema, args, state, db, changes, violations)
        else:
            self._ground_user_lookup(action_name, args, db, changes)
            self._ground_user_id(action_name, args, state, db, changes, violations)
            self._ground_order_id(action_name, args, state, db, changes, violations)
            self._ground_address(action_name, args, state, db, changes, violations)
            self._ground_payment_method(action_name, args, state, db, changes, violations)
            self._ground_item_lists(action_name, args, state, db, changes, violations)

        return GroundingResult(arguments=args, changes=changes, violations=violations)

    def _ground_from_semantic_roles(
        self,
        schema: ActionSchema,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        target_parameter = str(schema.target_binding.get("parameter") or "")
        if target_parameter:
            self._ground_target_identifier(
                schema,
                target_parameter,
                args,
                state,
                db,
                changes,
                violations,
            )

        role_parameters: Dict[str, List[str]] = {}
        for parameter, semantics in schema.parameter_semantics.items():
            role_parameters.setdefault(str(semantics.get("role") or ""), []).append(parameter)

        for parameter in role_parameters.get("new_value", []):
            ontology_property = schema.parameter_semantics[parameter].get("ontology_property_id", "")
            if str(ontology_property).endswith(".address"):
                self._ground_address_value(parameter, args, state, db, changes, violations)

        for parameter in role_parameters.get("payment_method", []):
            self._ground_payment_role(parameter, args, state, db, changes, violations)

        source_parameter = first(role_parameters.get("source_items"))
        replacement_parameter = first(role_parameters.get("replacement_items"))
        if source_parameter:
            self._ground_item_roles(
                source_parameter,
                replacement_parameter,
                args,
                state,
                db,
                changes,
                violations,
            )

    def _ground_target_identifier(
        self,
        schema: ActionSchema,
        parameter: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        object_type = schema.target_object.lower()
        value = args.get(parameter)
        if object_type == "order":
            if value in (None, "") and len(state.cached_orders) == 1:
                value = next(iter(state.cached_orders))
                args[parameter] = value
                changes.append(f"{parameter}:<missing>->{value}")
            canonical = self._canonical_order_id(value, db)
            if canonical:
                if canonical != value:
                    args[parameter] = canonical
                    changes.append(f"{parameter}:{value}->{canonical}")
            else:
                violations.append(f"GROUNDING: {parameter} {value or '<missing>'} does not identify an observed Order")
        elif object_type == "user":
            if state.user_id and value != state.user_id:
                args[parameter] = state.user_id
                changes.append(f"{parameter}:{value}->{state.user_id}")
            elif not state.user_id:
                violations.append(f"GROUNDING: {parameter} is not bound to an authenticated User")

    def _ground_address_value(
        self,
        parameter: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        address = self._extract_address(args, state, db)
        if address:
            if args.get(parameter) != address:
                changes.append(f"{parameter}:normalized")
            args[parameter] = address
            for field_name in ADDRESS_FIELDS:
                args.pop(field_name, None)
        else:
            violations.append(f"GROUNDING: {parameter} has no resolvable address binding")

    def _ground_payment_role(
        self,
        parameter: str,
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        value = args.get(parameter)
        valid_methods = self._payment_methods_for(args.get("order_id"), state, db)
        if value:
            if valid_methods and value not in valid_methods:
                violations.append(
                    f"GROUNDING: {parameter} {value} is not bound to order/user context"
                )
            return
        if len(valid_methods) == 1:
            args[parameter] = valid_methods[0]
            changes.append(f"{parameter}:<missing>->{valid_methods[0]}")
        elif valid_methods:
            violations.append(f"GROUNDING: ambiguous {parameter} candidates {valid_methods}")
        else:
            violations.append(f"GROUNDING: missing {parameter}")

    def _ground_item_roles(
        self,
        source_parameter: str,
        replacement_parameter: Optional[str],
        args: Dict[str, Any],
        state: DialogueState,
        db: Dict[str, Any],
        changes: List[str],
        violations: List[str],
    ) -> None:
        for parameter in (source_parameter, replacement_parameter):
            if parameter and parameter in args and isinstance(args[parameter], str):
                args[parameter] = [args[parameter]]
                changes.append(f"{parameter}:string->list")
        source_items = args.get(source_parameter)
        if not isinstance(source_items, list) or not source_items:
            violations.append(f"GROUNDING: missing {source_parameter}")
            return
        order = self._order_for(args.get("order_id"), state, db)
        if order:
            observed_items = {str(item.get("item_id")) for item in order.get("items", [])}
            missing = [item for item in source_items if str(item) not in observed_items]
            if missing:
                violations.append(
                    f"GROUNDING: {source_parameter} not bound to target order {missing}"
                )
        if replacement_parameter:
            replacements = args.get(replacement_parameter)
            if not isinstance(replacements, list) or not replacements:
                violations.append(f"GROUNDING: missing {replacement_parameter}")
            elif len(replacements) != len(source_items):
                violations.append(
                    f"GROUNDING: len({source_parameter}) != len({replacement_parameter})"
                )
            else:
                unknown = [item for item in replacements if not self._find_variant(str(item), db)]
                if unknown:
                    violations.append(
                        f"GROUNDING: {replacement_parameter} not observed {unknown}"
                    )

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
        zip_code = str(args.get("zip") or args.get("zip_code", ""))
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

        user_id = state.user_id
        if not user_id and order:
            user_id = order.get("user_id")
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
