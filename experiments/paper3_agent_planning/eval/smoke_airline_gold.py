"""Smoke test: verify airline gold actions pass through verifier + simulator."""
from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from data_loader import AirlineDB, load_tasks, load_split, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from airline_simulator import AirlineSimulator
from airline_verifier import AirlineConstraintVerifier


# Actions that require user confirmation before execution
UPDATE_ACTIONS = {
    "book_reservation",
    "update_reservation_flights",
    "update_reservation_baggages",
    "update_reservation_passengers",
    "cancel_reservation",
}


import re


def _extract_user_id(known_info: str) -> Optional[str]:
    """Extract user_id from known_info text."""
    if not known_info:
        return None
    patterns = [
        r"Your user id is[:\s]+([a-z_0-9]+)",
        r"Your user id[:\s]+([a-z_0-9]+)",
        r"user id is[:\s]+([a-z_0-9]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, known_info, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def run_task_gold(db: AirlineDB, action_bank: ActionBank, task) -> dict:
    """Run gold actions for a single airline task."""
    simulator = AirlineSimulator({
        "users": db.users,
        "flights": db.flights,
        "reservations": db.reservations,
    })
    verifier = AirlineConstraintVerifier(action_bank)
    state = DialogueState()

    # Auto-authenticate if user_id is in known_info
    instructions = task.user_scenario.get("instructions", {})
    known_info = instructions.get("known_info", "")
    auto_user_id = _extract_user_id(known_info)
    if auto_user_id:
        state.user_authenticated = True
        state.user_id = auto_user_id

    results = {
        "task_id": task.task_id,
        "total_actions": len(task.gold_actions),
        "passed": 0,
        "failed": 0,
        "verifier_rejected": 0,
        "simulator_errors": 0,
        "errors": [],
    }

    for idx, gold_action in enumerate(task.gold_actions):
        action_name = gold_action["name"]
        arguments = gold_action.get("arguments", {})

        # Auto-authenticate lookup actions
        if action_name in ("get_user_details", "get_reservation_details", "search_direct_flight"):
            state.user_authenticated = True

        # Auto-confirm update actions
        if action_name in UPDATE_ACTIONS:
            state.user_confirmed = True

        # Verify
        v_result = verifier.verify(action_name, arguments, state, simulator.db)
        if not v_result.passed:
            results["verifier_rejected"] += 1
            results["failed"] += 1
            results["errors"].append({
                "step": idx,
                "action": action_name,
                "arguments": arguments,
                "phase": "verifier",
                "error": v_result.violations,
            })
            state.record_action(action_name, arguments, {"verifier_rejected": v_result.violations})
            continue

        # Execute
        try:
            result = simulator.execute(action_name, arguments, state)
            state.record_action(action_name, arguments, result)
            results["passed"] += 1

            # Update auth state
            if action_name == "get_user_details":
                state.user_authenticated = True
                state.user_id = arguments.get("user_id")

            # Reset confirmation after update actions
            if action_name in UPDATE_ACTIONS:
                state.user_confirmed = False

        except Exception as e:
            results["simulator_errors"] += 1
            results["failed"] += 1
            results["errors"].append({
                "step": idx,
                "action": action_name,
                "arguments": arguments,
                "phase": "simulator",
                "error": str(e),
            })
            state.record_action(action_name, arguments, {"error": str(e)})

    results["success"] = results["failed"] == 0
    return results


def main():
    base = pathlib.Path(__file__).parents[1]
    db_path = base / "data/raw/airline/db.json"
    tasks_path = base / "data/raw/airline/tasks.json"
    split_path = base / "data/raw/airline/split_tasks.json"
    action_bank_path = base / "data/action_bank/airline_action_bank.json"

    db = AirlineDB.load(db_path)
    tasks = load_tasks(tasks_path)
    split_data = load_split(split_path)
    action_bank = ActionBank.from_json(action_bank_path)

    test_ids = split_data.get("test", [])[:10]  # First 10 for smoke test

    all_results = []
    for task_id in test_ids:
        task = get_task_by_id(tasks, task_id)
        if task is None:
            print(f"Warning: task {task_id} not found")
            continue

        result = run_task_gold(db, action_bank, task)
        all_results.append(result)

        status = "PASS" if result["success"] else "FAIL"
        print(f"[{status}] Task {task_id}: {result['passed']}/{result['total_actions']} actions OK "
              f"(verifier_rej={result['verifier_rejected']}, sim_err={result['simulator_errors']})")
        for err in result["errors"]:
            print(f"       -> Step {err['step']} {err['action']}: {err['phase']} | {err['error']}")

    total = len(all_results)
    passed = sum(1 for r in all_results if r["success"])
    total_actions = sum(r["total_actions"] for r in all_results)
    action_passes = sum(r["passed"] for r in all_results)
    verifier_rej = sum(r["verifier_rejected"] for r in all_results)
    sim_err = sum(r["simulator_errors"] for r in all_results)

    print(f"\n=== SUMMARY ===")
    print(f"Tasks: {passed}/{total} passed")
    print(f"Actions: {action_passes}/{total_actions} passed")
    print(f"Verifier rejections: {verifier_rej}")
    print(f"Simulator errors: {sim_err}")


if __name__ == "__main__":
    main()
