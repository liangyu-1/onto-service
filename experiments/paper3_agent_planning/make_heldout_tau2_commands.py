#!/usr/bin/env python3
"""Generate held-out tau2 commands that exclude previously debugged tasks."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXCLUDE = {"0", "1", "2", "3", "4", "5", "6", "8", "9", "11"}


def load_split(split_name: str) -> list[str]:
    with open(BASE_DIR / "data/raw/retail/split_tasks.json") as f:
        data = json.load(f)
    task_ids = data.get(split_name)
    if not isinstance(task_ids, list):
        raise ValueError(f"Unknown split {split_name!r}; available splits: {sorted(data)}")
    return [str(task_id) for task_id in task_ids]


def shell_join(items: list[str]) -> str:
    return " ".join(items)


def build_command(args: argparse.Namespace, agent_kind: str, save_to: str, task_ids: list[str]) -> str:
    parts = [
        "python",
        "experiments/paper3_agent_planning/tau2_ontology_agent.py",
        "\\\n  --domain",
        args.domain,
        "\\\n  --agent-kind",
        agent_kind,
        "\\\n  --agent-model",
        args.agent_model,
        "\\\n  --agent-base-url",
        args.agent_base_url,
        "\\\n  --api-key",
        '"$AGENT_API_KEY"',
        "\\\n  --user-llm",
        args.user_llm,
        "\\\n  --task-split-name",
        args.split,
        "\\\n  --task-ids",
        shell_join(task_ids),
        "\\\n  --num-trials",
        str(args.num_trials),
        "\\\n  --max-concurrency",
        str(args.max_concurrency),
        "\\\n  --max-steps",
        str(args.max_steps),
        "\\\n  --save-to",
        save_to,
    ]
    return " ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate held-out tau2 evaluation commands.")
    parser.add_argument("--split", default="base", help="Split name in data/raw/retail/split_tasks.json.")
    parser.add_argument("--num-tasks", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--exclude", nargs="*", default=sorted(DEFAULT_EXCLUDE))
    parser.add_argument("--domain", default="retail")
    parser.add_argument("--agent-model", default="GLM-5.1")
    parser.add_argument("--agent-base-url", default="https://open.bigmodel.cn/api/coding/paas/v4")
    parser.add_argument("--user-llm", default="openai/GLM-5.1")
    parser.add_argument("--num-trials", type=int, default=2)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--save-prefix", default="heldout_retail")
    args = parser.parse_args()

    candidates = [task_id for task_id in load_split(args.split) if task_id not in set(args.exclude)]
    if args.num_tasks > len(candidates):
        raise ValueError(
            f"Requested {args.num_tasks} tasks, but only {len(candidates)} remain after exclusions."
        )
    rng = random.Random(args.seed)
    task_ids = sorted(rng.sample(candidates, args.num_tasks), key=lambda value: int(value))

    print("# Held-out task ids")
    print(" ".join(task_ids))
    print()
    print("# Schema baseline")
    print(build_command(args, "schema", f"{args.save_prefix}_schema_seed{args.seed}", task_ids))
    print()
    print("# Ontology full")
    print(build_command(args, "ontology_full", f"{args.save_prefix}_ontology_seed{args.seed}", task_ids))


if __name__ == "__main__":
    main()
