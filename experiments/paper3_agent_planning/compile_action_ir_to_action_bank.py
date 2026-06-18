#!/usr/bin/env python3
"""Compile canonical Action IR into the runtime ActionBank JSON used by Paper3."""
from __future__ import annotations

import argparse
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from action_bank import ActionBank  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(BASE_DIR / "data/action_ir/retail_action_ir.json"),
        help="Canonical Action IR JSON.",
    )
    parser.add_argument(
        "--output",
        default=str(BASE_DIR / "data/action_bank/retail_action_bank.json"),
        help="Runtime ActionBank JSON.",
    )
    args = parser.parse_args()

    action_bank = ActionBank.from_action_ir_json(pathlib.Path(args.input))
    action_bank.save(pathlib.Path(args.output))
    print(f"Compiled {len(action_bank.list_actions())} actions: {args.input} -> {args.output}")


if __name__ == "__main__":
    main()
