"""Heuristic "LLM" that follows simple rules for pipeline validation.
This simulates a naive agent that makes common mistakes."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from state_manager import DialogueState


class HeuristicLLM:
    """A rule-based agent that simulates common LLM mistakes for comparison."""

    def __init__(self, mistake_rate: float = 0.3):
        self.mistake_rate = mistake_rate
        self.step = 0
        self.authenticated = False
        self.has_order = False
        self.has_products = False
        self.confirmed = False
        self.order_id = None
        self.user_id = None
        self.task_type = None

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Return a heuristic action based on current state."""
        task = self._parse_task(user_prompt)
        self._update_state_from_history(user_prompt)
        self.step += 1

        # Determine task type
        if self.task_type is None:
            task_lower = task.lower()
            if "cancel" in task_lower:
                self.task_type = "cancel"
            elif "return" in task_lower:
                self.task_type = "return"
            elif "exchange" in task_lower:
                self.task_type = "exchange"
            elif "modify" in task_lower:
                self.task_type = "modify"
            else:
                self.task_type = "query"

        # Extract order ID if not known
        if self.order_id is None:
            self.order_id = self._extract_order_id(task)

        # Extract user info if not known
        if self.user_id is None:
            name_zip = self._extract_name_zip(task)
            if name_zip:
                self.user_id = name_zip

        # Step 1: Authenticate
        if not self.authenticated:
            if self._make_mistake():
                return {
                    "thought": "I'll look up the order directly.",
                    "action": "get_order_details",
                    "arguments": {"order_id": self.order_id or "#W0000000"},
                }
            self.authenticated = True
            return {
                "thought": "I need to authenticate the user first.",
                "action": "find_user_id_by_name_zip",
                "arguments": self.user_id or {"first_name": "Unknown", "last_name": "User", "zip": "00000"},
            }

        # Step 2: Get user details
        if self.authenticated and not self.has_order and self.step <= 3:
            self.has_order = True
            return {
                "thought": "Now I'll get the order details.",
                "action": "get_order_details",
                "arguments": {"order_id": self.order_id or "#W0000000"},
            }

        # Step 3: Get product details (for exchange)
        if self.task_type == "exchange" and not self.has_products and self.step <= 5:
            self.has_products = True
            # Extract product IDs from task if possible
            product_ids = self._extract_product_ids(task)
            if product_ids and len(product_ids) >= 1:
                return {
                    "thought": "I need to check product details.",
                    "action": "get_product_details",
                    "arguments": {"product_id": product_ids[0]},
                }

        # Step 4: Execute the main action
        if self.task_type == "cancel":
            if not self.confirmed:
                if self._make_mistake():
                    return {
                        "thought": "I'll cancel the order now.",
                        "action": "cancel_pending_order",
                        "arguments": {
                            "order_id": self.order_id,
                            "reason": "no longer needed",
                        },
                    }
                self.confirmed = True
                return {
                    "thought": "I need user confirmation before canceling.",
                    "action": "ask_for_confirmation",
                    "arguments": {},
                }
            return {
                "thought": "Canceling the order.",
                "action": "cancel_pending_order",
                "arguments": {
                    "order_id": self.order_id,
                    "reason": "no longer needed",
                },
            }

        elif self.task_type == "return":
            if not self.confirmed:
                if self._make_mistake():
                    return {
                        "thought": "I'll return the items.",
                        "action": "return_delivered_order_items",
                        "arguments": {
                            "order_id": self.order_id,
                            "item_ids": ["item_id"],
                            "payment_method_id": "payment_id",
                        },
                    }
                self.confirmed = True
                return {
                    "thought": "I need user confirmation.",
                    "action": "ask_for_confirmation",
                    "arguments": {},
                }
            return {
                "thought": "Returning the items.",
                "action": "return_delivered_order_items",
                "arguments": {
                    "order_id": self.order_id,
                    "item_ids": ["item_id"],
                    "payment_method_id": "payment_id",
                },
            }

        elif self.task_type == "exchange":
            if not self.confirmed:
                if self._make_mistake():
                    return {
                        "thought": "I'll exchange the items.",
                        "action": "exchange_delivered_order_items",
                        "arguments": {
                            "order_id": self.order_id,
                            "item_ids": ["item_id"],
                            "new_item_ids": ["new_item_id"],
                            "payment_method_id": "payment_id",
                        },
                    }
                self.confirmed = True
                return {
                    "thought": "I need user confirmation.",
                    "action": "ask_for_confirmation",
                    "arguments": {},
                }
            return {
                "thought": "Exchanging the items.",
                "action": "exchange_delivered_order_items",
                "arguments": {
                    "order_id": self.order_id,
                    "item_ids": ["item_id"],
                    "new_item_ids": ["new_item_id"],
                    "payment_method_id": "payment_id",
                },
            }

        # Default: respond to user
        return {
            "thought": "I'm done with this task.",
            "action": "respond_to_user",
            "arguments": {"message": "How else can I help you?"},
        }

    def _make_mistake(self) -> bool:
        import random
        return random.random() < self.mistake_rate

    def _update_state_from_history(self, prompt: str) -> None:
        """Update internal state from conversation history."""
        if "find_user_id_by_name_zip" in prompt or "find_user_id_by_email" in prompt:
            self.authenticated = True
        if "get_order_details" in prompt:
            self.has_order = True
        if "get_product_details" in prompt:
            self.has_products = True
        if "ask_for_confirmation" in prompt:
            self.confirmed = True

    def _parse_task(self, prompt: str) -> str:
        """Extract task description."""
        if "Reason for call:" in prompt:
            return prompt.split("Reason for call:")[1].split("\n")[0]
        return ""

    def _extract_order_id(self, task: str) -> Optional[str]:
        """Extract order ID from task text."""
        match = re.search(r'#W\d+', task)
        return match.group(0) if match else None

    def _extract_name_zip(self, task: str) -> Optional[Dict[str, str]]:
        """Extract name and zip from task text."""
        match = re.search(r'You are ([\w\s]+) in zip code (\d+)', task)
        if match:
            name = match.group(1).strip()
            zip_code = match.group(2)
            parts = name.split()
            if len(parts) >= 2:
                return {"first_name": parts[0], "last_name": parts[-1], "zip": zip_code}
        return None

    def _extract_product_ids(self, task: str) -> List[str]:
        """Extract product IDs from task text."""
        # Look for product IDs (10-digit numbers)
        matches = re.findall(r'\b\d{10}\b', task)
        return matches
