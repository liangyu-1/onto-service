"""Agent 1: DocumentSynthesizer — generates synthetic procedural documents."""
from __future__ import annotations

import json
import pathlib
import random
import re
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan, ProcedureGraph, SyntheticDocument
from utils import write_jsonl


class DocumentSynthesizer:
    """Generates synthetic SOPs/procedural documents from action schemas and task traces.

    Each document is grounded in a gold action sequence from tau-bench tasks,
    rendered as natural-language procedural text with headings, numbered steps,
    conditions, warnings, and tables.
    """

    def __init__(
        self,
        action_bank_path: pathlib.Path,
        tasks_path: pathlib.Path,
        split_path: pathlib.Path,
        seed: int = 42,
    ):
        with open(action_bank_path) as f:
            self.action_bank = json.load(f)
        with open(tasks_path) as f:
            self.tasks = json.load(f)
        with open(split_path) as f:
            self.split = json.load(f)
        random.seed(seed)

    def _action_to_text(self, action: Dict[str, Any]) -> str:
        """Convert an action call to a natural-language instruction."""
        name = action["name"]
        args = action.get("arguments", {})

        templates = {
            "find_user_id_by_email": lambda a: f"Find the user by their email address {a.get('email', '[email]')}.",
            "find_user_id_by_name_zip": lambda a: f"Look up the user using name {a.get('first_name', '')} {a.get('last_name', '')} and zip code {a.get('zip', '')}.",
            "get_user_details": lambda a: f"Retrieve detailed information for the user (ID: {a.get('user_id', '')}).",
            "get_order_details": lambda a: f"Get the details of order {a.get('order_id', '')}.",
            "get_product_details": lambda a: f"Look up product details for product ID {a.get('product_id', '')}.",
            "get_item_details": lambda a: f"Retrieve item details for item ID {a.get('item_id', '')}.",
            "list_all_product_types": lambda a: "List all available product types in the catalog.",
            "cancel_pending_order": lambda a: f"Cancel the pending order {a.get('order_id', '')}. Reason: {a.get('reason', '')}.",
            "modify_pending_order_address": lambda a: f"Update the shipping address for pending order {a.get('order_id', '')}.",
            "modify_pending_order_items": lambda a: f"Modify items in pending order {a.get('order_id', '')}: replace {a.get('item_ids', [])} with {a.get('new_item_ids', [])}.",
            "modify_pending_order_payment": lambda a: f"Change the payment method for pending order {a.get('order_id', '')} to {a.get('payment_method_id', '')}.",
            "modify_user_address": lambda a: f"Update the user's default address to the new address provided.",
            "return_delivered_order_items": lambda a: f"Process a return for items {a.get('item_ids', [])} from delivered order {a.get('order_id', '')}.",
            "exchange_delivered_order_items": lambda a: f"Exchange items {a.get('item_ids', [])} for {a.get('new_item_ids', [])} in delivered order {a.get('order_id', '')}.",
            "transfer_to_human_agents": lambda a: f"Transfer the case to a human agent. Summary: {a.get('summary', '')}",
            "calculate": lambda a: f"Perform calculation: {a.get('expression', '')}.",
            "ask_for_confirmation": lambda a: f"Ask the user to confirm: {a.get('action_description', '')}",
            "finish_task": lambda a: "Conclude the task and mark it as complete.",
        }

        if name in templates:
            return templates[name](args)
        return f"Execute action '{name}' with parameters {json.dumps(args)}."

    def _action_to_ir(self, action: Dict[str, Any], schema: Dict[str, Any]) -> ActionIR:
        """Convert a ground-truth action to Action IR."""
        return ActionIR(
            action_id=action.get("action_id", ""),
            action_type=action["name"],
            actor="agent",
            target=action.get("arguments", {}).get("order_id", "") or action.get("arguments", {}).get("user_id", ""),
            target_type=schema.get("target_object", ""),
            parameters=action.get("arguments", {}),
            preconditions=schema.get("preconditions", []),
            effects=schema.get("effects", []),
            constraints=schema.get("constraints", []),
            evidence={},
            grounding={
                "action_type_grounded": True,
                "target_type_grounded": bool(schema.get("target_object", "")),
            },
            control_flow={},
            confidence=1.0,
            resolved=True,
        )

    def _render_doc(
        self,
        task: Dict[str, Any],
        doc_id: str,
        style: str = "sop",
    ) -> SyntheticDocument:
        """Render a task's gold action sequence as a procedural document."""
        actions = task.get("evaluation_criteria", {}).get("actions", [])
        user_scenario = task.get("user_scenario", {})
        instructions = user_scenario.get("instructions", {})
        reason = instructions.get("reason_for_call", "")
        known = instructions.get("known_info", "")

        # Build ground-truth Action IRs
        schemas = {a["action_id"]: a for a in self.action_bank.get("actions", [])}
        gt_actions = []
        for act in actions:
            schema = schemas.get(act["name"], {})
            gt_actions.append(self._action_to_ir(act, schema))

        # Render text
        lines = []
        if style == "sop":
            lines.append(f"# Standard Operating Procedure: Task {doc_id}")
            lines.append("")
            if reason:
                lines.append(f"## Purpose")
                lines.append(reason)
                lines.append("")
            if known:
                lines.append(f"## Known Information")
                lines.append(known)
                lines.append("")
            lines.append("## Procedure")
            for i, act in enumerate(actions, 1):
                text = self._action_to_text(act)
                lines.append(f"{i}. {text}")
                # Add conditionals/warnings based on schema
                schema = schemas.get(act["name"], {})
                preconds = schema.get("preconditions", [])
                constraints = schema.get("constraints", [])
                if preconds:
                    lines.append(f"   **Precondition**: {'; '.join(preconds)}")
                if constraints:
                    lines.append(f"   **Constraint**: {'; '.join(constraints)}")
            lines.append("")
            lines.append("## Completion")
            lines.append("Ensure all steps are completed and the customer is satisfied.")

        elif style == "script":
            lines.append(f"# Customer Service Script: Task {doc_id}")
            lines.append("")
            lines.append(f"**Customer Issue**: {reason}")
            lines.append(f"**Known Facts**: {known}")
            lines.append("")
            lines.append("**Agent Steps**:")
            for i, act in enumerate(actions, 1):
                text = self._action_to_text(act)
                lines.append(f"{i}. {text}")
            lines.append("")
            lines.append("**End of Script**")

        elif style == "manual":
            lines.append(f"# Maintenance Manual: Task {doc_id}")
            lines.append("")
            lines.append(f"## Problem Description")
            lines.append(reason)
            lines.append("")
            lines.append("## Step-by-Step Resolution")
            for i, act in enumerate(actions, 1):
                text = self._action_to_text(act)
                lines.append(f"### Step {i}")
                lines.append(text)
                schema = schemas.get(act["name"], {})
                if schema.get("effects"):
                    lines.append(f"**Expected outcome**: {'; '.join(schema['effects'])}")
            lines.append("")
            lines.append("## Verification")
            lines.append("Confirm all actions completed successfully.")

        full_text = "\n".join(lines)

        # Build ground-truth graph (sequential edges)
        edges = []
        for i in range(len(gt_actions) - 1):
            edges.append({
                "source": gt_actions[i].action_id,
                "target": gt_actions[i + 1].action_id,
                "relation": "sequential",
                "evidence": f"Step {i+1} → Step {i+2}",
            })
        gt_graph = ProcedureGraph(nodes=gt_actions, edges=edges)

        return SyntheticDocument(
            doc_id=doc_id,
            title=f"Task {doc_id}",
            domain="retail",
            text=full_text,
            source_tasks=[doc_id],
            ground_truth_actions=gt_actions,
            ground_truth_graph=gt_graph,
        )

    def generate(
        self,
        split_name: str = "test",
        styles: Optional[List[str]] = None,
        out_path: Optional[pathlib.Path] = None,
    ) -> List[SyntheticDocument]:
        """Generate synthetic documents for a task split."""
        styles = styles or ["sop", "script", "manual"]
        task_ids = self.split.get(split_name, [])
        docs = []

        # Map task IDs to task objects
        task_map = {str(t.get("id", "")): t for t in self.tasks}

        for tid in task_ids:
            task = task_map.get(tid)
            if not task:
                continue
            style = random.choice(styles)
            doc = self._render_doc(task, tid, style=style)
            docs.append(doc)

        if out_path:
            write_jsonl(out_path, [d.to_dict() for d in docs])

        return docs


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-bank", type=pathlib.Path, required=True)
    parser.add_argument("--tasks", type=pathlib.Path, required=True)
    parser.add_argument("--split", type=pathlib.Path, required=True)
    parser.add_argument("--split-name", default="test")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    synth = DocumentSynthesizer(
        action_bank_path=args.action_bank,
        tasks_path=args.tasks,
        split_path=args.split,
        seed=args.seed,
    )
    docs = synth.generate(split_name=args.split_name, out_path=args.out)
    print(f"Generated {len(docs)} synthetic documents → {args.out}")


if __name__ == "__main__":
    main()
