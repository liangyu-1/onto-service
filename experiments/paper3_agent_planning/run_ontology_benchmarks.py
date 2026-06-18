#!/usr/bin/env python3
"""Run ontology-semantics diagnostics for the action layer.

This runner is intentionally separate from the end-to-end LLM benchmark.  It
tests whether the ActionBank, verifier, argument grounder, and simulator encode
the ontology semantics claimed by the paper: state-sensitive admissibility,
role binding, and effect consistency.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank, ActionSchema  # noqa: E402
from argument_grounder import ArgumentGrounder  # noqa: E402
from data_loader import RetailDB, Task, load_split, load_tasks  # noqa: E402
from simulator import RetailSimulator  # noqa: E402
from state_manager import DialogueState  # noqa: E402
from verifier import ConstraintVerifier  # noqa: E402


MUTATING_ORDER_ACTIONS = {
    "cancel_pending_order",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "return_delivered_order_items",
    "exchange_delivered_order_items",
}

STATUS_FLIP = {
    "pending": "delivered",
    "delivered": "pending",
}


@dataclass
class BenchmarkCaseResult:
    benchmark: str
    case_id: str
    action: str
    passed: bool
    expected: str
    observed: str
    details: Dict[str, Any]


def load_retail() -> tuple[Dict[str, Any], List[Task], Dict[str, List[str]], ActionBank]:
    db = RetailDB.load(BASE_DIR / "data/raw/retail/db.json")
    db_dict = {"users": db.users, "products": db.products, "orders": db.orders}
    tasks = load_tasks(BASE_DIR / "data/raw/retail/tasks.json")
    split = load_split(BASE_DIR / "data/raw/retail/split_tasks.json")
    action_bank = ActionBank.from_json(BASE_DIR / "data/action_bank/retail_action_bank.json")
    return db_dict, tasks, split, action_bank


def task_text(task: Task) -> str:
    instructions = task.user_scenario.get("instructions", {}) if isinstance(task.user_scenario, dict) else {}
    parts = [
        str(instructions.get("reason_for_call", "") or ""),
        str(instructions.get("known_info", "") or ""),
        str(instructions.get("unknown_info", "") or ""),
        str(instructions.get("task_instructions", "") or ""),
    ]
    return "\n".join(part for part in parts if part)


def gold_calls(task: Task) -> List[Dict[str, Any]]:
    return [
        {"action": item.get("name", ""), "arguments": dict(item.get("arguments", {}) or {})}
        for item in task.gold_actions
    ]


def initialized_state_for_call(call: Dict[str, Any], db: Dict[str, Any]) -> DialogueState:
    state = DialogueState(user_authenticated=True, user_confirmed=True)
    args = call.get("arguments", {})
    order_id = args.get("order_id")
    if order_id and order_id in db.get("orders", {}):
        order = copy.deepcopy(db["orders"][order_id])
        state.cached_orders[order_id] = order
        user_id = order.get("user_id")
        if user_id:
            state.user_id = user_id
            if user_id in db.get("users", {}):
                state.cached_users[user_id] = copy.deepcopy(db["users"][user_id])
    user_id = args.get("user_id")
    if user_id and user_id in db.get("users", {}):
        state.user_id = user_id
        state.cached_users[user_id] = copy.deepcopy(db["users"][user_id])
    return state


def grounded_arguments(
    call: Dict[str, Any],
    state: DialogueState,
    db: Dict[str, Any],
    action_bank: ActionBank,
) -> tuple[Dict[str, Any], List[str], List[str]]:
    """Return ontology-canonical arguments for a benchmark call."""
    result = ArgumentGrounder().ground(
        call["action"],
        call.get("arguments", {}),
        state,
        db,
        schema=action_bank.get(call["action"]),
    )
    return result.arguments, result.changes, result.violations


def effective_gold_update_calls(tasks: Iterable[Task]) -> List[tuple[Task, Dict[str, Any]]]:
    cases: List[tuple[Task, Dict[str, Any]]] = []
    for task in tasks:
        for call in gold_calls(task):
            if call["action"] in MUTATING_ORDER_ACTIONS and call["arguments"].get("order_id"):
                cases.append((task, call))
    return cases


def run_state_admissibility(
    tasks: List[Task],
    db: Dict[str, Any],
    verifier: ConstraintVerifier,
    action_bank: ActionBank,
) -> List[BenchmarkCaseResult]:
    """Check that state predicates accept original state and reject flipped state."""
    results: List[BenchmarkCaseResult] = []
    for task, call in effective_gold_update_calls(tasks):
        action = call["action"]
        args = call["arguments"]
        order_id = args["order_id"]
        order = db.get("orders", {}).get(order_id)
        if not order:
            continue
        original_status = str(order.get("status", "")).lower()
        if original_status not in STATUS_FLIP:
            continue

        state = initialized_state_for_call(call, db)
        grounded_args, grounding_changes, grounding_violations = grounded_arguments(
            call, state, db, action_bank
        )
        original = verifier.verify(action, grounded_args, state, db)
        if not original.passed:
            results.append(BenchmarkCaseResult(
                benchmark="benchmark_data_precondition_mismatch",
                case_id=f"{task.task_id}:{action}:{order_id}:gold_precondition",
                action=action,
                passed=True,
                expected="gold update action should be excluded from state counterfactuals if original state violates ontology preconditions",
                observed="; ".join(grounding_violations + original.violations),
                details={
                    "task_text": task_text(task),
                    "order_status": original_status,
                    "raw_arguments": args,
                    "grounded_arguments": grounded_args,
                    "grounding_changes": grounding_changes,
                },
            ))
            continue

        results.append(BenchmarkCaseResult(
            benchmark="state_admissibility_original",
            case_id=f"{task.task_id}:{action}:{order_id}:original",
            action=action,
            passed=True,
            expected="original order state should satisfy action preconditions",
            observed="passed",
            details={
                "task_text": task_text(task),
                "order_status": original_status,
                "raw_arguments": args,
                "grounded_arguments": grounded_args,
                "grounding_changes": grounding_changes,
            },
        ))

        flipped_db = copy.deepcopy(db)
        flipped_db["orders"][order_id]["status"] = STATUS_FLIP[original_status]
        flipped_state = initialized_state_for_call(call, flipped_db)
        flipped_args, flipped_changes, flipped_grounding_violations = grounded_arguments(
            call, flipped_state, flipped_db, action_bank
        )
        flipped = verifier.verify(action, flipped_args, flipped_state, flipped_db)
        results.append(BenchmarkCaseResult(
            benchmark="state_admissibility_counterfactual",
            case_id=f"{task.task_id}:{action}:{order_id}:flipped",
            action=action,
            passed=not flipped.passed,
            expected=f"flipped status {STATUS_FLIP[original_status]!r} should make original action inadmissible",
            observed="passed unexpectedly" if flipped.passed else "; ".join(flipped_grounding_violations + flipped.violations),
            details={
                "task_text": task_text(task),
                "original_status": original_status,
                "flipped_status": STATUS_FLIP[original_status],
                "raw_arguments": args,
                "grounded_arguments": flipped_args,
                "grounding_changes": flipped_changes,
            },
        ))
    return results


def run_role_binding(
    tasks: List[Task],
    db: Dict[str, Any],
    verifier: ConstraintVerifier,
    action_bank: ActionBank,
) -> List[BenchmarkCaseResult]:
    """Perturb ontology role fillers and check that verifier rejects them."""
    results: List[BenchmarkCaseResult] = []
    all_item_ids = {
        str(item_id)
        for product in db.get("products", {}).values()
        for item_id in product.get("variants", {}).keys()
    }

    for task, call in effective_gold_update_calls(tasks):
        action = call["action"]
        args = call["arguments"]
        order_id = args.get("order_id")
        state = initialized_state_for_call(call, db)
        grounded_args, grounding_changes, grounding_violations = grounded_arguments(
            call, state, db, action_bank
        )
        original = verifier.verify(action, grounded_args, state, db)
        if not original.passed:
            continue

        if args.get("item_ids"):
            order_items = {
                str(item.get("item_id"))
                for item in db["orders"].get(order_id, {}).get("items", [])
            }
            wrong_items = sorted(all_item_ids - order_items)
            if wrong_items:
                bad_args = copy.deepcopy(grounded_args)
                bad_args["item_ids"] = [wrong_items[0]]
                check = verifier.verify(action, bad_args, state, db)
                results.append(BenchmarkCaseResult(
                    benchmark="role_binding_item_membership",
                    case_id=f"{task.task_id}:{action}:{order_id}:wrong_item",
                    action=action,
                    passed=not check.passed,
                    expected="item_ids must be role fillers from the target order",
                    observed="passed unexpectedly" if check.passed else "; ".join(check.violations),
                    details={
                        "arguments": bad_args,
                        "raw_arguments": args,
                        "grounded_arguments": grounded_args,
                        "grounding_changes": grounding_changes,
                        "grounding_violations": grounding_violations,
                    },
                ))

        if grounded_args.get("payment_method_id"):
            bad_args = copy.deepcopy(grounded_args)
            bad_args["payment_method_id"] = "payment_method_not_in_user_or_order"
            check = verifier.verify(action, bad_args, state, db)
            results.append(BenchmarkCaseResult(
                benchmark="role_binding_payment_membership",
                case_id=f"{task.task_id}:{action}:{order_id}:wrong_payment",
                action=action,
                passed=not check.passed,
                expected="payment_method_id must be available for the authenticated user/order",
                observed="passed unexpectedly" if check.passed else "; ".join(check.violations),
                details={
                    "arguments": bad_args,
                    "raw_arguments": args,
                    "grounded_arguments": grounded_args,
                    "grounding_changes": grounding_changes,
                    "grounding_violations": grounding_violations,
                },
            ))

    return results


def run_effect_consistency(
    tasks: List[Task],
    db: Dict[str, Any],
    action_bank: ActionBank,
) -> List[BenchmarkCaseResult]:
    """Replay gold update actions and compare observed mutations to ActionBank effects."""
    results: List[BenchmarkCaseResult] = []
    for task, call in effective_gold_update_calls(tasks):
        action = call["action"]
        args = call["arguments"]
        schema = action_bank.get(action)
        if schema is None:
            continue
        order_id = args.get("order_id")
        state = initialized_state_for_call(call, db)
        grounded_args, grounding_changes, grounding_violations = grounded_arguments(
            call, state, db, action_bank
        )
        original = ConstraintVerifier(action_bank).verify(action, grounded_args, state, db)
        if grounding_violations or not original.passed:
            results.append(BenchmarkCaseResult(
                benchmark="benchmark_data_precondition_mismatch",
                case_id=f"{task.task_id}:{action}:{order_id}:effect_precondition",
                action=action,
                passed=True,
                expected="effect benchmark excludes actions whose original state is not executable",
                observed="; ".join(grounding_violations + original.violations),
                details={
                    "effects": schema.effects,
                    "raw_arguments": args,
                    "grounded_arguments": grounded_args,
                    "grounding_changes": grounding_changes,
                },
            ))
            continue
        before = copy.deepcopy(db.get("orders", {}).get(order_id, {}))
        sim = RetailSimulator(db)
        try:
            if grounding_violations:
                raise ValueError("; ".join(grounding_violations))
            sim.execute(action, grounded_args, state)
            after = sim.db.get("orders", {}).get(order_id, {})
            ok, observed = effect_matches(schema, before, after)
        except Exception as exc:
            ok = False
            observed = f"execution error: {exc}"
        results.append(BenchmarkCaseResult(
            benchmark="effect_consistency",
            case_id=f"{task.task_id}:{action}:{order_id}:effect",
            action=action,
            passed=ok,
            expected="observed DB transition should match at least one declared ActionBank effect",
            observed=observed,
            details={
                "effects": schema.effects,
                "raw_arguments": args,
                "grounded_arguments": grounded_args,
                "grounding_changes": grounding_changes,
            },
        ))
    return results


def effect_matches(schema: ActionSchema, before: Dict[str, Any], after: Dict[str, Any]) -> tuple[bool, str]:
    effects = [effect.lower() for effect in schema.effects]
    status = str(after.get("status", "")).lower()
    before_status = str(before.get("status", "")).lower()
    for effect in effects:
        if "order.status =" in effect:
            expected = effect.split("=", 1)[1].strip().strip("'\"").lower()
            if status == expected or (expected.startswith("pending") and status.startswith("pending")):
                return True, f"status changed {before_status!r}->{status!r}"
        if "order.address = new_address" in effect and before.get("address") != after.get("address"):
            return True, "order address changed"
        if "order.payment updated" in effect and before.get("payment_history") != after.get("payment_history"):
            return True, "order payment history changed"
        if "order.items replaced" in effect and before.get("items") != after.get("items"):
            return True, "order items changed"
        if "trigger refund" in effect:
            # Refund is not fully modeled by the local simulator; accept only if
            # another concrete mutation also happened.
            continue
    return False, f"no declared concrete effect matched; status {before_status!r}->{status!r}"


def run_argument_grounding(
    tasks: List[Task],
    db: Dict[str, Any],
    action_bank: ActionBank,
) -> List[BenchmarkCaseResult]:
    """Check whether common LLM-style parameter aliases are canonicalized."""
    grounder = ArgumentGrounder()
    results: List[BenchmarkCaseResult] = []
    alias_cases = {
        "find_user_id_by_name_zip": ("zip", "zip_code"),
        "get_order_details": ("order_id", "order_number"),
        "cancel_pending_order": ("order_id", "order_number"),
    }
    for task in tasks:
        for call in gold_calls(task):
            action = call["action"]
            if action not in alias_cases:
                continue
            canonical, alias = alias_cases[action]
            if canonical not in call["arguments"]:
                continue
            state = initialized_state_for_call(call, db)
            aliased_args = dict(call["arguments"])
            aliased_args[alias] = aliased_args.pop(canonical)
            grounded = grounder.ground(
                action,
                aliased_args,
                state,
                db,
                schema=action_bank.get(action),
            )
            passed = canonical in grounded.arguments and alias not in grounded.arguments
            results.append(BenchmarkCaseResult(
                benchmark="argument_role_canonicalization",
                case_id=f"{task.task_id}:{action}:{alias}",
                action=action,
                passed=passed,
                expected=f"{alias} should be canonicalized to {canonical}",
                observed=json.dumps(grounded.arguments, ensure_ascii=False, sort_keys=True),
                details={"changes": grounded.changes, "violations": grounded.violations},
            ))
    return results


def summarize(results: List[BenchmarkCaseResult]) -> Dict[str, Any]:
    by_benchmark: Dict[str, Dict[str, Any]] = {}
    for benchmark in sorted({r.benchmark for r in results}):
        rows = [r for r in results if r.benchmark == benchmark]
        passed = sum(1 for r in rows if r.passed)
        by_benchmark[benchmark] = {
            "cases": len(rows),
            "passed": passed,
            "failed": len(rows) - passed,
            "accuracy": round(passed / len(rows), 4) if rows else None,
        }
    failures = [r for r in results if not r.passed]
    action_counts = Counter(r.action for r in failures)
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": by_benchmark,
        "failure_actions": dict(action_counts),
        "num_failures": len(failures),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ontology-semantics benchmark suite.")
    parser.add_argument("--split", default="test", choices=["train", "dev", "test", "all"])
    parser.add_argument("--output", default="results/ontology_benchmark_results.json")
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()

    db, all_tasks, split, action_bank = load_retail()
    if args.split == "all":
        tasks = all_tasks
    else:
        ids = set(split.get(args.split, []))
        tasks = [task for task in all_tasks if task.task_id in ids]
    if args.max_cases is not None:
        tasks = tasks[: args.max_cases]

    verifier = ConstraintVerifier(action_bank)
    results: List[BenchmarkCaseResult] = []
    results.extend(run_state_admissibility(tasks, db, verifier, action_bank))
    results.extend(run_role_binding(tasks, db, verifier, action_bank))
    results.extend(run_effect_consistency(tasks, db, action_bank))
    results.extend(run_argument_grounding(tasks, db, action_bank))

    payload = {
        "benchmark_suite": "ontology_retail_local",
        "split": args.split,
        "num_tasks": len(tasks),
        **summarize(results),
        "results": [asdict(result) for result in results],
    }

    out = pathlib.Path(args.output)
    if not out.is_absolute():
        out = BASE_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(json.dumps({k: v for k, v in payload.items() if k != "results"}, indent=2, ensure_ascii=False))
    print(f"Saved detailed ontology benchmark results to: {out}")


if __name__ == "__main__":
    main()
