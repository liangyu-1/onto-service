"""Task-to-ontology context builder for retail action planning."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from state_manager import DialogueState


class OntologyContextBuilder:
    """Build compact object-binding hints from task text, state, and the DB."""

    def build(self, task_info: str, state: DialogueState, db: Dict[str, Any]) -> str:
        text = task_info or ""
        lower = text.lower()
        lines: List[str] = []

        user_hints = self._user_hints(text, db)
        if user_hints:
            lines.append("Task-grounded user candidates:")
            lines.extend(f"- {hint}" for hint in user_hints[:3])

        order_hints = self._order_hints(text, state, db)
        if order_hints:
            lines.append("Task/state-grounded order candidates:")
            lines.extend(f"- {hint}" for hint in order_hints[:8])

        product_hints = self._product_hints(lower, state, db)
        if product_hints:
            lines.append("Task/state-grounded product and variant candidates:")
            lines.extend(f"- {hint}" for hint in product_hints[:10])

        update_hints = self._update_hints(lower, state)
        if update_hints:
            lines.append("Likely update action types:")
            lines.extend(f"- {hint}" for hint in update_hints)

        if not lines:
            return "No deterministic ontology grounding hints available yet."
        return "\n".join(lines)

    def _user_hints(self, text: str, db: Dict[str, Any]) -> List[str]:
        hints: List[str] = []
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
        if email_match:
            email = email_match.group(0)
            for uid, user in db.get("users", {}).items():
                if str(user.get("email", "")).lower() == email.lower():
                    hints.append(f"user_id={uid}, email={user.get('email')}, orders={user.get('orders', [])}")
                    return hints

        zip_matches = re.findall(r"\b\d{5}\b", text)
        for zip_code in zip_matches:
            for uid, user in db.get("users", {}).items():
                name = user.get("name", {})
                address = user.get("address", {})
                full_name = f"{name.get('first_name', '')} {name.get('last_name', '')}".strip()
                if str(address.get("zip", "")) == zip_code and full_name.lower() in text.lower():
                    hints.append(f"user_id={uid}, name={full_name}, zip={zip_code}, orders={user.get('orders', [])}")
        return hints

    def _order_hints(self, text: str, state: DialogueState, db: Dict[str, Any]) -> List[str]:
        hints: List[str] = []
        seen = set()
        for raw in re.findall(r"#?W\d{7}", text, flags=re.IGNORECASE):
            order_id = raw if raw.startswith("#") else f"#{raw}"
            order = db.get("orders", {}).get(order_id)
            if order:
                hints.append(self._format_order(order_id, order))
                seen.add(order_id)

        for order_id, order in state.cached_orders.items():
            if order_id not in seen:
                hints.append(self._format_order(order_id, order))
                seen.add(order_id)

        if state.user_id and state.user_id in db.get("users", {}):
            for order_id in db["users"][state.user_id].get("orders", []):
                if order_id in seen:
                    continue
                order = db.get("orders", {}).get(order_id)
                if order:
                    hints.append(self._format_order(order_id, order))
                    seen.add(order_id)
        return hints

    def _product_hints(self, text_lower: str, state: DialogueState, db: Dict[str, Any]) -> List[str]:
        hints: List[str] = []
        product_ids = set(state.cached_products.keys())
        for order in state.cached_orders.values():
            for item in order.get("items", []):
                product_id = item.get("product_id")
                if product_id:
                    product_ids.add(product_id)
        for product_id, product in db.get("products", {}).items():
            name = str(product.get("name", ""))
            if name and name.lower() in text_lower:
                product_ids.add(product_id)

        for product_id in sorted(product_ids):
            product = db.get("products", {}).get(product_id)
            if not product:
                continue
            variants = self._rank_variants(text_lower, product)
            hints.append(
                f"product_id={product_id}, name={product.get('name')}, "
                f"candidate_variants={variants[:5]}"
            )
        return hints

    def _rank_variants(self, text_lower: str, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for item_id, variant in product.get("variants", {}).items():
            if not variant.get("available", False):
                continue
            score = 0
            for value in variant.get("options", {}).values():
                value_text = str(value).lower()
                if value_text and value_text in text_lower:
                    score += 1
            scored.append((
                -score,
                {
                    "item_id": item_id,
                    "price": variant.get("price"),
                    "options": variant.get("options", {}),
                },
            ))
        scored.sort(key=lambda x: (x[0], x[1]["item_id"]))
        return [item for _, item in scored]

    def _update_hints(self, text_lower: str, state: DialogueState) -> List[str]:
        hints: List[str] = []
        if any(w in text_lower for w in ("return", "refund")):
            hints.append("return_delivered_order_items for delivered orders")
        if any(w in text_lower for w in ("exchange", "replace")):
            hints.append("exchange_delivered_order_items for delivered orders")
        if any(w in text_lower for w in ("cancel", "cancellation")):
            hints.append("cancel_pending_order for pending orders")
        if any(w in text_lower for w in ("address", "shipping")):
            hints.append("modify_pending_order_address or modify_user_address depending on target")
        if any(w in text_lower for w in ("change", "modify", "different", "color", "size", "capacity", "storage")):
            hints.append("modify_pending_order_items for pending orders")

        if state.user_confirmed:
            hints.append("confirmation is already available for exactly one next update")
        return hints

    def _format_order(self, order_id: str, order: Dict[str, Any]) -> str:
        items = []
        for item in order.get("items", []):
            items.append({
                "name": item.get("name"),
                "product_id": item.get("product_id"),
                "item_id": item.get("item_id"),
                "price": item.get("price"),
                "options": item.get("options", {}),
            })
        payment_methods = [
            payment.get("payment_method_id")
            for payment in order.get("payment_history", [])
            if payment.get("payment_method_id")
        ]
        return (
            f"order_id={order_id}, status={order.get('status')}, "
            f"address={order.get('address', {})}, payment_methods={payment_methods}, items={items}"
        )
