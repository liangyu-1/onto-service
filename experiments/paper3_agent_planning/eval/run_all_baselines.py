"""Run all baselines and Ours on tau-bench test tasks."""
from __future__ import annotations

import json
import pathlib
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from data_loader import RetailDB, load_tasks, load_split, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from llm_client import OpenAIClient
from verifier import ConstraintVerifier
from baselines.schema_baseline import SchemaPlanner
from baselines.ours_planner import OursPlanner
from baselines.react_baseline import ReActPlanner
from baselines.rag_baseline import RAGPlanner


def simulate_task(task, db, planner, max_steps=8):
    """Simulate a task and return metrics."""
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
            return {
                'predicted': predicted,
                'final': None,
                'success': False,
                'violations': violations,
                'invalid': invalid,
                'reason': 'transferred',
            }
        
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
            result = db.users.get(state.user_id, {'error': 'not found'})
        elif action['action'] == 'get_order_details':
            oid = action['arguments'].get('order_id', '')
            order = next((o for o in db.orders.values()
                         if o.get('order_id') == oid and o.get('user_id') == state.user_id), None)
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
            matches = sum(1 for p, g in zip(predicted, gold_actions) if p == g)
            accuracy = matches / max(len(gold_actions), 1)
            return {
                'predicted': predicted,
                'final': final,
                'success': final == gold_final,
                'violations': violations,
                'invalid': invalid,
                'accuracy': accuracy,
                'reason': 'completed',
            }
        else:
            result = {'error': 'unknown action'}
            invalid += 1
        
        state.history.append({
            'action': action['action'],
            'arguments': action['arguments'],
            'result': result
        })
    
    matches = sum(1 for p, g in zip(predicted, gold_actions) if p == g)
    accuracy = matches / max(len(gold_actions), 1)
    return {
        'predicted': predicted,
        'final': None,
        'success': False,
        'violations': violations,
        'invalid': invalid,
        'accuracy': accuracy,
        'reason': 'max_steps',
    }


def run_baseline(name, planner, tasks, db, limit=10):
    """Run a baseline on test tasks."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    
    results = []
    for task in tasks[:limit]:
        gold = [ga['name'] for ga in task.gold_actions]
        
        start = time.time()
        result = simulate_task(task, db, planner)
        elapsed = time.time() - start
        
        result['task_id'] = task.task_id
        result['gold'] = gold
        result['time'] = elapsed
        results.append(result)
        
        status = "✅" if result['success'] else "❌"
        print(f"{status} Task {task.task_id}: acc={result.get('accuracy', 0):.0%}, "
              f"final={result['final']}, gold={gold[-1] if gold else None}, "
              f"violations={result['violations']}, invalid={result['invalid']}, "
              f"time={elapsed:.1f}s")
    
    # Summary
    success_count = sum(1 for r in results if r['success'])
    avg_acc = sum(r.get('accuracy', 0) for r in results) / len(results)
    total_v = sum(r['violations'] for r in results)
    total_i = sum(r['invalid'] for r in results)
    avg_time = sum(r['time'] for r in results) / len(results)
    
    print(f"\nSummary: Success={success_count}/{len(results)}={success_count/len(results):.1%}, "
          f"AvgAcc={avg_acc:.1%}, Violations={total_v}, Invalid={total_i}, AvgTime={avg_time:.1f}s")
    
    return {
        'name': name,
        'num_tasks': len(results),
        'task_success_rate': success_count / len(results),
        'avg_action_accuracy': avg_acc,
        'total_violations': total_v,
        'total_invalid': total_i,
        'avg_time': avg_time,
        'results': results,
    }


def main():
    base = pathlib.Path(__file__).parents[1]
    db_path = base / 'data/raw/retail/db.json'
    tasks_path = base / 'data/raw/retail/tasks.json'
    split_path = base / 'data/raw/retail/split_tasks.json'
    action_bank_path = base / 'data/action_bank/retail_action_bank.json'
    
    db = RetailDB.load(db_path)
    all_tasks = load_tasks(tasks_path)
    split_data = load_split(split_path)
    action_bank = ActionBank.from_json(action_bank_path)
    
    test_tasks = [t for t in all_tasks if t.task_id in set(split_data.get('test', []))]
    train_tasks = [t for t in all_tasks if t.task_id in set(split_data.get('train', []))]
    
    llm = OpenAIClient(model='gemma4-31b', base_url='http://172.16.22.79:9999/v1')
    verifier = ConstraintVerifier(action_bank)
    
    limit = 10
    
    all_results = []
    
    # 1. Schema-Only
    schema_planner = SchemaPlanner(llm, action_bank)
    all_results.append(run_baseline("Schema-Only", schema_planner, test_tasks, db, limit))
    
    # 2. ReAct
    react_planner = ReActPlanner(llm)
    all_results.append(run_baseline("ReAct", react_planner, test_tasks, db, limit))
    
    # 3. RAG
    rag_planner = RAGPlanner(llm, action_bank, train_tasks, top_k=2)
    all_results.append(run_baseline("RAG", rag_planner, test_tasks, db, limit))
    
    # 4. Ours (with verifier)
    ours_planner = OursPlanner(llm, action_bank, verifier, max_repair=1)
    all_results.append(run_baseline("Ours", ours_planner, test_tasks, db, limit))
    
    # Save all results
    out_path = base / 'results/all_baselines.json'
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Final comparison table
    print(f"\n{'='*80}")
    print("FINAL COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Method':<15} | {'Success':>8} | {'AvgAcc':>8} | {'Violations':>10} | {'Invalid':>8} | {'Time':>8}")
    print("-" * 80)
    for r in all_results:
        print(f"{r['name']:<15} | {r['task_success_rate']:>7.1%} | {r['avg_action_accuracy']:>7.1%} | "
              f"{r['total_violations']:>10} | {r['total_invalid']:>8} | {r['avg_time']:>7.1f}s")
    print(f"{'='*80}")
    print(f"\nResults saved to {out_path}")


if __name__ == '__main__':
    main()
