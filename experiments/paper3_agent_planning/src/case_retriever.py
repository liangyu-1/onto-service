"""Ontology-aware retrieval of solved train cases for in-context planning."""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Set, Tuple


STOPWORDS = {
    "the", "and", "you", "your", "want", "with", "that", "this", "from",
    "order", "orders", "agent", "please", "need", "have", "for", "but",
    "are", "not", "can", "will", "same", "other", "one", "all",
}


class CaseRetriever:
    """Retrieve train tasks whose ontology/action structure matches a test task."""

    def __init__(self, train_tasks: List[Any], db: Dict[str, Any], top_k: int = 3):
        self.train_tasks = train_tasks
        self.db = db
        self.top_k = top_k
        self.index = [self._encode_task(task) for task in train_tasks]

    def retrieve(self, task: Any) -> List[str]:
        return [record["text"] for record in self.retrieve_records(task)]

    def retrieve_records(self, task: Any) -> List[Dict[str, Any]]:
        query = self._encode_task(task, include_gold=False)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for encoded in self.index:
            score = self._score(query, encoded)
            if score > 0:
                scored.append((score, encoded))
        scored.sort(key=lambda item: (-item[0], item[1]["task_id"]))
        records = []
        for score, encoded in scored[: self.top_k]:
            records.append({
                "task_id": encoded["task_id"],
                "score": round(score, 4),
                "text": self._format_case(encoded),
                "action_names": encoded["action_names"],
            })
        return records

    def _encode_task(self, task: Any, include_gold: bool = True) -> Dict[str, Any]:
        text = self._task_info(task)
        text_lower = text.lower()
        gold_actions = []
        if include_gold:
            gold_actions = [
                {"action": ga["name"], "arguments": ga.get("arguments", {})}
                for ga in getattr(task, "gold_actions", [])
            ]
        action_names = [call["action"] for call in gold_actions]
        order_statuses = self._order_statuses(gold_actions)
        product_names = self._product_names(text_lower, gold_actions)
        tokens = self._tokens(text_lower)
        intents = self._intents(text_lower, action_names)
        return {
            "task_id": str(getattr(task, "task_id", "")),
            "text": text,
            "tokens": tokens,
            "intents": intents,
            "action_names": action_names,
            "action_set": set(action_names),
            "order_statuses": order_statuses,
            "product_names": product_names,
            "gold_actions": gold_actions,
        }

    def _score(self, query: Dict[str, Any], candidate: Dict[str, Any]) -> float:
        score = 0.0
        score += 5.0 * self._jaccard(query["intents"], candidate["intents"])
        score += 4.0 * self._jaccard(set(query["action_names"]), set(candidate["action_names"]))
        score += 3.0 * self._jaccard(query["product_names"], candidate["product_names"])
        score += 2.0 * self._jaccard(query["order_statuses"], candidate["order_statuses"])
        score += 1.0 * self._jaccard(query["tokens"], candidate["tokens"])

        # Multi-update tasks are structurally different from single-update tasks.
        q_updates = self._estimated_update_count(query)
        c_updates = sum(1 for name in candidate["action_names"] if self._is_update(name))
        if q_updates >= 2 and c_updates >= 2:
            score += 1.0
        elif q_updates == c_updates:
            score += 0.5
        return score

    def _estimated_update_count(self, encoded: Dict[str, Any]) -> int:
        if encoded["action_names"]:
            return sum(1 for name in encoded["action_names"] if self._is_update(name))
        intents = encoded["intents"]
        count = 0
        for intent in ("cancel", "return", "exchange", "address", "item_modify", "payment"):
            if intent in intents:
                count += 1
        return count

    def _format_case(self, encoded: Dict[str, Any]) -> str:
        actions = []
        for call in encoded["gold_actions"]:
            actions.append(
                f"{call['action']}({json.dumps(call.get('arguments', {}), ensure_ascii=False)})"
            )
        return (
            f"Retrieved train case task_id={encoded['task_id']}:\n"
            f"Task: {encoded['text']}\n"
            f"Ontology/action tags: intents={sorted(encoded['intents'])}, "
            f"products={sorted(encoded['product_names'])}, statuses={sorted(encoded['order_statuses'])}\n"
            f"Gold action trace:\n- " + "\n- ".join(actions)
        )

    def _task_info(self, task: Any) -> str:
        user_scenario = getattr(task, "user_scenario", {}) or {}
        instructions = user_scenario.get("instructions", {}) if isinstance(user_scenario, dict) else {}
        reason = instructions.get("reason_for_call", "")
        known = instructions.get("known_info", "")
        task_instructions = instructions.get("task_instructions", "")
        return "\n".join(part for part in (reason, known, task_instructions) if part)

    def _tokens(self, text_lower: str) -> Set[str]:
        tokens = set(re.findall(r"[a-z0-9]+", text_lower))
        return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}

    def _intents(self, text_lower: str, action_names: Iterable[str]) -> Set[str]:
        intents = set()
        keyword_map = {
            "cancel": ("cancel", "cancellation"),
            "return": ("return", "refund"),
            "exchange": ("exchange", "replace"),
            "address": ("address", "shipping"),
            "item_modify": ("modify", "change", "different", "color", "size", "capacity", "storage"),
            "payment": ("payment", "card", "paypal", "gift card"),
            "human": ("human", "agent", "escalat"),
        }
        for intent, keywords in keyword_map.items():
            if any(keyword in text_lower for keyword in keywords):
                intents.add(intent)
        for action in action_names:
            if action.startswith("modify_pending_order_address") or action == "modify_user_address":
                intents.add("address")
            elif action.startswith("modify_pending_order_items"):
                intents.add("item_modify")
            elif action.startswith("return"):
                intents.add("return")
            elif action.startswith("exchange"):
                intents.add("exchange")
            elif action.startswith("cancel"):
                intents.add("cancel")
        return intents

    def _order_statuses(self, gold_actions: List[Dict[str, Any]]) -> Set[str]:
        statuses = set()
        for call in gold_actions:
            order_id = call.get("arguments", {}).get("order_id")
            if order_id and order_id in self.db.get("orders", {}):
                status = self.db["orders"][order_id].get("status")
                if status:
                    statuses.add(str(status))
        return statuses

    def _product_names(self, text_lower: str, gold_actions: List[Dict[str, Any]]) -> Set[str]:
        names = set()
        for product in self.db.get("products", {}).values():
            name = str(product.get("name", ""))
            if name and name.lower() in text_lower:
                names.add(name)

        item_ids = []
        for call in gold_actions:
            args = call.get("arguments", {})
            for key in ("item_ids", "new_item_ids"):
                vals = args.get(key, [])
                if isinstance(vals, str):
                    vals = [vals]
                item_ids.extend(vals)
        item_to_product = self._item_to_product()
        for item_id in item_ids:
            product_name = item_to_product.get(str(item_id))
            if product_name:
                names.add(product_name)
        return names

    def _item_to_product(self) -> Dict[str, str]:
        mapping = {}
        for product in self.db.get("products", {}).values():
            name = product.get("name", "")
            for item_id in product.get("variants", {}).keys():
                mapping[item_id] = name
        return mapping

    def _jaccard(self, a: Set[str], b: Set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _is_update(self, action_name: str) -> bool:
        return action_name in {
            "modify_user_address",
            "modify_pending_order_address",
            "modify_pending_order_items",
            "modify_pending_order_payment",
            "cancel_pending_order",
            "return_delivered_order_items",
            "exchange_delivered_order_items",
        }
