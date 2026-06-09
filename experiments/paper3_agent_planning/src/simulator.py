"""Simulator for retail domain tool execution."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from state_manager import DialogueState


class RetailSimulator:
    """Simulates retail tool execution on a copy of the database."""

    def __init__(self, db: Dict[str, Any]):
        # Deep copy to avoid mutating original
        self.db = copy.deepcopy(db)
        self.users = self.db["users"]
        self.products = self.db["products"]
        self.orders = self.db["orders"]

    def execute(self, action_name: str, arguments: Dict[str, Any], state: DialogueState) -> Any:
        """Execute an action and return the result."""
        method = getattr(self, action_name, None)
        if method is None:
            raise ValueError(f"Unknown action: {action_name}")
        return method(arguments, state)

    # --- Query actions (read-only) ---

    def find_user_id_by_email(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        email = arguments["email"]
        for uid, user in self.users.items():
            if user.get("email") == email:
                state.cached_users[uid] = copy.deepcopy(user)
                return uid
        raise ValueError(f"User with email {email} not found")

    def find_user_id_by_name_zip(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        first_name = arguments["first_name"]
        last_name = arguments["last_name"]
        zip_code = arguments["zip"]
        for uid, user in self.users.items():
            name = user.get("name", {})
            addr = user.get("address", {})
            if (str(name.get("first_name", "")).lower() == str(first_name).lower() and
                str(name.get("last_name", "")).lower() == str(last_name).lower() and
                addr.get("zip") == zip_code):
                state.cached_users[uid] = copy.deepcopy(user)
                return uid
        raise ValueError(f"User {first_name} {last_name} in {zip_code} not found")

    def get_user_details(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        user_id = arguments["user_id"]
        user = self.users.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        state.cached_users[user_id] = copy.deepcopy(user)
        return copy.deepcopy(user)

    def get_order_details(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def get_product_details(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        product_id = arguments["product_id"]
        product = self.products.get(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")
        state.cached_products[product_id] = copy.deepcopy(product)
        return copy.deepcopy(product)

    def get_item_details(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        item_id = arguments["item_id"]
        for pid, product in self.products.items():
            variants = product.get("variants", {})
            if item_id in variants:
                state.cached_products[pid] = copy.deepcopy(product)
                item = copy.deepcopy(variants[item_id])
                item["item_id"] = item_id
                item["product_id"] = pid
                item["name"] = product.get("name", "")
                return item
        raise ValueError(f"Item {item_id} not found")

    def list_all_product_types(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        return json.dumps([p["name"] for p in self.products.values()])

    def ask_for_confirmation(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        state.user_confirmed = True
        return {"confirmed": True}

    # --- Update actions (mutate DB) ---

    def cancel_pending_order(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        reason = arguments["reason"]
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order["status"] != "pending":
            raise ValueError("Non-pending order cannot be cancelled")
        order["status"] = "cancelled"
        order["cancellation_reason"] = reason
        # Refund logic simplified
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def modify_pending_order_address(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        new_address = self._address_from_arguments(arguments)
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order["status"] != "pending":
            raise ValueError("Non-pending order cannot be modified")
        order["address"] = new_address
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def modify_pending_order_items(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        item_ids = arguments["item_ids"]
        new_item_ids = arguments["new_item_ids"]
        payment_method_id = arguments["payment_method_id"]
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order["status"] != "pending":
            raise ValueError("Non-pending order cannot be modified")
        # Replace items
        for old_id, new_id in zip(item_ids, new_item_ids):
            for item in order["items"]:
                if item["item_id"] == old_id:
                    # Find new item details
                    for pid, product in self.products.items():
                        if new_id in product.get("variants", {}):
                            new_variant = product["variants"][new_id]
                            item["item_id"] = new_id
                            item["name"] = product["name"]
                            item["product_id"] = pid
                            item["price"] = new_variant["price"]
                            item["options"] = new_variant["options"]
                            break
                    break
        order["status"] = "pending (items modified)"
        order["payment_history"].append({
            "transaction_type": "item_modification",
            "payment_method_id": payment_method_id,
        })
        state.action_taken_on_order[order_id] = True
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def modify_pending_order_payment(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        payment_method_id = arguments["payment_method_id"]
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order["status"] != "pending":
            raise ValueError("Non-pending order cannot be modified")
        order["payment_history"].append({
            "transaction_type": "payment_update",
            "payment_method_id": payment_method_id,
        })
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def modify_user_address(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        user_id = arguments["user_id"]
        new_address = self._address_from_arguments(arguments)
        user = self.users.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        user["address"] = new_address
        state.cached_users[user_id] = copy.deepcopy(user)
        return copy.deepcopy(user)

    def return_delivered_order_items(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        item_ids = arguments["item_ids"]
        payment_method_id = arguments["payment_method_id"]
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order["status"] != "delivered":
            raise ValueError("Non-delivered order cannot be returned")
        if state.action_taken_on_order.get(order_id, False):
            raise ValueError("Return/exchange/modify can only be done once per order")
        order["status"] = "return requested"
        order["returned_items"] = item_ids
        order["return_payment_method"] = payment_method_id
        state.action_taken_on_order[order_id] = True
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def exchange_delivered_order_items(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        order_id = arguments["order_id"]
        item_ids = arguments["item_ids"]
        new_item_ids = arguments["new_item_ids"]
        payment_method_id = arguments["payment_method_id"]
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order["status"] != "delivered":
            raise ValueError("Non-delivered order cannot be exchanged")
        if state.action_taken_on_order.get(order_id, False):
            raise ValueError("Return/exchange/modify can only be done once per order")
        # Replace items
        for old_id, new_id in zip(item_ids, new_item_ids):
            for item in order["items"]:
                if item["item_id"] == old_id:
                    for pid, product in self.products.items():
                        if new_id in product.get("variants", {}):
                            new_variant = product["variants"][new_id]
                            item["item_id"] = new_id
                            item["name"] = product["name"]
                            item["product_id"] = pid
                            item["price"] = new_variant["price"]
                            item["options"] = new_variant["options"]
                            break
                    break
        order["status"] = "exchange requested"
        order["exchanged_items"] = item_ids
        order["exchange_payment_method"] = payment_method_id
        state.action_taken_on_order[order_id] = True
        state.cached_orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def transfer_to_human_agents(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        state.transfer_to_human = True
        return "Transferred to human agent."

    def finish_task(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        return {"finished": True}

    def calculate(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        # Simple expression calculator - for safety, just return the expression
        expression = arguments.get("expression", "")
        return f"Calculated: {expression}"

    def _address_from_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        address = arguments.get("address")
        if isinstance(address, dict):
            return copy.deepcopy(address)
        fields = ("address1", "address2", "city", "country", "state", "zip")
        flat = {field: arguments.get(field) for field in fields if field in arguments}
        if all(flat.get(field) for field in ("address1", "city", "state", "zip")):
            return flat
        raise ValueError("Address arguments must include address dict or flat address fields")


import json
