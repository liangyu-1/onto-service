"""End-to-end runner for evaluating a planner on tau-bench tasks."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict, List, Optional

# Add src to path
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from data_loader import RetailDB, load_tasks, load_split, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from planner import OntologyPlanner
from llm_client import LLMClient, DummyClient
from metrics import EvaluationResult, compute_action_accuracy


# Actions that require user confirmation before execution
UPDATE_ACTIONS = {
    "cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items",
    "modify_pending_order_payment", "modify_user_address",
    "return_delivered_order_items", "exchange_delivered_order_items",
}


class TaskRunner:
    """Runs a planner on a single task and evaluates the result."""

    def __init__(self, db: RetailDB, action_bank: ActionBank, llm: Optional[LLMClient] = None):
        self.db = db
        self.action_bank = action_bank
        self.llm = llm or DummyClient()
        self.verifier = ConstraintVerifier(action_bank)
        self.planner = OntologyPlanner(action_bank, self.verifier, self.llm)

    def _create_simulator(self) -> RetailSimulator:
        """Create a fresh simulator with a clean DB copy."""
        return RetailSimulator({
            "users": self.db.users,
            "products": self.db.products,
            "orders": self.db.orders,
        })

    def run_task_with_planner(self, task, planner, max_steps: int = 20, auto_confirm: bool = False) -> EvaluationResult:
        """Run a task with a given planner."""
        result = EvaluationResult(
            task_id=task.task_id,
            gold_actions=task.gold_actions,
        )

        # Fresh state and simulator for each task
        state = DialogueState()
        simulator = self._create_simulator()
        predicted_actions = []

        # Extract task description from user scenario
        instructions = task.user_scenario.get("instructions", {})
        task_desc = instructions.get("reason_for_call", "")
        known_info = instructions.get("known_info", "")
        unknown_info = instructions.get("unknown_info", "")

        full_desc = f"""Reason for call: {task_desc}
Known info: {known_info}
Unknown info: {unknown_info}"""

        try:
            for step in range(max_steps):
                # Plan next action
                plan = planner.plan_next_action(full_desc, state, simulator.db)
                action_name = plan.get("action", "")
                arguments = plan.get("arguments", {})

                # Record the predicted action
                predicted_actions.append({
                    "action": action_name,
                    "arguments": arguments,
                    "thought": plan.get("thought", ""),
                })

                # Check if it's a terminal action
                if action_name in ("respond_to_user", "ask_for_confirmation"):
                    if plan.get("needs_confirmation") and state.user_authenticated:
                        state.user_confirmed = True
                        continue
                    break

                if action_name == "transfer_to_human_agents":
                    break

                # For gold baseline: auto-confirm update actions before verification
                if auto_confirm and action_name in UPDATE_ACTIONS:
                    state.user_confirmed = True

                # Verify before execution
                v_result = self.verifier.verify(action_name, arguments, state, simulator.db)
                if not v_result.passed:
                    result.constraint_violations += len(v_result.violations)
                    state.record_action(action_name, arguments, {"verifier_rejected": v_result.violations})
                    continue

                # Try to execute the action
                try:
                    action_result = simulator.execute(action_name, arguments, state)
                    state.record_action(action_name, arguments, action_result)

                    # Update state based on action
                    if action_name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
                        state.user_authenticated = True
                        state.user_id = action_result
                    
                    # Reset confirmation after update actions
                    if action_name in UPDATE_ACTIONS:
                        state.user_confirmed = False

                except ValueError as e:
                    result.invalid_actions += 1
                    state.record_action(action_name, arguments, {"error": str(e)})

                # Check if we've completed all gold actions
                if len(predicted_actions) >= len(task.gold_actions):
                    break

        except Exception as e:
            result.error_message = str(e)

        result.predicted_actions = predicted_actions
        result.action_accuracy = compute_action_accuracy(predicted_actions, task.gold_actions)
        result.success = result.action_accuracy >= 1.0 and result.constraint_violations == 0 and result.invalid_actions == 0

        return result

    def run_task(self, task, max_steps: int = 20) -> EvaluationResult:
        """Run a task with the default ontology planner."""
        return self.run_task_with_planner(task, self.planner, max_steps)

    def run_task_gold(self, task, max_steps: int = 20) -> EvaluationResult:
        """Run a task following gold actions (for validation)."""
        from baselines.rule_baseline import RuleBaselinePlanner
        gold_planner = RuleBaselinePlanner(task.gold_actions)
        return self.run_task_with_planner(task, gold_planner, max_steps, auto_confirm=True)


def run_evaluation(
    db_path: pathlib.Path,
    tasks_path: pathlib.Path,
    split_path: pathlib.Path,
    action_bank_path: pathlib.Path,
    llm: Optional[LLMClient] = None,
    split: str = "test",
    use_gold: bool = False,
    limit: int = 5,
) -> List[EvaluationResult]:
    """Run evaluation on a split of tasks."""
    db = RetailDB.load(db_path)
    tasks = load_tasks(tasks_path)
    split_data = load_split(split_path)
    action_bank = ActionBank.from_json(action_bank_path)

    task_ids = split_data.get(split, [])
    runner = TaskRunner(db, action_bank, llm)

    results = []
    for task_id in task_ids[:limit]:
        task = get_task_by_id(tasks, task_id)
        if task is None:
            print(f"Warning: task {task_id} not found")
            continue

        if use_gold:
            print(f"Running task {task_id} (gold baseline)...")
            result = runner.run_task_gold(task)
        else:
            print(f"Running task {task_id}...")
            result = runner.run_task(task)

        results.append(result)
        print(f"  Accuracy: {result.action_accuracy:.2%}, Success: {result.success}, Invalid: {result.invalid_actions}, Constraint violations: {result.constraint_violations}")

    return results


if __name__ == "__main__":
    base = pathlib.Path(__file__).parents[1]
    db_path = base / "data/raw/retail/db.json"
    tasks_path = base / "data/raw/retail/tasks.json"
    split_path = base / "data/raw/retail/split_tasks.json"
    action_bank_path = base / "data/action_bank/retail_action_bank.json"

    print("=== Testing with GOLD baseline (pipeline validation) ===")
    gold_results = run_evaluation(db_path, tasks_path, split_path, action_bank_path, use_gold=True, limit=5)

    from metrics import aggregate_results
    print("\n=== GOLD BASELINE SUMMARY ===")
    print(json.dumps(aggregate_results(gold_results), indent=2))
