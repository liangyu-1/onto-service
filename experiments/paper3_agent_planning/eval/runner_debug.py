"""Debug runner for a single task."""
import sys
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/src')

from data_loader import RetailDB, load_tasks, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from baselines.rule_baseline import RuleBaselinePlanner
from metrics import EvaluationResult, compute_action_accuracy

db = RetailDB.load('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/db.json')
action_bank = ActionBank.from_json('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json')

tasks = load_tasks('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/tasks.json')
task = get_task_by_id(tasks, '9')

sim = RetailSimulator({"users": db.users, "products": db.products, "orders": db.orders})
verifier = ConstraintVerifier(action_bank)
state = DialogueState()
planner = RuleBaselinePlanner(task.gold_actions)

UPDATE_ACTIONS = {
    "cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items",
    "modify_pending_order_payment", "modify_user_address",
    "return_delivered_order_items", "exchange_delivered_order_items",
}

predicted_actions = []
result = EvaluationResult(task_id='9', gold_actions=task.gold_actions)

for step in range(20):
    plan = planner.plan_next_action("", state, sim.db)
    action_name = plan.get("action", "")
    args = plan.get("arguments", {})
    
    predicted_actions.append({"action": action_name, "arguments": args})
    print(f"Step {step+1}: {action_name} {args}")
    
    if action_name in ("respond_to_user", "ask_for_confirmation"):
        print("  -> Terminal action, breaking")
        break
    if action_name == "transfer_to_human_agents":
        break
    
    if action_name in UPDATE_ACTIONS:
        state.user_confirmed = True
        print(f"  -> Auto-confirmed")
    
    v_result = verifier.verify(action_name, args, state, sim.db)
    if not v_result.passed:
        result.constraint_violations += len(v_result.violations)
        print(f"  -> REJECTED: {v_result.violations}")
        continue
    print(f"  -> Verified OK")
    
    try:
        res = sim.execute(action_name, args, state)
        if action_name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
            state.user_authenticated = True
            state.user_id = res
        if action_name in UPDATE_ACTIONS:
            state.user_confirmed = False
        print(f"  -> Executed OK")
    except Exception as e:
        result.invalid_actions += 1
        print(f"  -> ERROR: {e}")
    
    print(f"  -> predicted={len(predicted_actions)}, gold={len(task.gold_actions)}")
    if len(predicted_actions) >= len(task.gold_actions):
        print("  -> Reached gold count, breaking")
        break

result.predicted_actions = predicted_actions
result.action_accuracy = compute_action_accuracy(predicted_actions, task.gold_actions)
result.success = result.action_accuracy >= 1.0 and result.constraint_violations == 0 and result.invalid_actions == 0

print(f"\nFinal: accuracy={result.action_accuracy:.2%}, success={result.success}, violations={result.constraint_violations}, invalid={result.invalid_actions}")
