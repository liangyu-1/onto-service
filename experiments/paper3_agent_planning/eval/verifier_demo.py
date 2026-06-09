"""Demonstrate the verifier catching common LLM errors."""
from __future__ import annotations

import json
import sys
sys.path.insert(0, '/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/src')

from data_loader import RetailDB
from action_bank import ActionBank
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from state_manager import DialogueState

def demo():
    db = RetailDB.load('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/raw/retail/db.json')
    action_bank = ActionBank.from_json('/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json')
    verifier = ConstraintVerifier(action_bank)
    
    print("=" * 70)
    print("VERIFIER DEMO: Catching Common LLM Errors")
    print("=" * 70)
    
    # Scenario 1: LLM tries to cancel without authentication
    print("\n[Scenario 1] Cancel order WITHOUT authentication")
    state = DialogueState()
    sim = RetailSimulator({'users': db.users, 'products': db.products, 'orders': db.orders})
    
    action = {
        'action_name': 'cancel_pending_order',
        'arguments': {'order_id': '#W2611340', 'reason': 'no longer needed'}
    }
    result = verifier.verify(action['action_name'], action['arguments'], state, sim.db)
    print(f"  Action: {action['action_name']}({action['arguments']})")
    print(f"  Result: {'PASS' if result.passed else 'FAIL'}")
    for v in result.violations:
        print(f"  Violation: {v}")
    
    # Scenario 2: LLM tries to cancel a non-pending order
    print("\n[Scenario 2] Cancel order that is NOT pending")
    state = DialogueState()
    state.user_authenticated = True
    sim = RetailSimulator({'users': db.users, 'products': db.products, 'orders': db.orders})
    
    action = {
        'action_name': 'cancel_pending_order',
        'arguments': {'order_id': '#W2611340', 'reason': 'no longer needed'}
    }
    result = verifier.verify(action['action_name'], action['arguments'], state, sim.db)
    print(f"  Action: {action['action_name']}({action['arguments']})")
    print(f"  Order status: {sim.db['orders']['#W2611340']['status']}")
    print(f"  Result: {'PASS' if result.passed else 'FAIL'}")
    for v in result.violations:
        print(f"  Violation: {v}")
    
    # Scenario 3: LLM tries to exchange without user confirmation
    print("\n[Scenario 3] Exchange items WITHOUT user confirmation")
    state = DialogueState()
    state.user_authenticated = True
    state.user_id = 'james_li_5688'
    sim = RetailSimulator({'users': db.users, 'products': db.products, 'orders': db.orders})
    
    action = {
        'action_name': 'exchange_delivered_order_items',
        'arguments': {
            'order_id': '#W2611340',
            'item_ids': ['6469567736'],
            'new_item_ids': ['6469567736'],
            'payment_method_id': 'payment_id'
        }
    }
    result = verifier.verify(action['action_name'], action['arguments'], state, sim.db)
    print(f"  Action: {action['action_name']}({action['arguments']})")
    print(f"  Result: {'PASS' if result.passed else 'FAIL'}")
    for v in result.violations:
        print(f"  Violation: {v}")
    
    # Scenario 4: LLM tries to return from a pending order (wrong status)
    print("\n[Scenario 4] Return items from PENDING order (should be delivered)")
    state = DialogueState()
    state.user_authenticated = True
    state.user_confirmed = True
    sim = RetailSimulator({'users': db.users, 'products': db.products, 'orders': db.orders})
    
    # Find a pending order
    pending_order = None
    for oid, order in sim.db['orders'].items():
        if order['status'] == 'pending':
            pending_order = oid
            break
    
    if pending_order:
        action = {
            'action_name': 'return_delivered_order_items',
            'arguments': {
                'order_id': pending_order,
                'item_ids': ['item_id'],
                'payment_method_id': 'payment_id'
            }
        }
        result = verifier.verify(action['action_name'], action['arguments'], state, sim.db)
        print(f"  Action: {action['action_name']}({action['arguments']})")
        print(f"  Order status: {sim.db['orders'][pending_order]['status']}")
        print(f"  Result: {'PASS' if result.passed else 'FAIL'}")
        for v in result.violations:
            print(f"  Violation: {v}")
    
    # Scenario 5: Correct action (should pass)
    print("\n[Scenario 5] Correctly authenticated and confirmed cancel")
    state = DialogueState()
    state.user_authenticated = True
    state.user_confirmed = True
    sim = RetailSimulator({'users': db.users, 'products': db.products, 'orders': db.orders})
    
    # Find a pending order
    pending_order = None
    for oid, order in sim.db['orders'].items():
        if order['status'] == 'pending':
            pending_order = oid
            break
    
    if pending_order:
        action = {
            'action_name': 'cancel_pending_order',
            'arguments': {
                'order_id': pending_order,
                'reason': 'no longer needed'
            }
        }
        result = verifier.verify(action['action_name'], action['arguments'], state, sim.db)
        print(f"  Action: {action['action_name']}({action['arguments']})")
        print(f"  Order status: {sim.db['orders'][pending_order]['status']}")
        print(f"  Result: {'PASS' if result.passed else 'FAIL'}")
        for v in result.violations:
            print(f"  Violation: {v}")
    
    print("\n" + "=" * 70)
    print("Demo complete. The verifier successfully catches policy violations")
    print("that a naive LLM would make.")
    print("=" * 70)


if __name__ == "__main__":
    demo()
