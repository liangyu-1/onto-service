"""Predicate-driven repair planning over ActionBank enabling semantics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from action_bank import ActionBank


@dataclass(frozen=True)
class MissingPredicate:
    predicate: str
    violation_type: str
    arguments: Dict[str, Any]


class OntologyRepairPlanner:
    """Resolve missing predicates to enabling actions declared by ActionBank."""

    def __init__(self, action_bank: ActionBank, tool_names: Iterable[str]):
        self.action_bank = action_bank
        self.tool_names = set(tool_names)

    def plan(
        self,
        candidate: Dict[str, Any],
        violations: Iterable[str],
        runtime_state: Any,
        context_text: str,
    ) -> Optional[Dict[str, Any]]:
        missing = missing_predicates(candidate, violations)
        for requirement in missing:
            providers = self.action_bank.providers_for(requirement.predicate)
            for provider in providers:
                repair = self._instantiate_provider(
                    provider,
                    candidate,
                    requirement,
                    runtime_state,
                    context_text,
                )
                if repair is not None:
                    repair["_repair_for"] = str(candidate.get("action") or "")
                    repair["_repair_arguments"] = dict(candidate.get("arguments") or {})
                    repair["_repair_reason"] = requirement.violation_type
                    repair["_missing_predicate"] = requirement.predicate
                    repair["_provider_action"] = provider.get("action_id", "")
                    return repair
        return self._parameter_completion(candidate, missing, context_text)

    def _instantiate_provider(
        self,
        provider: Dict[str, str],
        candidate: Dict[str, Any],
        missing: MissingPredicate,
        runtime_state: Any,
        context_text: str,
    ) -> Optional[Dict[str, Any]]:
        provider_action = provider.get("action_id", "")
        runtime_role = provider.get("runtime_role", "tool")
        arguments = dict(candidate.get("arguments") or {})

        if runtime_role == "dialogue_act":
            return {
                "thought": f"Acquire missing predicate {missing.predicate}.",
                "action": "respond_to_user",
                "arguments": {},
                "message_to_user": confirmation_message(candidate),
            }
        if provider_action not in self.tool_names:
            return None

        provider_schema = self.action_bank.get(provider_action)
        if provider_schema is None:
            return None
        provider_arguments: Dict[str, Any] = {}
        for parameter, semantics in provider_schema.parameter_semantics.items():
            role = semantics.get("role")
            value = self._bind_provider_parameter(
                parameter,
                role,
                arguments,
                runtime_state,
                context_text,
            )
            if value not in (None, "", []):
                provider_arguments[parameter] = value
            elif semantics.get("required", True):
                return None
        return {
            "thought": f"Acquire missing predicate {missing.predicate} with {provider_action}.",
            "action": provider_action,
            "arguments": provider_arguments,
            "message_to_user": "",
        }

    def _bind_provider_parameter(
        self,
        parameter: str,
        role: str,
        rejected_arguments: Dict[str, Any],
        runtime_state: Any,
        context_text: str,
    ) -> Any:
        if parameter in rejected_arguments:
            return rejected_arguments[parameter]
        if role == "target_identifier":
            if parameter == "user_id":
                return runtime_state.user_id
            if parameter == "product_id":
                product_id = product_needed_for_replacement(rejected_arguments, runtime_state)
                if product_id:
                    return product_id
        if parameter == "email":
            match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", context_text)
            return match.group(0) if match else None
        if parameter in {"first_name", "last_name", "zip"}:
            values = extract_labeled_name_zip(context_text)
            return values.get(parameter)
        return None

    def _parameter_completion(
        self,
        candidate: Dict[str, Any],
        missing: List[MissingPredicate],
        context_text: str,
    ) -> Optional[Dict[str, Any]]:
        action = str(candidate.get("action") or "")
        arguments = dict(candidate.get("arguments") or {})
        changed = False
        for requirement in missing:
            if requirement.violation_type != "MISSING_PARAMETER":
                continue
            parameter = requirement.predicate.rsplit(".", 1)[-1]
            if parameter == "email":
                match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", context_text)
                if match:
                    arguments[parameter] = match.group(0)
                    changed = True
            elif parameter == "order_id":
                matches = list(dict.fromkeys(re.findall(r"#[A-Za-z0-9][A-Za-z0-9_-]*", context_text)))
                if len(matches) == 1:
                    arguments[parameter] = matches[0]
                    changed = True
            elif parameter in {"first_name", "last_name", "zip"}:
                value = extract_labeled_name_zip(context_text).get(parameter)
                if value:
                    arguments[parameter] = value
                    changed = True
        if not changed:
            return None
        return {
            "thought": f"Complete missing role fillers for {action}.",
            "action": action,
            "arguments": arguments,
            "message_to_user": str(candidate.get("message_to_user") or ""),
            "_repair_for": action,
            "_repair_arguments": dict(candidate.get("arguments") or {}),
            "_repair_reason": "MISSING_PARAMETER",
            "_missing_predicate": "required parameter bound",
            "_provider_action": action,
        }


def missing_predicates(
    candidate: Dict[str, Any],
    violations: Iterable[str],
) -> List[MissingPredicate]:
    action = str(candidate.get("action") or "")
    arguments = dict(candidate.get("arguments") or {})
    missing: List[MissingPredicate] = []
    for violation in violations:
        violation_text = str(violation)
        violation_type = violation_text.split(":", 1)[0]
        if violation_type == "AUTHENTICATION_REQUIRED":
            predicate = "user_authenticated == true"
        elif violation_type == "CONFIRMATION_REQUIRED":
            predicate = "user_confirmed == true"
        elif violation_type == "ORDER_STATUS_UNVERIFIED":
            predicate = "order.status known"
        elif violation_type == "ROLE_BINDING" and (
            "replacement" in violation_text or "variants" in violation_text
        ):
            predicate = "product.variants known"
        elif violation_type == "MISSING_PARAMETER":
            detail = violation_text.split(":", 1)[1].strip() if ":" in violation_text else action
            predicate = f"required parameter bound.{detail.rsplit('.', 1)[-1]}"
        else:
            continue
        missing.append(MissingPredicate(predicate, violation_type, arguments))
    return missing


def product_needed_for_replacement(arguments: Dict[str, Any], runtime_state: Any) -> str:
    order_id = arguments.get("order_id")
    source_items = arguments.get("item_ids") or []
    if isinstance(source_items, str):
        source_items = [source_items]
    products = {
        runtime_state.order_item_product(order_id, item_id)
        for item_id in source_items
        if runtime_state.order_item_product(order_id, item_id)
    }
    return next(iter(products)) if len(products) == 1 else ""


def confirmation_message(candidate: Dict[str, Any]) -> str:
    action = str(candidate.get("action") or "")
    arguments = dict(candidate.get("arguments") or {})
    order_id = arguments.get("order_id")
    target = f" for order {order_id}" if order_id else ""
    return f"Please confirm that you want me to proceed with {action}{target}."


def extract_labeled_name_zip(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    labels = {
        "first_name": ("first name", "first_name", "firstname"),
        "last_name": ("last name", "last_name", "lastname"),
        "zip": ("zip code", "zipcode", "zip"),
    }
    for key, variants in labels.items():
        for label in variants:
            match = re.search(
                rf"\b{re.escape(label)}\b\s*[:=]\s*([A-Za-z0-9'-]+)",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                values[key] = match.group(1)
                break
    return values
