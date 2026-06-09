"""Run all baselines and our method on tau-bench tasks."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict, List

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from data_loader import RetailDB, load_tasks, load_split, get_task_by_id
from action_bank import ActionBank
from state_manager import DialogueState
from simulator import RetailSimulator
from verifier import ConstraintVerifier
from planner import OntologyPlanner
from llm_client import LLMClient, create_llm_client
from metrics import EvaluationResult, compute_action_accuracy, aggregate_results


UPDATE_ACTIONS = {
    "cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items",
    "modify_pending_order_payment", "modify_user_address",
    "return_delivered_order_items", "exchange_delivered_order_items",
}


class TaskRunner:
    """Runs a planner on a single task."""

    def __init__(self, db: RetailDB, action_bank: ActionBank, llm: LLMClient):
        self.db = db
        self.action_bank = action_bank
        self.llm = llm
        self.verifier = ConstraintVerifier(action_bank)
        self.planner = OntologyPlanner(action_bank, self.verifier, llm)

    def _create_simulator(self) -> RetailSimulator:
        return RetailSimulator({
            "users": self.db.users,
            "products": self.db.products,
            "orders": self.db.orders,
        })

    def run_task(self, task, planner, max_steps: int = 20, auto_confirm: bool = False, use_verifier: bool = True) -> EvaluationResult:
        """Run a task with a given planner."""
        result = EvaluationResult(
            task_id=task.task_id,
            gold_actions=task.gold_actions,
        )

        state = DialogueState()
        simulator = self._create_simulator()
        predicted_actions = []

        instructions = task.user_scenario.get("instructions", {})
        task_desc = instructions.get("reason_for_call", "")
        known_info = instructions.get("known_info", "")
        unknown_info = instructions.get("unknown_info", "")
        full_desc = f"Reason for call: {task_desc}\nKnown info: {known_info}\nUnknown info: {unknown_info}"

        try:
            for step in range(max_steps):
                plan = planner.plan_next_action(full_desc, state, simulator.db)
                action_name = plan.get("action", "")
                arguments = plan.get("arguments", {})

                predicted_actions.append({
                    "action": action_name,
                    "arguments": arguments,
                    "thought": plan.get("thought", ""),
                })

                if action_name in ("respond_to_user", "ask_for_confirmation"):
                    if plan.get("needs_confirmation") and state.user_authenticated:
                        state.user_confirmed = True
                        continue
                    break

                if action_name == "transfer_to_human_agents":
                    break

                if auto_confirm and action_name in UPDATE_ACTIONS:
                    state.user_confirmed = True

                if use_verifier:
                    v_result = self.verifier.verify(action_name, arguments, state, simulator.db)
                    if not v_result.passed:
                        result.constraint_violations += len(v_result.violations)
                        result.repair_attempts += 1
                        state.record_action(action_name, arguments, {"verifier_rejected": v_result.violations})
                        continue

                try:
                    action_result = simulator.execute(action_name, arguments, state)
                    state.record_action(action_name, arguments, action_result)

                    if action_name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
                        state.user_authenticated = True
                        state.user_id = action_result
                    if action_name in UPDATE_ACTIONS:
                        state.user_confirmed = False

                except ValueError as e:
                    result.invalid_actions += 1
                    state.record_action(action_name, arguments, {"error": str(e)})

                if len(predicted_actions) >= len(task.gold_actions):
                    break

        except Exception as e:
            result.error_message = str(e)

        result.predicted_actions = predicted_actions
        result.action_accuracy = compute_action_accuracy(predicted_actions, task.gold_actions)
        result.success = result.action_accuracy >= 1.0 and result.constraint_violations == 0 and result.invalid_actions == 0

        return result


def run_baseline(
    name: str,
    runner: TaskRunner,
    tasks: List[Any],
    task_ids: List[str],
    planner,
    auto_confirm: bool = False,
    use_verifier: bool = True,
    limit: int = 10,
) -> Dict[str, Any]:
    """Run a single baseline."""
    print(f"\n=== {name} ===")
    results = []

    for task_id in task_ids[:limit]:
        task = get_task_by_id(tasks, task_id)
        if task is None:
            continue

        result = runner.run_task(task, planner, auto_confirm=auto_confirm, use_verifier=use_verifier)
        results.append(result)
        print(f"Task {task_id}: accuracy={result.action_accuracy:.2%}, success={result.success}, violations={result.constraint_violations}, invalid={result.invalid_actions}")

    summary = aggregate_results(results)
    summary["baseline_name"] = name
    print(f"\nSummary: {json.dumps(summary, indent=2)}")
    return summary


def main():
    base = pathlib.Path(__file__).parents[1]
    db_path = base / "data/raw/retail/db.json"
    tasks_path = base / "data/raw/retail/tasks.json"
    split_path = base / "data/raw/retail/split_tasks.json"
    action_bank_path = base / "data/action_bank/retail_action_bank.json"

    db = RetailDB.load(db_path)
    tasks = load_tasks(tasks_path)
    split_data = load_split(split_path)
    action_bank = ActionBank.from_json(action_bank_path)

    test_ids = split_data.get("test", [])[:10]  # Limit to 10 for testing

    # Create LLM client
    llm = create_llm_client()
    runner = TaskRunner(db, action_bank, llm)

    # Import baseline planners
    from baselines.react_baseline import ReActPlanner
    from baselines.rag_baseline import RAGPlanner
    from baselines.schema_baseline import SchemaPlanner

    all_results = []

    # Baseline 1: ReAct (no action layer, no verifier)
    all_results.append(run_baseline(
        "ReAct (no action layer, no verifier)",
        runner, tasks, test_ids,
        ReActPlanner(llm),
        auto_confirm=False, use_verifier=False,
    ))

    # Baseline 2: Schema-only (ActionBank in prompt, no verifier)
    all_results.append(run_baseline(
        "Schema-only (no verifier)",
        runner, tasks, test_ids,
        SchemaPlanner(llm, action_bank),
        auto_confirm=False, use_verifier=False,
    ))

    # Ours: Schema + Verifier
    all_results.append(run_baseline(
        "Ours (Schema + Verifier)",
        runner, tasks, test_ids,
        SchemaPlanner(llm, action_bank),
        auto_confirm=False, use_verifier=True,
    ))

    # Save results
    results_path = base / "results/baseline_comparison.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
