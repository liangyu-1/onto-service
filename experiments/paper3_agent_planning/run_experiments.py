#!/usr/bin/env python3
"""Run all experiments and save results to local files."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from data_loader import RetailDB, Task, load_tasks, load_split
from action_bank import ActionBank
from state_manager import DialogueState
from llm_client import OpenAIClient, create_llm_client
from verifier import ConstraintVerifier
from simulator import RetailSimulator
from evaluator import LocalTauBenchEvaluator
from case_retriever import CaseRetriever
from baselines.schema_baseline import SchemaPlanner
from baselines.ours_planner import OursPlanner
from baselines.ablation_planners import (
    DuplicateOnlyPlanner,
    PreconditionOnlyPlanner,
    BlockingNoRepairPlanner,
)


FINAL_ACTIONS = {
    "finish_task",
    "transfer_to_human_agents",
}

UPDATE_ACTIONS = {
    "modify_user_address",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "cancel_pending_order",
    "return_delivered_order_items",
    "exchange_delivered_order_items",
}


# ============================================================================
# Experiment Runner
# ============================================================================

class ExperimentRunner:
    def __init__(
        self,
        db: RetailDB,
        action_bank: ActionBank,
        verifier: ConstraintVerifier,
        max_steps: int = 15,
    ):
        self.db = db
        self.db_dict = {
            "users": db.users,
            "products": db.products,
            "orders": db.orders,
        }
        self.action_bank = action_bank
        self.verifier = verifier
        self.max_steps = max_steps
        self.evaluator = LocalTauBenchEvaluator(self.db_dict)

    def _create_simulator(self) -> RetailSimulator:
        return RetailSimulator(self.db_dict)

    def run_task(
        self,
        task: Task,
        planner,
        planner_name: str,
    ) -> Dict[str, Any]:
        """Run a single task and return detailed results."""
        state = DialogueState()
        gold_names = [ga["name"] for ga in task.gold_actions]
        gold_action_calls = [
            {"action": ga["name"], "arguments": ga.get("arguments", {})}
            for ga in task.gold_actions
        ]
        gold_final = gold_names[-1] if gold_names else None
        gold_final_call = gold_action_calls[-1] if gold_action_calls else None
        predicted = []
        predicted_calls = []
        step_details = []
        executed_violation_count = 0
        rejected_violation_count = 0
        invalid_count = 0
        execution_errors = []
        repair_count = 0
        grounding_change_count = 0
        grounding_rejection_count = 0
        progress_rejection_count = 0
        retrieved_case_ids_seen = []
        suggestion_count_total = 0
        suggestion_fallback_count = 0
        update_suggestion_fallback_count = 0
        start_time = time.time()
        simulator = self._create_simulator()

        for step in range(self.max_steps):
            step_start = time.time()
            action = planner.plan_next_action(task, state, self.db_dict)
            step_time = time.time() - step_start

            action_name = action.get("action", "")
            arguments = action.get("arguments", {})
            thought = action.get("thought", "")
            grounding_trace = action.get("_grounding_trace", [])
            retrieved_case_ids = action.get("_retrieved_case_ids", [])
            suggested_action_count = action.get("_suggested_action_count", 0)
            suggestion_fallback_used = bool(action.get("_suggestion_fallback_used", False))
            update_suggestion_fallback_used = bool(action.get("_update_suggestion_fallback_used", False))
            repair_trace = action.get("_repair_trace", [])
            repair_count += len(repair_trace)
            rejected_violation_count += sum(len(r.get("violations", [])) for r in repair_trace)
            grounding_change_count += len(grounding_trace)
            grounding_rejection_count += sum(
                1
                for r in repair_trace
                for v in r.get("violations", [])
                if str(v).startswith("GROUNDING:")
            )
            progress_rejection_count += sum(
                1
                for r in repair_trace
                for v in r.get("violations", [])
                if str(v).startswith("PROGRESS:")
            )
            for case_id in retrieved_case_ids:
                if case_id not in retrieved_case_ids_seen:
                    retrieved_case_ids_seen.append(case_id)
            suggestion_count_total += suggested_action_count
            if suggestion_fallback_used:
                suggestion_fallback_count += 1
            if update_suggestion_fallback_used:
                update_suggestion_fallback_count += 1

            # Track violations/invalids
            v_result = self.verifier.verify(action_name, arguments, state, self.db_dict)
            if not v_result.passed:
                executed_violation_count += len(v_result.violations)
                if "Unknown action" in str(v_result.violations):
                    invalid_count += 1

            predicted.append(action_name)
            predicted_call = {"action": action_name, "arguments": arguments}
            predicted_calls.append(predicted_call)

            # Execute
            execution_error = None
            try:
                result = simulator.execute(action_name, arguments, state)
                if action_name in ("find_user_id_by_email", "find_user_id_by_name_zip"):
                    state.user_id = result
                    state.user_authenticated = True
                if action_name in UPDATE_ACTIONS:
                    state.user_confirmed = False
            except Exception as e:
                result = {"error": str(e)}
                execution_error = str(e)
                execution_errors.append(f"{action_name}: {e}")
                invalid_count += 1
            is_final = action_name in FINAL_ACTIONS

            step_details.append({
                "step": step,
                "action": action_name,
                "arguments": arguments,
                "thought": thought,
                "grounding_trace": grounding_trace,
                "retrieved_case_ids": retrieved_case_ids,
                "suggested_action_count": suggested_action_count,
                "suggestion_fallback_used": suggestion_fallback_used,
                "update_suggestion_fallback_used": update_suggestion_fallback_used,
                "repair_trace": repair_trace,
                "verifier_passed": v_result.passed,
                "verifier_violations": v_result.violations,
                "result": result,
                "execution_error": execution_error,
                "is_final": is_final,
                "step_time": round(step_time, 2),
            })

            state.history.append({
                "action": action_name,
                "arguments": arguments,
                "result": result,
            })

            if is_final:
                break

        elapsed = time.time() - start_time
        final_action = predicted[-1] if predicted else None
        local_reward = self.evaluator.evaluate(
            task=task,
            predicted_calls=predicted_calls,
            executed_violation_count=executed_violation_count,
            invalid_count=invalid_count,
            predicted_execution_errors=execution_errors,
        )
        success = local_reward.local_success
        strict_success = local_reward.strict_success
        final_name_match = local_reward.final_name_match
        final_exact_match = local_reward.final_exact_match

        # Calculate prefix accuracy
        accuracy = self._prefix_accuracy(gold_names, predicted)

        return {
            "task_id": task.task_id,
            "planner": planner_name,
            "gold_actions": gold_names,
            "gold_action_calls": gold_action_calls,
            "gold_final": gold_final,
            "gold_final_call": gold_final_call,
            "predicted_actions": predicted,
            "predicted_action_calls": predicted_calls,
            "predicted_final": final_action,
            "predicted_final_call": predicted_calls[-1] if predicted_calls else None,
            "predicted_effective_final_call": local_reward.predicted_final_action,
            "success": success,
            "strict_success": strict_success,
            "final_name_match": final_name_match,
            "final_exact_match": final_exact_match,
            "db_state_match": local_reward.db_state_match,
            "db_hash_match": local_reward.db_hash_match,
            "local_db_reward": local_reward.local_db_reward,
            "local_communicate_reward": local_reward.local_communicate_reward,
            "local_nl_assertion_reward": local_reward.local_nl_assertion_reward,
            "reward_basis": local_reward.reward_basis,
            "db_mismatch_summary": local_reward.db_mismatch_summary,
            "accuracy": round(accuracy, 3),
            "exact_action_accuracy": round(self._exact_action_accuracy(gold_action_calls, predicted_calls), 3),
            "violation_count": executed_violation_count,
            "executed_violation_count": executed_violation_count,
            "rejected_violation_count": rejected_violation_count,
            "invalid_count": invalid_count,
            "execution_errors": execution_errors,
            "local_reward": local_reward.to_dict(),
            "evaluator_name": local_reward.evaluator_name,
            "evaluator_scope": local_reward.evaluator_scope,
            "official_tau_bench_available": local_reward.official_tau_bench_available,
            "coverage_warning_count": len(local_reward.coverage_warnings),
            "repair_count": repair_count,
            "grounding_change_count": grounding_change_count,
            "grounding_rejection_count": grounding_rejection_count,
            "progress_rejection_count": progress_rejection_count,
            "retrieved_case_ids": retrieved_case_ids_seen,
            "retrieved_case_count": len(retrieved_case_ids_seen),
            "suggestion_count_total": suggestion_count_total,
            "suggestion_fallback_count": suggestion_fallback_count,
            "update_suggestion_fallback_count": update_suggestion_fallback_count,
            "num_steps": len(predicted),
            "total_time": round(elapsed, 2),
            "step_details": step_details,
        }

    def _prefix_accuracy(self, gold: List[str], predicted: List[str]) -> float:
        """Calculate prefix match accuracy."""
        if not gold:
            return 0.0
        predicted = [name for name in predicted if name != "finish_task"]
        matches = 0
        for i in range(min(len(gold), len(predicted))):
            if gold[i] == predicted[i]:
                matches += 1
            else:
                break
        return matches / len(gold)

    def _exact_action_accuracy(self, gold: List[Dict[str, Any]], predicted: List[Dict[str, Any]]) -> float:
        """Prefix accuracy with both action name and arguments."""
        if not gold:
            return 0.0
        predicted = [call for call in predicted if call.get("action") != "finish_task"]
        matches = 0
        for i in range(min(len(gold), len(predicted))):
            if self._actions_match(predicted[i], gold[i]):
                matches += 1
            else:
                break
        return matches / len(gold)

    def _actions_match(self, predicted: Optional[Dict[str, Any]], gold: Optional[Dict[str, Any]]) -> bool:
        if not predicted or not gold:
            return False
        return (
            predicted.get("action") == gold.get("action")
            and predicted.get("arguments", {}) == gold.get("arguments", {})
        )


# ============================================================================
# Main
# ============================================================================

def run_experiments(
    model: str,
    base_url: str,
    api_key: str,
    num_tasks: Optional[int] = None,
    output_dir: str = "results",
    max_steps: int = 15,
    use_kimi_cli: bool = False,
    planner_filter: Optional[List[str]] = None,
    require_official_evaluator: bool = False,
):
    """Run all experiments and save results."""
    print(f"\n{'='*60}")
    print(f"Experiment Start: {datetime.now().isoformat()}")
    print(f"Model: {model}")
    print(f"Base URL: {base_url}")
    print(f"{'='*60}\n")

    # Load data
    db = RetailDB.load(BASE_DIR / "data/raw/retail/db.json")
    all_tasks = load_tasks(BASE_DIR / "data/raw/retail/tasks.json")
    split_data = load_split(BASE_DIR / "data/raw/retail/split_tasks.json")
    action_bank = ActionBank.from_json(BASE_DIR / "data/action_bank/retail_action_bank.json")

    test_ids = set(split_data.get("test", []))
    train_ids = set(split_data.get("train", []))
    test_tasks = [t for t in all_tasks if t.task_id in test_ids]
    train_tasks = [t for t in all_tasks if t.task_id in train_ids]
    if num_tasks is not None:
        test_tasks = test_tasks[:num_tasks]

    print(f"Loaded {len(test_tasks)} test tasks and {len(train_tasks)} train cases")

    # Create LLM client
    if use_kimi_cli:
        from kimi_cli_client import KimiCLIClient
        llm = KimiCLIClient(model=model)
    else:
        llm = OpenAIClient(model=model, base_url=base_url, api_key=api_key)
    verifier = ConstraintVerifier(action_bank)
    runner = ExperimentRunner(db, action_bank, verifier, max_steps=max_steps)
    if require_official_evaluator and not runner.evaluator.official_tau_bench_available:
        raise RuntimeError(
            "Official tau-bench package is not available in this environment. "
            "Install tau-bench/tau2-bench or rerun without --require-official-evaluator to use local DB-hash evaluation."
        )
    case_retriever = CaseRetriever(train_tasks, runner.db_dict, top_k=3)

    # Planners (including ablations)
    planners = {
        "Schema-Only": SchemaPlanner(llm, action_bank),
        "DupOnly": DuplicateOnlyPlanner(llm, action_bank),
        "PrecondOnly": PreconditionOnlyPlanner(llm, action_bank),
        "BlockingNoRepair": BlockingNoRepairPlanner(llm, action_bank),
        "OursNoCases": OursPlanner(llm, action_bank, verifier, max_repair=2, case_retriever=None),
        "Ours": OursPlanner(llm, action_bank, verifier, max_repair=2, case_retriever=case_retriever),
    }
    if planner_filter:
        unknown = sorted(set(planner_filter) - set(planners))
        if unknown:
            raise ValueError(f"Unknown planners requested: {unknown}. Available: {sorted(planners)}")
        planners = {name: planners[name] for name in planner_filter}

    # Output directory
    out_dir = pathlib.Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_results = {}

    for planner_name, planner in planners.items():
        print(f"\n{'-'*60}")
        print(f"Running: {planner_name}")
        print(f"{'-'*60}")

        planner_results = []
        for i, task in enumerate(test_tasks):
            print(f"\n[{i+1}/{len(test_tasks)}] Task {task.task_id}...", end=" ", flush=True)
            try:
                result = runner.run_task(task, planner, planner_name)
                planner_results.append(result)
                status = "SUCCESS" if result["success"] else "FAIL"
                effective_final = result.get("predicted_effective_final_call") or result.get("predicted_final_call")
                effective_name = effective_final.get("action") if isinstance(effective_final, dict) else result["predicted_final"]
                print(f"{status} (effective_final={effective_name}, gold={result['gold_final']}, time={result['total_time']:.1f}s)")
            except Exception as e:
                print(f"ERROR: {e}")
                planner_results.append({
                    "task_id": task.task_id,
                    "planner": planner_name,
                    "error": str(e),
                })

        all_results[planner_name] = planner_results

        # Save per-planner results
        planner_file = out_dir / f"{planner_name.replace('-', '_').lower()}_{timestamp}.json"
        with open(planner_file, "w") as f:
            json.dump(planner_results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {planner_name} results to: {planner_file}")

    # Save combined results
    combined_file = out_dir / f"all_results_{timestamp}.json"
    with open(combined_file, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"Saved combined results to: {combined_file}")

    # Print summary
    print_summary(all_results)

    return all_results


def print_summary(all_results: Dict[str, List[Dict]]):
    """Print experiment summary."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for planner_name, results in all_results.items():
        valid_results = [r for r in results if "error" not in r]
        if not valid_results:
            continue

        total = len(valid_results)
        success = sum(1 for r in valid_results if r.get("success", False))
        strict_success = sum(1 for r in valid_results if r.get("strict_success", False))
        local_db_reward = sum(
            1 for r in valid_results
            if r.get("local_db_reward", r.get("db_hash_match", r.get("db_state_match", False)))
        )
        avg_acc = sum(r.get("accuracy", 0) for r in valid_results) / total
        avg_exact_acc = sum(r.get("exact_action_accuracy", 0) for r in valid_results) / total
        total_violations = sum(r.get("violation_count", 0) for r in valid_results)
        total_rejected_violations = sum(r.get("rejected_violation_count", 0) for r in valid_results)
        total_invalids = sum(r.get("invalid_count", 0) for r in valid_results)
        total_repairs = sum(r.get("repair_count", 0) for r in valid_results)
        total_grounding_changes = sum(r.get("grounding_change_count", 0) for r in valid_results)
        total_grounding_rejections = sum(r.get("grounding_rejection_count", 0) for r in valid_results)
        total_progress_rejections = sum(r.get("progress_rejection_count", 0) for r in valid_results)
        tasks_with_cases = sum(1 for r in valid_results if r.get("retrieved_case_count", 0) > 0)
        total_suggestions = sum(r.get("suggestion_count_total", 0) for r in valid_results)
        total_suggestion_fallbacks = sum(r.get("suggestion_fallback_count", 0) for r in valid_results)
        total_update_suggestion_fallbacks = sum(r.get("update_suggestion_fallback_count", 0) for r in valid_results)
        total_coverage_warnings = sum(r.get("coverage_warning_count", 0) for r in valid_results)
        avg_time = sum(r.get("total_time", 0) for r in valid_results) / total
        evaluator_names = sorted(set(r.get("evaluator_name", "unknown") for r in valid_results))
        official_available = any(r.get("official_tau_bench_available", False) for r in valid_results)

        print(f"\n{planner_name}:")
        print(f"  Tasks: {total}")
        print(f"  Local DB Reward: {local_db_reward}/{total} = {100*local_db_reward/total:.1f}%")
        print(f"  Local DB Success Rate: {success}/{total} = {100*success/total:.1f}%")
        print(f"  Strict Success Rate: {strict_success}/{total} = {100*strict_success/total:.1f}%")
        print(f"  Avg Name-Prefix Accuracy: {avg_acc*100:.1f}%")
        print(f"  Avg Exact-Prefix Accuracy: {avg_exact_acc*100:.1f}%")
        print(f"  Executed Violations: {total_violations}")
        print(f"  Rejected Violations: {total_rejected_violations}")
        print(f"  Total Invalid Actions: {total_invalids}")
        print(f"  Total Repairs: {total_repairs}")
        print(f"  Grounding Changes: {total_grounding_changes}")
        print(f"  Grounding Rejections: {total_grounding_rejections}")
        print(f"  Progress Rejections: {total_progress_rejections}")
        print(f"  Tasks with Retrieved Train Cases: {tasks_with_cases}/{total}")
        print(f"  Total Suggested Actions: {total_suggestions}")
        print(f"  Suggestion Fallbacks Used: {total_suggestion_fallbacks}")
        print(f"  Update Suggestion Fallbacks Used: {total_update_suggestion_fallbacks}")
        print(f"  Evaluator: {evaluator_names} (official_tau_bench_available={official_available})")
        print(f"  Coverage Warnings: {total_coverage_warnings}")
        print(f"  Avg Time: {avg_time:.1f}s")

        # Violation type breakdown
        vtype_counts = {}
        for r in valid_results:
            for step in r.get("step_details", []):
                for v in step.get("verifier_violations", []):
                    vtype = v.split(":")[0] if ":" in v else "OTHER"
                    vtype_counts[vtype] = vtype_counts.get(vtype, 0) + 1
        if vtype_counts:
            print(f"  Violation types: {vtype_counts}")

        # Per-task breakdown
        print(f"  Per-task results:")
        for r in valid_results:
            status = "✓" if r.get("success") else "✗"
            effective_final = r.get("predicted_effective_final_call") or r.get("predicted_final_call") or {}
            effective_name = effective_final.get("action", r.get("predicted_final"))
            print(
                f"    {status} Task {r['task_id']}: effective_final={effective_name} "
                f"(gold={r['gold_final']}) name_acc={r['accuracy']*100:.0f}% "
                f"exact_acc={r.get('exact_action_accuracy', 0)*100:.0f}%"
            )


def main():
    parser = argparse.ArgumentParser(description="Run agent planning experiments")
    parser.add_argument("--model", default="./models/Qwen3.6-27B", help="Model name")
    parser.add_argument("--base-url", default="http://172.16.22.79:9999/qwen36/v1", help="API base URL")
    parser.add_argument("--api-key", default="EMPTY", help="API key")
    parser.add_argument("--num-tasks", type=int, default=None, help="Number of tasks to run (default: all)")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    parser.add_argument("--max-steps", type=int, default=15, help="Max steps per task")
    parser.add_argument("--use-kimi-cli", action="store_true", help="Use Kimi CLI instead of HTTP API")
    parser.add_argument("--planners", nargs="+", default=None, help="Planner names to run, e.g. Schema-Only Ours")
    parser.add_argument(
        "--require-official-evaluator",
        action="store_true",
        help="Fail fast unless an official tau-bench evaluator package is importable.",
    )
    args = parser.parse_args()

    run_experiments(
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        num_tasks=args.num_tasks,
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        use_kimi_cli=args.use_kimi_cli,
        planner_filter=args.planners,
        require_official_evaluator=args.require_official_evaluator,
    )


if __name__ == "__main__":
    main()
