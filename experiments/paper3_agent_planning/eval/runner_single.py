"""Run a single task for debugging."""
import sys
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/src')

from data_loader import RetailDB, load_tasks, get_task_by_id
from action_bank import ActionBank
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from state_manager import DialogueState
from baselines.rule_baseline import RuleBaselinePlanner
from metrics import EvaluationResult, compute_action_accuracy

db = RetailDB.load('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/db.json')
action_bank = ActionBank.from_json('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json')
tasks = load_tasks('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/tasks.json')

task = get_task_by_id(tasks, '9')
print(f"Task 9: {len(task.gold_actions)} gold actions")

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

instructions = task.user_scenario.get("instructions", {})
task_desc = instructions.get("reason_for_call", "")
known_info = instructions.get("known_info", "")
unknown_info = instructions.get("unknown_info", "")
full_desc = f"Reason for call: {task_desc}\nKnown info: {known_info}\nUnknown info: {unknown_info}"

for step in range(20):
    plan = planner.plan_next_action(full_desc, state, sim.db)
    action_name = plan.get("action", "")
    args = plan.get("arguments", {})
    
    predicted_actions.append({"action": action_name, "arguments": args})
    
    if action_name in ("respond_to_user", "ask_for_confirmation"):
        break
    if action_name == "transfer_to_human_agents":
        break
    
    if action_name in UPDATE_ACTIONS:
        state.user_confirmed = True
    
    v_result = verifier.verify(action_name, args, state, sim.db)
    if not v_result.passed:
        result.constraint_violations += len(v_result.violations)
        print(f"Step {step+1}: {action_name} REJECTED - {v_result.violations}")
        continue
    
    try:
        res = sim.execute(action_name, args, state)
        if action_name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
            state.user_authenticated = True
            state.user_id = res
        if action_name in UPDATE_ACTIONS:
            state.user_confirmed = False
    except Exception as e:
        result.invalid_actions += 1
    
    if len(predicted_actions) >= len(task.gold_actions):
        break

result.predicted_actions = predicted_actions
result.action_accuracy = compute_action_accuracy(predicted_actions, task.gold_actions)
result.success = result.action_accuracy >= 1.0 and result.constraint_violations == 0 and result.invalid_actions == 0

print(f"Accuracy: {result.action_accuracy:.2%}, Success: {result.success}, Violations: {result.constraint_violations}, Invalid: {result.invalid_actions}")
