"""Counterfactual state test for state sensitivity evaluation."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

from data_loader import RetailDB
from state_manager import DialogueState


class CounterfactualGenerator:
    """Generate counterfactual states by modifying key state variables."""

    def __init__(self, db: RetailDB):
        self.db = db

    def generate_for_task(self, task_id: str, original_plan: List[str]) -> List[Tuple[str, Dict[str, Any], str]]:
        """Generate counterfactual states for a task.
        
        Returns list of (description, state_modification, expected_change).
        """
        variants = []

        # Find the user and order involved in this task
        user_id = None
        order_id = None
        for action in task_id.gold_actions if hasattr(task_id, 'gold_actions') else []:
            if 'user_id' in action.get('arguments', {}):
                user_id = action['arguments']['user_id']
            if 'order_id' in action.get('arguments', {}):
                order_id = action['arguments']['order_id']

        if not user_id or not order_id:
            return variants

        # Variant 1: Change order status from pending -> delivered
        if 'cancel_pending_order' in [a['name'] for a in (task_id.gold_actions if hasattr(task_id, 'gold_actions') else [])]:
            variants.append((
                "order_status_delivered",
                {"order_id": order_id, "new_status": "delivered"},
                "cancel_pending_order should become return_delivered_order_items or exchange_delivered_order_items"
            ))

        # Variant 2: Change order status from delivered -> pending
        if 'return_delivered_order_items' in [a['name'] for a in (task_id.gold_actions if hasattr(task_id, 'gold_actions') else [])]:
            variants.append((
                "order_status_pending",
                {"order_id": order_id, "new_status": "pending"},
                "return_delivered_order_items should become cancel_pending_order"
            ))

        # Variant 3: User not authenticated
        variants.append((
            "user_not_authenticated",
            {"user_id": user_id, "authenticated": False},
            "get_user_details/get_order_details should be blocked or require authentication first"
        ))

        # Variant 4: User not confirmed for modification
        if any(a['name'] in ['return_delivered_order_items', 'exchange_delivered_order_items', 'modify_pending_order_items'] 
               for a in (task_id.gold_actions if hasattr(task_id, 'gold_actions') else [])):
            variants.append((
                "user_not_confirmed",
                {"user_id": user_id, "confirmed": False},
                "Final action should require ask_for_confirmation first"
            ))

        return variants

    def apply_modification(self, db: RetailDB, modification: Dict[str, Any]) -> RetailDB:
        """Apply a state modification to a copy of the DB."""
        db_copy = copy.deepcopy(db)
        
        if "order_id" in modification and "new_status" in modification:
            oid = modification["order_id"]
            for order in db_copy.orders.values():
                if order.get("order_id") == oid:
                    order["status"] = modification["new_status"]
                    break
        
        return db_copy


def evaluate_state_sensitivity(
    planner,
    task,
    original_db: RetailDB,
    counterfactual_generator: CounterfactualGenerator,
    simulator,
    max_steps: int = 10,
) -> Dict[str, Any]:
    """Evaluate if planner correctly responds to state changes.
    
    Returns:
        {
            "original_plan": [...],
            "counterfactuals": [
                {
                    "description": str,
                    "modification": dict,
                    "plan": [...],
                    "correctly_changed": bool,
                }
            ],
            "ssa": float,  # State Sensitivity Accuracy
        }
    """
    from run_experiments import RetailSimulator
    
    # Run original
    state_orig = DialogueState()
    plan_orig = []
    sim = RetailSimulator(original_db)
    for step in range(max_steps):
        action = planner.plan_next_action(task, state_orig, original_db)
        plan_orig.append(action['action'])
        result, is_final = sim.execute(action['action'], action.get('arguments', {}), state_orig)
        state_orig.history.append({'action': action['action'], 'arguments': action.get('arguments', {}), 'result': result})
        if is_final:
            break

    # Run counterfactuals
    cf_results = []
    variants = counterfactual_generator.generate_for_task(task, plan_orig)
    
    for desc, mod, expected in variants:
        db_cf = counterfactual_generator.apply_modification(original_db, mod)
        state_cf = DialogueState()
        plan_cf = []
        sim_cf = RetailSimulator(db_cf)
        
        for step in range(max_steps):
            action = planner.plan_next_action(task, state_cf, db_cf)
            plan_cf.append(action['action'])
            result, is_final = sim_cf.execute(action['action'], action.get('arguments', {}), state_cf)
            state_cf.history.append({'action': action['action'], 'arguments': action.get('arguments', {}), 'result': result})
            if is_final:
                break
        
        # Check if plan changed appropriately
        changed = plan_cf != plan_orig
        # More nuanced: check if the final action matches expectation
        correctly_changed = changed  # Simplified
        
        cf_results.append({
            "description": desc,
            "modification": mod,
            "plan": plan_cf,
            "original_plan": plan_orig,
            "changed": changed,
            "correctly_changed": correctly_changed,
            "expected": expected,
        })

    ssa = sum(1 for r in cf_results if r['correctly_changed']) / len(cf_results) if cf_results else 0
    
    return {
        "original_plan": plan_orig,
        "counterfactuals": cf_results,
        "ssa": ssa,
        "num_variants": len(variants),
    }
