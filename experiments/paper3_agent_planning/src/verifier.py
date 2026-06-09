"""Constraint verifier for action execution."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from action_bank import ActionBank, ActionSchema
from state_manager import DialogueState


class VerificationResult:
    def __init__(self, passed: bool, violations: List[str] = None):
        self.passed = passed
        self.violations = violations or []

    def __bool__(self):
        return self.passed


class ConstraintVerifier:
    """Verifies if an action can be executed given current state."""

    def __init__(self, action_bank: ActionBank):
        self.action_bank = action_bank

    def verify(self, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> VerificationResult:
        """Check all preconditions and constraints for an action."""
        schema = self.action_bank.get(action_name)
        if schema is None:
            return VerificationResult(False, [f"Unknown action: {action_name}"])

        violations = []

        # Check required parameters declared by the action ontology.
        for param_name in schema.parameters:
            if param_name not in arguments or arguments.get(param_name) in (None, "", []):
                violations.append(f"ARGUMENT: Missing required parameter '{param_name}'")

        # Check for duplicate actions (same action with same args already succeeded)
        dup = self._check_duplicate(action_name, arguments, state)
        if dup:
            violations.append(f"DUPLICATE: {dup}")

        # Check preconditions
        for precond in schema.preconditions:
            ok, msg = self._check_precondition(precond, arguments, state, db)
            if not ok:
                violations.append(f"PRECONDITION: {msg}")

        # Check constraints
        for constraint in schema.constraints:
            ok, msg = self._check_constraint(constraint, arguments, state, db)
            if not ok:
                violations.append(f"CONSTRAINT: {msg}")

        return VerificationResult(len(violations) == 0, violations)

    def _check_duplicate(self, action_name: str, arguments: Dict[str, Any], state: DialogueState) -> str:
        """Check if this exact action was already executed successfully."""
        for h in state.history:
            if h.get('action') != action_name:
                continue
            # Compare arguments
            prev_args = h.get('arguments', {})
            if prev_args == arguments:
                result = h.get('result', {})
                if self._is_successful_result(result):
                    return f"Action {action_name} with same arguments already executed successfully. Use the result from history instead."
        return ""

    def _is_successful_result(self, result: Any) -> bool:
        if isinstance(result, dict):
            return 'error' not in result and 'verifier_rejected' not in result
        return result is not None

    def _check_precondition(self, precond: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluate a precondition string."""
        precond = precond.strip()

        # Handle: order.status == 'pending'
        if ".status ==" in precond:
            parts = precond.replace("'", "").replace('"', "").split("==")
            obj_ref = parts[0].strip()  # e.g., "order.status"
            expected = parts[1].strip()  # e.g., "pending"
            
            # Extract object type and field
            obj_type, field = obj_ref.split(".")
            
            # Get the object from arguments or state cache
            obj_id = None
            if obj_type == "order":
                obj_id = arguments.get("order_id")
                if obj_id and obj_id in state.cached_orders:
                    actual = state.cached_orders[obj_id].get("status", "")
                elif obj_id and obj_id in db.get("orders", {}):
                    actual = db["orders"][obj_id].get("status", "")
                else:
                    return False, f"Order {obj_id} not found in cache or DB"
            else:
                return True, ""  # Skip unknown object types for now
            
            if actual != expected:
                return False, f"{obj_ref} is '{actual}', expected '{expected}'"
            return True, ""

        # Handle: len(item_ids) == len(new_item_ids)
        if precond == "len(item_ids) == len(new_item_ids)":
            item_ids = arguments.get("item_ids")
            new_item_ids = arguments.get("new_item_ids")
            if not isinstance(item_ids, list) or not isinstance(new_item_ids, list):
                return False, "item_ids and new_item_ids must be lists"
            if len(item_ids) != len(new_item_ids):
                return False, "len(item_ids) != len(new_item_ids)"
            return True, ""

        # Handle: reason in ['a', 'b']
        if " in [" in precond:
            parts = precond.split(" in ")
            param_name = parts[0].strip()
            allowed_str = parts[1].strip()
            # Parse list
            allowed = [x.strip().strip("'\"").strip() for x in allowed_str.strip("[]").split(",")]
            actual = arguments.get(param_name, "")
            if actual not in allowed:
                return False, f"{param_name}='{actual}' not in {allowed}"
            return True, ""

        # Handle: user_authenticated == true
        if "user_authenticated" in precond:
            if not state.user_authenticated:
                return False, "User not authenticated"
            return True, ""

        # Handle: user_confirmed == true
        if "user_confirmed" in precond:
            if not state.user_confirmed:
                return False, "User did not confirm action"
            return True, ""

        # Default: pass (unknown preconditions are warnings)
        return True, ""

    def _check_constraint(self, constraint: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluate a policy constraint."""
        constraint = constraint.strip()

        if "user_authenticated" in constraint:
            if not state.user_authenticated:
                return False, "User not authenticated"
            return True, ""

        if "user_confirmed" in constraint:
            if not state.user_confirmed:
                return False, "User did not confirm action"
            return True, ""

        if "action_taken_on_order" in constraint:
            order_id = arguments.get("order_id")
            if order_id and state.action_taken_on_order.get(order_id, False):
                return False, f"Action already taken on order {order_id}"
            return True, ""

        if constraint == "referential_integrity == true":
            return self._check_referential_integrity(arguments, state, db)

        # Default: pass
        return True, ""

    def _check_referential_integrity(self, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> Tuple[bool, str]:
        order_id = arguments.get("order_id")
        order = None
        if order_id:
            order = state.cached_orders.get(order_id) or db.get("orders", {}).get(order_id)
            if order is None:
                return False, f"Order {order_id} not found"

        item_ids = arguments.get("item_ids")
        if item_ids and order:
            order_items = {str(item.get("item_id")) for item in order.get("items", [])}
            missing = [item_id for item_id in item_ids if str(item_id) not in order_items]
            if missing:
                return False, f"Items {missing} are not in order {order_id}"

        new_item_ids = arguments.get("new_item_ids")
        if new_item_ids:
            known_variants = {
                item_id
                for product in db.get("products", {}).values()
                for item_id in product.get("variants", {}).keys()
            }
            missing = [item_id for item_id in new_item_ids if str(item_id) not in known_variants]
            if missing:
                return False, f"Replacement items {missing} do not exist"

        payment_method_id = arguments.get("payment_method_id")
        if payment_method_id and order:
            order_methods = {
                payment.get("payment_method_id")
                for payment in order.get("payment_history", [])
                if payment.get("payment_method_id")
            }
            user_methods = set()
            if state.user_id and state.user_id in db.get("users", {}):
                user_methods = set(db["users"][state.user_id].get("payment_methods", {}).keys())
            if payment_method_id not in order_methods and payment_method_id not in user_methods:
                return False, f"Payment method {payment_method_id} is not available for the authenticated user/order"

        return True, ""
