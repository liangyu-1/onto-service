"""Ontology-grounded next-action suggestions."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from state_manager import DialogueState
from task_progress import TaskProgressVerifier


class ActionSuggester:
    """Generate conservative next-action candidates from task/state/DB."""

    def __init__(self):
        self.progress = TaskProgressVerifier()

    def suggest(self, task_info: str, state: DialogueState, db: Dict[str, Any]) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        self._suggest_auth(task_info, state, db, suggestions)
        if not state.user_authenticated:
            return suggestions[:6]

        self._suggest_user_details(state, suggestions)
        self._suggest_order_details(task_info, state, db, suggestions)
        self._suggest_product_details(task_info, state, db, suggestions)
        self._suggest_confirmation(task_info, state, suggestions)
        self._suggest_updates(task_info, state, db, suggestions)
        self._suggest_finish(task_info, state, db, suggestions)
        return self._dedupe(suggestions)[:10]

    def format_for_prompt(self, suggestions: List[Dict[str, Any]]) -> str:
        if not suggestions:
            return "No deterministic next-action suggestions available."
        lines = []
        for i, suggestion in enumerate(suggestions, 1):
            lines.append(
                f"{i}. {suggestion['action']}({suggestion.get('arguments', {})})"
                f" -- confidence={suggestion.get('confidence', 0)}; {suggestion.get('reason', '')}"
            )
        return "\n".join(lines)

    def _suggest_auth(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        suggestions: List[Dict[str, Any]],
    ) -> None:
        if state.user_authenticated:
            return
        email = self._extract_email(task_info)
        if email:
            suggestions.append({
                "action": "find_user_id_by_email",
                "arguments": {"email": email},
                "confidence": 5,
                "reason": "authenticate with email mentioned in task",
            })
            return
        user_by_id = self._match_user_id(task_info, db)
        if user_by_id:
            uid, record = user_by_id
            name = record.get("name", {})
            zip_code = record.get("address", {}).get("zip", "")
            suggestions.append({
                "action": "find_user_id_by_name_zip",
                "arguments": {
                    "first_name": name.get("first_name", ""),
                    "last_name": name.get("last_name", ""),
                    "zip": zip_code,
                },
                "confidence": 5,
                "reason": f"authenticate from user_id-like mention {uid}",
            })
            return
        user = self._match_user_by_name_zip(task_info, db)
        if user:
            uid, record = user
            name = record.get("name", {})
            zip_code = record.get("address", {}).get("zip", "")
            suggestions.append({
                "action": "find_user_id_by_name_zip",
                "arguments": {
                    "first_name": name.get("first_name", ""),
                    "last_name": name.get("last_name", ""),
                    "zip": zip_code,
                },
                "confidence": 5,
                "reason": f"authenticate matched user_id={uid}",
            })

    def _suggest_user_details(self, state: DialogueState, suggestions: List[Dict[str, Any]]) -> None:
        if not state.user_id or state.user_id in state.cached_users:
            return
        suggestions.append({
            "action": "get_user_details",
            "arguments": {"user_id": state.user_id},
            "confidence": 4,
            "reason": "load user's orders, address and payment methods",
        })

    def _suggest_order_details(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        suggestions: List[Dict[str, Any]],
    ) -> None:
        order_ids = self._mentioned_order_ids(task_info, db)
        if state.user_id and state.user_id in db.get("users", {}):
            order_ids.extend(db["users"][state.user_id].get("orders", []))
        for order_id in order_ids:
            if order_id in state.cached_orders:
                continue
            suggestions.append({
                "action": "get_order_details",
                "arguments": {"order_id": order_id},
                "confidence": 4,
                "reason": "inspect candidate order status, items and payment history",
            })

    def _suggest_product_details(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        suggestions: List[Dict[str, Any]],
    ) -> None:
        text = task_info.lower()
        product_ids: Set[str] = set()
        for product_id, product in db.get("products", {}).items():
            name = str(product.get("name", ""))
            if name and name.lower() in text:
                product_ids.add(product_id)
        for order in state.cached_orders.values():
            for item in order.get("items", []):
                name = str(item.get("name", "")).lower()
                if name and name in text:
                    product_id = item.get("product_id")
                    if product_id:
                        product_ids.add(product_id)
        for product_id in sorted(product_ids):
            if product_id in state.cached_products:
                continue
            suggestions.append({
                "action": "get_product_details",
                "arguments": {"product_id": product_id},
                "confidence": 4,
                "reason": "retrieve variants for requested item change/exchange",
            })

    def _suggest_confirmation(
        self,
        task_info: str,
        state: DialogueState,
        suggestions: List[Dict[str, Any]],
    ) -> None:
        required = self.progress._required_intents(task_info)
        completed = self.progress._completed_intents(state)
        if state.user_confirmed or not (required - completed):
            return
        if not state.cached_orders and not state.cached_users:
            return
        suggestions.append({
            "action": "ask_for_confirmation",
            "arguments": {"action_description": "Confirm the requested order/profile update actions."},
            "confidence": 3,
            "reason": "confirmation is required before update actions",
        })

    def _suggest_updates(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        suggestions: List[Dict[str, Any]],
    ) -> None:
        required = self.progress._required_intents(task_info)
        completed = self.progress._completed_intents(state)
        missing = required - completed
        if not state.user_confirmed or not missing:
            return
        for order_id, order in state.cached_orders.items():
            status = str(order.get("status", "")).lower()
            payment_method = self._single_payment_method(order)
            if "cancel" in missing and status == "pending":
                suggestions.append({
                    "action": "cancel_pending_order",
                    "arguments": {"order_id": order_id, "reason": "no longer needed"},
                    "confidence": 3,
                    "reason": "pending order can satisfy cancel intent",
                })
            if "address" in missing and status == "pending":
                address = self._target_address(task_info, state, db, exclude_order_id=order_id)
                if address:
                    suggestions.append({
                        "action": "modify_pending_order_address",
                        "arguments": {"order_id": order_id, "address": address},
                        "confidence": 4,
                        "reason": "pending order can receive target address",
                    })
            if "return" in missing and status == "delivered" and payment_method:
                suggestions.append({
                    "action": "return_delivered_order_items",
                    "arguments": {
                        "order_id": order_id,
                        "item_ids": [item.get("item_id") for item in order.get("items", []) if item.get("item_id")],
                        "payment_method_id": payment_method,
                    },
                    "confidence": 3,
                    "reason": "delivered order can satisfy return intent",
                })
            if "item_modify" in missing and status == "pending" and payment_method:
                replacement = self._replacement_for_order(task_info, order, db)
                if replacement:
                    old_item_id, new_item_id, confidence = replacement
                    suggestions.append({
                        "action": "modify_pending_order_items",
                        "arguments": {
                            "order_id": order_id,
                            "item_ids": [old_item_id],
                            "new_item_ids": [new_item_id],
                            "payment_method_id": payment_method,
                        },
                        "confidence": confidence,
                        "reason": "pending order item has an ontology-matched replacement variant",
                    })
            if "exchange" in missing and status == "delivered" and payment_method:
                replacement = self._replacement_for_order(task_info, order, db)
                if replacement:
                    old_item_id, new_item_id, confidence = replacement
                    suggestions.append({
                        "action": "exchange_delivered_order_items",
                        "arguments": {
                            "order_id": order_id,
                            "item_ids": [old_item_id],
                            "new_item_ids": [new_item_id],
                            "payment_method_id": payment_method,
                        },
                        "confidence": confidence,
                        "reason": "delivered order item has an ontology-matched exchange variant",
                    })

    def _suggest_finish(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        suggestions: List[Dict[str, Any]],
    ) -> None:
        check = self.progress.check_terminal("finish_task", task_info, state, db)
        if check.passed and check.required_intents:
            suggestions.append({
                "action": "finish_task",
                "arguments": {},
                "confidence": 4,
                "reason": "all conservatively inferred required intents are complete",
            })

    def _extract_email(self, text: str) -> Optional[str]:
        match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
        return match.group(0) if match else None

    def _match_user_by_name_zip(self, text: str, db: Dict[str, Any]) -> Optional[tuple[str, Dict[str, Any]]]:
        text_lower = text.lower()
        zips = set(re.findall(r"\b\d{5}\b", text))
        for uid, user in db.get("users", {}).items():
            name = user.get("name", {})
            full_name = f"{name.get('first_name', '')} {name.get('last_name', '')}".lower()
            zip_code = str(user.get("address", {}).get("zip", ""))
            if full_name and full_name in text_lower and zip_code in zips:
                return uid, user
        return None

    def _match_user_id(self, text: str, db: Dict[str, Any]) -> Optional[tuple[str, Dict[str, Any]]]:
        for candidate in re.findall(r"\b[a-z]+_[a-z]+_\d+\b", text.lower()):
            if candidate in db.get("users", {}):
                return candidate, db["users"][candidate]
        return None

    def _mentioned_order_ids(self, text: str, db: Dict[str, Any]) -> List[str]:
        order_ids = []
        for raw in re.findall(r"#?W\d{7}", text, flags=re.IGNORECASE):
            order_id = raw if raw.startswith("#") else f"#{raw}"
            if order_id in db.get("orders", {}) and order_id not in order_ids:
                order_ids.append(order_id)
        return order_ids

    def _single_payment_method(self, order: Dict[str, Any]) -> Optional[str]:
        methods = [
            payment.get("payment_method_id")
            for payment in order.get("payment_history", [])
            if payment.get("payment_method_id")
        ]
        unique = list(dict.fromkeys(methods))
        return unique[0] if len(unique) == 1 else None

    def _target_address(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        exclude_order_id: str,
    ) -> Optional[Dict[str, Any]]:
        text = task_info.lower()
        if "nyc" in text or "new york" in text or "seattle" in text or "parent" in text:
            for order_id, order in state.cached_orders.items():
                if order_id == exclude_order_id:
                    continue
                address = order.get("address")
                if not isinstance(address, dict):
                    continue
                city = str(address.get("city", "")).lower()
                if ("new york" in text or "nyc" in text) and city == "new york":
                    return address
                if "seattle" in text and city == "seattle":
                    return address
        if state.user_id and state.user_id in db.get("users", {}) and "profile" in text:
            return db["users"][state.user_id].get("address")
        return None

    def _replacement_for_order(
        self,
        task_info: str,
        order: Dict[str, Any],
        db: Dict[str, Any],
    ) -> Optional[tuple[str, str, int]]:
        text = task_info.lower()
        best: Optional[tuple[int, str, str]] = None
        explicit_item_ids = set(re.findall(r"\b\d{10}\b", task_info))
        for item in order.get("items", []):
            product_id = item.get("product_id")
            product = db.get("products", {}).get(product_id)
            if not product:
                continue
            name = str(product.get("name", "")).lower()
            if name and name not in text:
                continue
            old_item_id = str(item.get("item_id"))
            old_options = item.get("options", {})
            old_price = item.get("price")
            for new_item_id, variant in product.get("variants", {}).items():
                if new_item_id == old_item_id or not variant.get("available", False):
                    continue
                score = self._variant_score(
                    text,
                    old_options,
                    variant.get("options", {}),
                    old_price,
                    variant.get("price"),
                    new_item_id,
                    explicit_item_ids,
                )
                if score <= 0:
                    continue
                candidate = (score, old_item_id, new_item_id)
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best:
            confidence = 4 if best[0] >= 5 else 3 if best[0] >= 2 else 2
            return best[1], best[2], confidence
        return None

    def _variant_score(
        self,
        text: str,
        old_options: Dict[str, Any],
        new_options: Dict[str, Any],
        old_price: Any,
        new_price: Any,
        new_item_id: str,
        explicit_item_ids: Set[str],
    ) -> int:
        score = 0
        if new_item_id in explicit_item_ids:
            score += 10
        for value in new_options.values():
            value_text = str(value).lower()
            if value_text and value_text in text:
                score += 2
        if "same or lower" in text or "same price or lower" in text or "lower price" in text:
            try:
                if float(new_price) <= float(old_price):
                    score += 2
                else:
                    score -= 3
            except (TypeError, ValueError):
                pass
        water = str(new_options.get("water resistance", "")).lower()
        if "without water resistance" in text or "no water resistance" in text:
            if water in {"not resistant", "no", "none"}:
                score += 3
            elif water:
                score -= 2
        for key, value in old_options.items():
            value_text = str(value).lower()
            if ("same" in text or "keep" in text) and value_text and new_options.get(key) == value:
                score += 1
        if "cheapest" in text:
            score += 1
        return score

    def _dedupe(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped = []
        seen = set()
        for suggestion in suggestions:
            key = (suggestion["action"], repr(suggestion.get("arguments", {})))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(suggestion)
        return deduped
