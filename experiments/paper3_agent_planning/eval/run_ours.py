"""Run Ours (LLM + ActionBank + Verifier) evaluation on tau-bench test tasks."""
from __future__ import annotations

import json
import pathlib
import sys
import time
from typing import List

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from data_loader import RetailDB, load_tasks, load_split, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from llm_client import OpenAIClient
from verifier import ConstraintVerifier
from baselines.schema_baseline import SchemaPlanner


class VerifierEnhancedPlanner(SchemaPlanner):
    """Schema planner with runtime constraint verification and repair loop."""

    def __init__(self, llm, action_bank, verifier, max_repair=2):
        super().__init__(llm, action_bank)
        self.verifier = verifier
        self.max_repair = max_repair

    def plan_next_action(self, task, state, db):
        # Try planning with repair loop
        for attempt in range(self.max_repair + 1):
            action = super().plan_next_action(task, state, db)
            action_name = action.get('action', '')
            arguments = action.get('arguments', {})

            # Skip verification for terminal actions
            if action_name in ('transfer_to_human_agents',):
                return action

            # Verify the action
            v_result = self.verifier.verify(action_name, arguments, state, db)
            if v_result.passed:
                return action

            # Action rejected - record violation and try again
            violations = v_result.violations
            state.history.append({
                'action': action_name,
                'arguments': arguments,
                'result': {'verifier_rejected': violations}
            })

        # Max repairs reached, return last action anyway
        return action


def simulate_task(task, db, planner, max_steps=8):
    """Simulate a task with the verifier-enhanced planner."""
    state = DialogueState()
    gold_actions = [ga['name'] for ga in task.gold_actions]
    gold_final = gold_actions[-1] if gold_actions else None
    predicted = []
    violations = 0
    invalid = 0

    for step in range(max_steps):
        action = planner.plan_next_action(task, state, db)
        predicted.append(action['action'])

        if action['action'] == 'transfer_to_human_agents':
            return predicted, None, False, 'transferred', violations, invalid

        # Simulate execution
        if action['action'] == 'find_user_id_by_name_zip':
            fn = action['arguments'].get('first_name', '')
            ln = action['arguments'].get('last_name', '')
            z = action['arguments'].get('zip', '')
            uid = next((u for u, usr in db.users.items()
                       if usr.get('name', {}).get('first_name') == fn
                       and usr.get('name', {}).get('last_name') == ln
                       and usr.get('address', {}).get('zip') == z), None)
            result = {'user_id': uid} if uid else {'error': 'not found'}
            if uid:
                state.user_id = uid
                state.user_authenticated = True
        elif action['action'] == 'find_user_id_by_email':
            em = action['arguments'].get('email', '')
            uid = next((u for u, usr in db.users.items() if usr.get('email') == em), None)
            result = {'user_id': uid} if uid else {'error': 'not found'}
            if uid:
                state.user_id = uid
                state.user_authenticated = True
        elif action['action'] == 'get_user_details':
            uid = action['arguments'].get('user_id', state.user_id)
            result = db.users.get(uid, {'error': 'not found'})
        elif action['action'] == 'get_order_details':
            uid = action['arguments'].get('user_id', state.user_id)
            oid = action['arguments'].get('order_id', '')
            order = next((o for o in db.orders.values()
                         if o.get('order_id') == oid and o.get('user_id') == uid), None)
            result = order if order else {'error': 'not found'}
            if order:
                state.cached_orders[str(oid)] = order
        elif action['action'] == 'get_product_details':
            pid = action['arguments'].get('product_id', '')
            result = db.products.get(pid, {'error': 'not found'})
        elif action['action'] in ['cancel_pending_order', 'exchange_delivered_order_items',
                                   'return_delivered_order_items', 'modify_pending_order_items',
                                   'modify_pending_order_address', 'modify_user_address']:
            state.history.append({
                'action': action['action'],
                'arguments': action['arguments'],
                'result': {'status': 'done'}
            })
            final = action['action']
            success = final == gold_final
            return predicted, final, success, 'completed', violations, invalid
        else:
            result = {'error': 'unknown action'}
            invalid += 1

        state.history.append({
            'action': action['action'],
            'arguments': action['arguments'],
            'result': result
        })

    return predicted, None, False, 'max_steps', violations, invalid


