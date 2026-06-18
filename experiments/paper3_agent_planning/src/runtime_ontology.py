"""Structured runtime ontology state reconstructed from observed tau2 events."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from action_bank import ActionBank, ActionSchema
from state_manager import DialogueState


@dataclass(frozen=True)
class SuccessfulToolCall:
    action: str
    arguments: Dict[str, Any]
    result: Any


@dataclass(frozen=True)
class ConfirmationBinding:
    action: str
    arguments: Dict[str, Any]


@dataclass
class RuntimeOntologyState:
    """Ontology individuals and predicates supported by observed trajectory evidence."""

    user_id: str = ""
    users: Dict[str, Any] = field(default_factory=dict)
    orders: Dict[str, Any] = field(default_factory=dict)
    products: Dict[str, Any] = field(default_factory=dict)
    product_type_ids: Dict[str, str] = field(default_factory=dict)
    payment_methods: Dict[str, Any] = field(default_factory=dict)
    successful_tool_calls: List[SuccessfulToolCall] = field(default_factory=list)
    confirmations: List[ConfirmationBinding] = field(default_factory=list)
    executed_mutations: List[SuccessfulToolCall] = field(default_factory=list)
    grounding_changes: List[str] = field(default_factory=list)

    @property
    def user_authenticated(self) -> bool:
        return bool(self.user_id)

    def to_dialogue_state(self) -> DialogueState:
        state = DialogueState(
            user_id=self.user_id or None,
            user_authenticated=self.user_authenticated,
            cached_users=dict(self.users),
            cached_orders=dict(self.orders),
            cached_products=dict(self.products),
        )
        state.action_taken_on_order = {
            str(call.arguments["order_id"]): True
            for call in self.executed_mutations
            if call.arguments.get("order_id")
        }
        return state

    def to_grounding_db(self) -> Dict[str, Any]:
        """Build a DB-shaped view using only observed official tool outputs."""
        users = dict(self.users)
        if self.user_id and self.user_id not in users:
            users[self.user_id] = {
                "user_id": self.user_id,
                "payment_methods": dict(self.payment_methods),
            }
        for order in self.orders.values():
            user_id = order.get("user_id")
            if user_id and user_id not in users:
                users[user_id] = {
                    "user_id": user_id,
                    "payment_methods": dict(self.payment_methods),
                }
        return {
            "users": users,
            "orders": dict(self.orders),
            "products": dict(self.products),
        }

    def has_successful_call(self, action: str, arguments: Dict[str, Any]) -> bool:
        signature = stable_json(arguments)
        return any(
            call.action == action and stable_json(call.arguments) == signature
            for call in self.successful_tool_calls
        )

    def has_confirmation(self, action: str, arguments: Dict[str, Any]) -> bool:
        target = target_signature(arguments)
        for confirmation in reversed(self.confirmations):
            if confirmation.action != action:
                continue
            if target_signature(confirmation.arguments) == target:
                return True
        return False

    def order_status(self, order_id: Any) -> str:
        order = self.orders.get(canonical_observed_id(order_id, self.orders))
        return str((order or {}).get("status") or "").lower()

    def target_observed(self, schema: ActionSchema, arguments: Dict[str, Any]) -> bool:
        binding_parameter = str(schema.target_binding.get("parameter") or "")
        if not binding_parameter:
            return True
        identifier = arguments.get(binding_parameter)
        if identifier in (None, ""):
            return False
        object_type = schema.target_object.lower()
        if object_type == "order":
            return bool(canonical_observed_id(identifier, self.orders))
        if object_type == "user":
            return str(identifier) in self.users or str(identifier) == self.user_id
        if object_type == "product":
            return str(identifier) in self.products or self.variant_product_id(str(identifier)) is not None
        return True

    def mutation_taken_on_order(self, order_id: Any, exclude_action: str = "") -> bool:
        canonical = canonical_observed_id(order_id, self.orders) or str(order_id or "")
        return any(
            call.action != exclude_action
            and str(call.arguments.get("order_id") or "") == canonical
            for call in self.executed_mutations
        )

    def order_item_ids(self, order_id: Any) -> set[str]:
        order = self.orders.get(canonical_observed_id(order_id, self.orders), {})
        return {str(item.get("item_id")) for item in order.get("items", []) or [] if item.get("item_id")}

    def order_item_product(self, order_id: Any, item_id: Any) -> str:
        order = self.orders.get(canonical_observed_id(order_id, self.orders), {})
        for item in order.get("items", []) or []:
            if str(item.get("item_id")) == str(item_id):
                return str(item.get("product_id") or "")
        return ""

    def variant_product_id(self, item_id: Any) -> Optional[str]:
        for product_id, product in self.products.items():
            if str(item_id) in (product.get("variants") or {}):
                return str(product_id)
        return None

    def valid_payment_method_ids(self, order_id: Any = None) -> set[str]:
        methods = set(self.payment_methods)
        order = self.orders.get(canonical_observed_id(order_id, self.orders), {})
        for payment in order.get("payment_history", []) or []:
            payment_id = payment.get("payment_method_id")
            if payment_id:
                methods.add(str(payment_id))
        return methods

    def to_prompt_text(self) -> str:
        lines: List[str] = []
        if self.user_id:
            lines.append(f"Authenticated user_id: {self.user_id}")
        if self.payment_methods:
            lines.append(f"Known payment_method_ids: {', '.join(sorted(self.payment_methods))}")
        if self.orders:
            lines.append("Known orders:")
            for order_id, order in sorted(self.orders.items()):
                items = []
                for item in order.get("items", []) or []:
                    items.append(
                        f"{item.get('name', '')}[item_id={item.get('item_id', '')}, "
                        f"product_id={item.get('product_id', '')}, options={item.get('options', {})}]"
                    )
                lines.append(
                    f"- {order_id}: status={order.get('status', '')}; items={'; '.join(items[:8])}"
                )
        if self.products:
            lines.append("Known product variants:")
            for product_id, product in sorted(self.products.items()):
                variants = []
                for item_id, variant in (product.get("variants") or {}).items():
                    if variant.get("available") is False:
                        continue
                    variants.append(
                        f"{item_id}: options={variant.get('options', {})}, price={variant.get('price')}"
                    )
                lines.append(
                    f"- {product.get('name', product_id)} product_id={product_id}: "
                    f"{'; '.join(variants[:12])}"
                )
        if self.confirmations:
            latest = self.confirmations[-1]
            lines.append(
                f"Latest explicit confirmation: action={latest.action}, "
                f"target={target_signature(latest.arguments)}"
            )
        if self.grounding_changes:
            lines.append(f"Last grounding changes: {self.grounding_changes[-8:]}")
        return "\n".join(lines) if lines else "No structured runtime state extracted yet."


def reconstruct_runtime_state(
    messages: Iterable[Any],
    action_bank: Optional[ActionBank] = None,
) -> RuntimeOntologyState:
    state = RuntimeOntologyState()
    pending_tool_calls: List[Dict[str, Any]] = []
    pending_confirmation: Optional[ConfirmationBinding] = None

    for message in messages:
        role = message_value(message, "role", "")
        content = message_value(message, "content")
        error = bool(message_value(message, "error", False))
        tool_calls = message_value(message, "tool_calls")
        raw_data = message_value(message, "raw_data", {}) or {}

        if role == "assistant":
            request = confirmation_request_from_raw_data(raw_data)
            if request is not None:
                pending_confirmation = request

        if role == "user" and pending_confirmation is not None:
            if is_explicit_confirmation(str(content or "")):
                state.confirmations.append(pending_confirmation)
                pending_confirmation = None
            elif is_explicit_rejection(str(content or "")):
                pending_confirmation = None

        if tool_calls:
            for tool_call in tool_calls:
                pending_tool_calls.append({
                    "name": message_value(tool_call, "name", ""),
                    "arguments": message_value(tool_call, "arguments", {}) or {},
                })
            continue

        if role != "tool":
            continue
        call = pending_tool_calls.pop(0) if pending_tool_calls else {"name": "", "arguments": {}}
        if error:
            continue
        result = parse_tool_content(content)
        record = SuccessfulToolCall(
            action=str(call.get("name") or ""),
            arguments=dict(call.get("arguments") or {}),
            result=result,
        )
        state.successful_tool_calls.append(record)
        schema = action_bank.get(record.action) if action_bank is not None else None
        if schema is not None and schema.action_kind == "mutate":
            state.executed_mutations.append(record)
        apply_tool_result(state, record)

    return state


def apply_tool_result(state: RuntimeOntologyState, record: SuccessfulToolCall) -> None:
    tool_name = record.action
    result = record.result
    if tool_name in {"find_user_id_by_email", "find_user_id_by_name_zip"} and isinstance(result, str):
        if result and "not found" not in result.lower() and "error" not in result.lower():
            state.user_id = result
        return
    if tool_name == "get_user_details" and isinstance(result, dict):
        user_id = str(result.get("user_id") or "")
        if user_id:
            state.user_id = user_id
            state.users[user_id] = result
        for payment_id, payment in (result.get("payment_methods") or {}).items():
            state.payment_methods[str(payment_id)] = payment
        return
    if tool_name == "get_order_details" and isinstance(result, dict):
        order_id = str(result.get("order_id") or record.arguments.get("order_id") or "")
        if order_id:
            state.orders[order_id] = result
        for payment in result.get("payment_history", []) or []:
            payment_id = payment.get("payment_method_id")
            if payment_id:
                state.payment_methods[str(payment_id)] = payment
        return
    if tool_name == "get_product_details" and isinstance(result, dict):
        product_id = str(result.get("product_id") or record.arguments.get("product_id") or "")
        if product_id:
            state.products[product_id] = result
        return
    if tool_name == "list_all_product_types" and isinstance(result, dict):
        state.product_type_ids.update({str(k): str(v) for k, v in result.items()})


def confirmation_request_from_raw_data(raw_data: Any) -> Optional[ConfirmationBinding]:
    if not isinstance(raw_data, dict):
        return None
    selected = raw_data.get("selected_candidate") or {}
    if selected.get("_repair_reason") == "CONFIRMATION_REQUIRED" and selected.get("_repair_for"):
        return ConfirmationBinding(
            action=str(selected["_repair_for"]),
            arguments=dict(selected.get("_repair_arguments") or {}),
        )
    gate = raw_data.get("ontology_gate") or {}
    if gate.get("selected_action") != "respond_to_user":
        return None
    for rejected in reversed(gate.get("rejected_candidates") or []):
        violations = rejected.get("violations") or []
        if any(str(v).startswith("CONFIRMATION_REQUIRED:") for v in violations):
            candidate = rejected.get("candidate") or {}
            return ConfirmationBinding(
                action=str(candidate.get("action") or ""),
                arguments=dict(candidate.get("arguments") or {}),
            )
    return None


def target_signature(arguments: Dict[str, Any]) -> str:
    target = {
        key: arguments[key]
        for key in ("user_id", "order_id", "item_ids", "new_item_ids", "payment_method_id", "reason", "address")
        if key in arguments
    }
    return stable_json(target)


def canonical_observed_id(value: Any, objects: Dict[str, Any]) -> str:
    text = str(value or "")
    if text in objects:
        return text
    stripped = text.lstrip("#").lower()
    for identifier in objects:
        if str(identifier).lstrip("#").lower() == stripped:
            return str(identifier)
    return ""


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def parse_tool_content(content: Any) -> Any:
    if not isinstance(content, str):
        return content
    text = content.strip()
    if not text:
        return text
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return content
    return content


def message_value(message: Any, key: str, default: Any = None) -> Any:
    if isinstance(message, dict):
        return message.get(key, default)
    return getattr(message, key, default)


def is_explicit_confirmation(text: str) -> bool:
    patterns = (
        r"\bi confirm\b",
        r"\bconfirmed\b",
        r"\bgo ahead\b",
        r"\bplease proceed\b",
        r"\byou may proceed\b",
        r"\bthat is correct\b",
        r"\bsounds good\b",
        r"\byes,\s*(cancel|return|exchange|modify|change|update|proceed)\b",
        r"\byes\s+(please\s+)?(cancel|return|exchange|modify|change|update|proceed)\b",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def is_explicit_rejection(text: str) -> bool:
    return bool(re.search(r"\b(no|do not|don't|stop|cancel that)\b", text, flags=re.IGNORECASE))
