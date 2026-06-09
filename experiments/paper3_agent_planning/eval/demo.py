"""Demo script showing the system working end-to-end."""
from __future__ import annotations

import json
import sys
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/src')

from data_loader import RetailDB, load_tasks, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from simulator import RetailSimulator
from verifier import ConstraintVerifier


def demo_task(task_id: str):
    """Demonstrate the system on a single task."""
    print(f"\n{'='*60}")
    print(f"DEMO: Task {task_id}")
    print(f"{'='*60}")

    # Load data
    db = RetailDB.load('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/db.json')
    tasks = load_tasks('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/tasks.json')
    action_bank = ActionBank.from_json('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json')

    task = get_task_by_id(tasks, task_id)
    sim = RetailSimulator({"users": db.users, "products": db.products, "orders": db.orders})
    verifier = ConstraintVerifier(action_bank)
    state = DialogueState()

    # Show task
    instructions = task.user_scenario.get("instructions", {})
    print(f"\nUser: {instructions.get('reason_for_call', '')}")
    print(f"Known: {instructions.get('known_info', '')}")

    # Show gold actions
    print(f"\nGold actions ({len(task.gold_actions)}):")
    for i, a in enumerate(task.gold_actions):
        print(f"  {i+1}. {a['name']}({json.dumps(a.get('arguments', {}))})")

    # Step through with verifier
    print(f"\nExecution with verifier:")
    UPDATE_ACTIONS = {
        "cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items",
        "modify_pending_order_payment", "modify_user_address",
        "return_delivered_order_items", "exchange_delivered_order_items",
    }

    for i, action in enumerate(task.gold_actions):
        name = action['name']
        args = action.get('arguments', {})

        # Auto-confirm for demo
        if name in UPDATE_ACTIONS:
            state.user_confirmed = True

        # Verify
        result = verifier.verify(name, args, state, sim.db)
        status = "✓ PASS" if result.passed else "✗ FAIL"

        # Execute
        try:
            res = sim.execute(name, args, state)
            exec_status = "✓"
            if name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
                state.user_authenticated = True
                state.user_id = res
            if name in UPDATE_ACTIONS:
                state.user_confirmed = False
        except Exception as e:
            exec_status = f"✗ {e}"

        print(f"  Step {i+1}: {name} -> {status} | Exec: {exec_status}")
        if not result.passed:
            for v in result.violations:
                print(f"           Violation: {v}")

    print(f"\nFinal state:")
    print(f"  Authenticated: {state.user_authenticated}")
    print(f"  User ID: {state.user_id}")
    print(f"  Cached orders: {list(state.cached_orders.keys())}")
    print(f"  Action taken on orders: {state.action_taken_on_order}")


if __name__ == "__main__":
    demo_task("5")
    demo_task("9")