def run_ours(
    db_path: pathlib.Path,
    tasks_path: pathlib.Path,
    split_path: pathlib.Path,
    action_bank_path: pathlib.Path,
    model: str = 'gemma4-31b',
    base_url: str = 'http://172.16.22.79:9999/v1',
    limit: int = 10,
) -> List[dict]:
    """Run Ours (with verifier) on test tasks."""
    db = RetailDB.load(db_path)
    tasks = load_tasks(tasks_path)
    split_data = load_split(split_path)
    action_bank = ActionBank.from_json(action_bank_path)

    llm = OpenAIClient(model=model, base_url=base_url)
    verifier = ConstraintVerifier(action_bank)
    planner = VerifierEnhancedPlanner(llm, action_bank, verifier, max_repair=1)

    task_ids = split_data.get('test', [])[:limit]
    results = []

    for task_id in task_ids:
        task = get_task_by_id(tasks, task_id)
        if task is None:
            print(f"Warning: task {task_id} not found")
            continue

        gold = [ga['name'] for ga in task.gold_actions]

        start = time.time()
        predicted, final, success, reason, violations, invalid = simulate_task(task, db, planner)
        elapsed = time.time() - start

        matches = sum(1 for p, g in zip(predicted, gold) if p == g)
        accuracy = matches / max(len(gold), 1)

        result = {
            'task_id': task_id,
            'gold': gold,
            'predicted': predicted,
            'final_action': final,
            'task_success': success,
            'action_accuracy': accuracy,
            'violations': violations,
            'invalid_actions': invalid,
            'reason': reason,
            'time': elapsed,
        }
        results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} Task {task_id}: acc={accuracy:.0%}, violations={violations}, invalid={invalid}, time={elapsed:.1f}s")

    return results


if __name__ == '__main__':
    base = pathlib.Path(__file__).parents[1]
    db_path = base / 'data/raw/retail/db.json'
    tasks_path = base / 'data/raw/retail/tasks.json'
    split_path = base / 'data/raw/retail/split_tasks.json'
    action_bank_path = base / 'data/action_bank/retail_action_bank.json'

    print("=== Ours (LLM + ActionBank + Verifier) ===\n")

    results = run_ours(
        db_path, tasks_path, split_path, action_bank_path,
        model='gemma4-31b',
        base_url='http://172.16.22.79:9999/v1',
        limit=10,
    )

    success_count = sum(1 for r in results if r['task_success'])
    avg_acc = sum(r['action_accuracy'] for r in results) / len(results)
    avg_time = sum(r['time'] for r in results) / len(results)
    total_violations = sum(r['violations'] for r in results)
    total_invalid = sum(r['invalid_actions'] for r in results)

    print(f"\n=== SUMMARY ({len(results)} tasks) ===")
    print(f"Task Success Rate: {success_count}/{len(results)} = {success_count/len(results):.1%}")
    print(f"Average Action Accuracy: {avg_acc:.1%}")
    print(f"Total Constraint Violations: {total_violations}")
    print(f"Total Invalid Actions: {total_invalid}")
    print(f"Average Time per Task: {avg_time:.1f}s")

    out_path = base / 'results/ours_results.json'
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump({
            'model': 'gemma4-31b',
            'method': 'ours',
            'num_tasks': len(results),
            'task_success_rate': success_count / len(results),
            'avg_action_accuracy': avg_acc,
            'total_violations': total_violations,
            'total_invalid': total_invalid,
            'avg_time': avg_time,
            'results': results,
        }, f, indent=2)
    print(f"\nResults saved to {out_path}")
