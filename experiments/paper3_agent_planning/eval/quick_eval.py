"""Quick evaluation with real LLM on a small subset."""
from __future__ import annotations

import json
import sys
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/src')
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/eval')

from data_loader import RetailDB, load_tasks, load_split, get_task_by_id
from action_bank import ActionBank
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from state_manager import DialogueState
from llm_client import create_llm_client
from baselines.schema_baseline import SchemaPlanner
from metrics import EvaluationResult, compute_action_accuracy, aggregate_results

def run_eval(num_tasks: int = 5):
    db = RetailDB.load('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/db.json')
    tasks = load_tasks('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/tasks.json')
    split_data = load_split('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/split_tasks.json')
    action_bank = ActionBank.from_json('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json')

    llm = create_llm_client()
    verifier = ConstraintVerifier(action_bank)
    planner = SchemaPlanner(llm, action_bank)

    test_ids = split_data.get('test', [])[:num_tasks]
    results_no_verifier = []
    results_with_verifier = []

    for task_id in test_ids:
        task = get_task_by_id(tasks, task_id)
        
        # Run without verifier
        result_no_v = run_single_task(task, planner, verifier, use_verifier=False)
        results_no_verifier.append(result_no_v)
        
        # Run with verifier
        result_v = run_single_task(task, planner, verifier, use_verifier=True)
        results_with_verifier.append(result_v)
        
        print(f"Task {task_id}: no_v={result_no_v.action_accuracy:.0%} (inv={result_no_v.invalid_actions}) | v={result_v.action_accuracy:.0%} (inv={result_v.invalid_actions}, cv={result_v.constraint_violations})")

    print("\n=== WITHOUT VERIFIER ===")
    print(json.dumps(aggregate_results(results_no_verifier), indent=2))
    
    print("\n=== WITH VERIFIER ===")
    print(json.dumps(aggregate_results(results_with_verifier), indent=2))


def run_single_task(task, planner, verifier, use_verifier: bool = True) -> EvaluationResult:
    result = EvaluationResult(task_id=task.task_id, gold_actions=task.gold_actions)
    state = DialogueState()
    sim = RetailSimulator({'users': {}, 'products': {}, 'orders': {}})  # Dummy sim for planning
    predicted_actions = []
    
    instructions = task.user_scenario.get('instructions', {})
    task_desc = instructions.get('reason_for_call', '')
    known_info = instructions.get('known_info', '')
    full_desc = f'Reason for call: {task_desc}\nKnown info: {known_info}'
    
    for step in range(10):
        plan = planner.plan_next_action(full_desc, state, sim.db)
        action_name = plan.get('action', '')
        arguments = plan.get('arguments', {})
        
        predicted_actions.append({'action': action_name, 'arguments': arguments})
        
        if action_name in ('respond_to_user', 'ask_for_confirmation', 'transfer_to_human_agents'):
            break
        
        if use_verifier:
            v_result = verifier.verify(action_name, arguments, state, sim.db)
            if not v_result.passed:
                result.constraint_violations += len(v_result.violations)
                continue
        
        # Simulate execution (simplified - just track auth)
        if action_name in ('find_user_id_by_email', 'find_user_id_by_name_zip'):
            state.user_authenticated = True
            state.user_id = "user_id"
        
        if len(predicted_actions) >= len(task.gold_actions):
            break
    
    result.predicted_actions = predicted_actions
    result.action_accuracy = compute_action_accuracy(predicted_actions, task.gold_actions)
    return result


if __name__ == "__main__":
    run_eval(num_tasks=5)
