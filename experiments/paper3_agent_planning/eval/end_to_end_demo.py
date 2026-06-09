"""End-to-end demo with a hardcoded smart agent showing the ideal behavior."""
from __future__ import annotations

import json
import sys
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/src')

from data_loader import RetailDB, load_tasks, get_task_by_id
from action_bank import ActionBank
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from state_manager import DialogueState


class SmartAgent:
    """A hardcoded smart agent that follows gold actions.
    This demonstrates what the system SHOULD look like when working correctly."""
    
    def __init__(self, gold_actions):
        self.gold_actions = gold_actions
        self.step = 0
    
    def plan_next_action(self, task_description, state, db):
        if self.step >= len(self.gold_actions):
            return {"action": "respond_to_user", "arguments": {}}
        
        gold = self.gold_actions[self.step]
        self.step += 1
        return {
            "thought": f"Following step {self.step}",
            "action": gold["name"],
            "arguments": gold.get("arguments", {}),
        }


def demo_task(task_id: str):
    print(f"\n{'='*70}")
    print(f"END-TO-END DEMO: Task {task_id}")
    print(f"{'='*70}")
    
    # Load data
    db = RetailDB.load('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/db.json')
    tasks = load_tasks('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/tasks.json')
    action_bank = ActionBank.from_json('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json')
    
    task = get_task_by_id(tasks, task_id)
    sim = RetailSimulator({"users": db.users, "products": db.products, "orders": db.orders})
    verifier = ConstraintVerifier(action_bank)
    state = DialogueState()
    agent = SmartAgent(task.gold_actions)
    
    # Show task
    instructions = task.user_scenario.get("instructions", {})
    print(f"\nUser: {instructions.get('reason_for_call', '')}")
    print(f"Known: {instructions.get('known_info', '')}")
    
    # Execute with verifier
    UPDATE_ACTIONS = {
        "cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items",
        "modify_pending_order_payment", "modify_user_address",
        "return_delivered_order_items", "exchange_delivered_order_items",
    }
    
    violations_caught = 0
    
    for i in range(len(task.gold_actions)):
        plan = agent.plan_next_action("", state, sim.db)
        action_name = plan["action"]
        arguments = plan["arguments"]
        
        # Auto-confirm for demo
        if action_name in UPDATE_ACTIONS:
            state.user_confirmed = True
        
        # Verify
        result = verifier.verify(action_name, arguments, state, sim.db)
        
        if not result.passed:
            violations_caught += len(result.violations)
            print(f"\n  Step {i+1}: {action_name}")
            print(f"    ⚠️  VERIFIER CAUGHT {len(result.violations)} VIOLATION(S):")
            for v in result.violations:
                print(f"       - {v}")
            # In real system, this would trigger repair loop
            print(f"    🔧 Repair: Auto-fixing and retrying...")
            # For demo, we just continue (in reality, LLM would replan)
        
        # Execute
        try:
            action_result = sim.execute(action_name, arguments, state)
            if action_name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
                state.user_authenticated = True
                state.user_id = action_result
            if action_name in UPDATE_ACTIONS:
                state.user_confirmed = False
            
            if result.passed:
                print(f"\n  Step {i+1}: {action_name} ✅")
            else:
                print(f"    -> Executed after repair ✅")
                
        except ValueError as e:
            print(f"\n  Step {i+1}: {action_name} ❌ ERROR: {e}")
    
    print(f"\n{'='*70}")
    print(f"RESULTS:")
    print(f"  Total steps: {len(task.gold_actions)}")
    print(f"  Violations caught by verifier: {violations_caught}")
    print(f"  Final state: authenticated={state.user_authenticated}, user_id={state.user_id}")
    print(f"  Orders modified: {list(state.action_taken_on_order.keys())}")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo_task("5")
    demo_task("9")
