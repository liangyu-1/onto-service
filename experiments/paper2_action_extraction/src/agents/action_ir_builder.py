"""Agent 4: ActionIRBuilder — compiles procedural units into Action IR records."""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan, ProceduralUnit
from llm_client import LLMClient


ACTION_IR_BUILD_PROMPT = """You are an Action IR builder. Given a set of procedural units (operations, conditions, constraints, exceptions) extracted from a document, compile them into structured Action IR records.

Each Action IR record must contain:
- action_type: the action name (e.g., "find_user_id_by_email", "cancel_pending_order")
- actor: who performs the action (e.g., "agent", "user", "system")
- target: the object the action operates on (e.g., order ID, user ID)
- target_type: the ontology object type (e.g., "User", "Order", "Product")
- parameters: a dict of parameter names to values
- preconditions: list of precondition strings
- effects: list of effect strings
- constraints: list of constraint strings
- evidence: dict mapping field names to lists of evidence text spans

Output as JSON:
{
  "actions": [
    {
      "action_type": "...",
      "actor": "...",
      "target": "...",
      "target_type": "...",
      "parameters": {...},
      "preconditions": [...],
      "effects": [...],
      "constraints": [...],
      "evidence": {"action_type": ["..."], "parameters": ["..."], ...}
    }
  ]
}

Procedural units:
"""


class ActionIRBuilder:
    """Compiles procedural units into Action IR records.

    Uses LLM for semantic compilation, with rule-based fallback for
    simple cases (single operation unit → single action).
    """

    def __init__(self, llm: Optional[LLMClient] = None, use_llm: bool = True):
        self.llm = llm
        self.use_llm = use_llm and llm is not None

        # Action type keyword mapping for rule-based fallback
        self.action_keywords = {
            "find_user_id_by_email": ["email", "find user", "by email"],
            "find_user_id_by_name_zip": ["name", "zip", "look up user"],
            "get_user_details": ["user details", "user information"],
            "get_order_details": ["order details", "get order"],
            "get_product_details": ["product details", "product information"],
            "get_item_details": ["item details", "item information"],
            "list_all_product_types": ["list products", "product types"],
            "cancel_pending_order": ["cancel", "pending order"],
            "modify_pending_order_address": ["address", "shipping address"],
            "modify_pending_order_items": ["modify items", "replace items", "change items"],
            "modify_pending_order_payment": ["payment", "payment method"],
            "modify_user_address": ["user address", "update address"],
            "return_delivered_order_items": ["return", "delivered"],
            "exchange_delivered_order_items": ["exchange", "delivered"],
            "transfer_to_human_agents": ["transfer", "human agent"],
            "calculate": ["calculate", "computation"],
            "ask_for_confirmation": ["confirm", "confirmation"],
            "finish_task": ["complete", "finish", "done"],
        }

    def _match_action_type(self, text: str) -> Optional[str]:
        """Rule-based action type matching."""
        text_lower = text.lower()
        best_match = None
        best_score = 0
        for action_id, keywords in self.action_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_match = action_id
        return best_match if best_score >= 1 else None

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Rule-based parameter extraction from text."""
        params = {}

        # Email
        email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", text)
        if email_match:
            params["email"] = email_match.group(0)

        # Order ID (e.g., #W2378156)
        order_match = re.search(r"#\w+", text)
        if order_match:
            params["order_id"] = order_match.group(0)

        # Name + zip
        name_match = re.search(r"name\s+([A-Za-z]+)\s+([A-Za-z]+)", text, re.IGNORECASE)
        if name_match:
            params["first_name"] = name_match.group(1)
            params["last_name"] = name_match.group(2)

        zip_match = re.search(r"zip\s+(\d+)", text, re.IGNORECASE)
        if zip_match:
            params["zip"] = zip_match.group(1)

        # Product/item IDs
        pid_match = re.search(r"product\s+ID\s+(\d+)", text, re.IGNORECASE)
        if pid_match:
            params["product_id"] = pid_match.group(1)

        iid_match = re.search(r"item\s+ID\s+(\d+)", text, re.IGNORECASE)
        if iid_match:
            params["item_id"] = iid_match.group(1)

        # Reason
        reason_match = re.search(r"reason:\s*(.+?)(?:\.|$)", text, re.IGNORECASE)
        if reason_match:
            params["reason"] = reason_match.group(1).strip()

        # Lists of IDs
        ids_match = re.search(r"items?\s+([\d,\s]+)", text, re.IGNORECASE)
        if ids_match:
            ids_str = ids_match.group(1)
            ids = [x.strip() for x in ids_str.split(",") if x.strip().isdigit()]
            if ids:
                params["item_ids"] = ids

        return params

    def _rule_build(self, units: List[ProceduralUnit]) -> List[ActionIR]:
        """Rule-based Action IR building."""
        actions = []
        for unit in units:
            if unit.unit_type != "operation":
                continue

            action_type = self._match_action_type(unit.text)
            if not action_type:
                continue

            params = self._extract_parameters(unit.text)

            # Collect preconditions/constraints from nearby condition/constraint units
            preconditions = []
            constraints = []
            for u in units:
                if u.chunk_id == unit.chunk_id or u.chunk_id == unit.parent_id:
                    if u.unit_type == "condition":
                        preconditions.append(u.text)
                    elif u.unit_type == "constraint":
                        constraints.append(u.text)

            actions.append(ActionIR(
                action_id=f"{unit.unit_id}_action",
                action_type=action_type,
                actor="agent",
                target=params.get("order_id", "") or params.get("user_id", ""),
                target_type="",  # Will be filled by grounder
                parameters=params,
                preconditions=preconditions,
                effects=[],
                constraints=constraints,
                evidence={
                    "action_type": [EvidenceSpan(text=unit.text, start=0, end=len(unit.text), chunk_id=unit.chunk_id)],
                    "parameters": [EvidenceSpan(text=unit.text, start=0, end=len(unit.text), chunk_id=unit.chunk_id)] if params else [],
                },
                confidence=0.5,
            ))

        return actions

    def _llm_build(self, units: List[ProceduralUnit]) -> List[ActionIR]:
        """LLM-based Action IR building."""
        if not self.llm:
            return self._rule_build(units)

        # Serialize units for the prompt
        units_json = json.dumps([u.to_dict() for u in units], ensure_ascii=False, indent=2)
        prompt = ACTION_IR_BUILD_PROMPT + units_json

        try:
            response = self.llm.chat_json(
                system_prompt="You are an Action IR builder. Output only valid JSON.",
                user_prompt=prompt,
                temperature=0.0,
            )
            raw_actions = response.get("actions", [])
        except Exception as e:
            print(f"LLM Action IR build failed: {e}")
            return self._rule_build(units)

        actions = []
        for i, ra in enumerate(raw_actions):
            evidence = {}
            for field, spans in ra.get("evidence", {}).items():
                evidence[field] = [EvidenceSpan(text=s, start=0, end=len(s)) for s in spans]

            actions.append(ActionIR(
                action_id=f"action_{i}",
                action_type=ra.get("action_type", ""),
                actor=ra.get("actor", "agent"),
                target=ra.get("target", ""),
                target_type=ra.get("target_type", ""),
                parameters=ra.get("parameters", {}),
                preconditions=ra.get("preconditions", []),
                effects=ra.get("effects", []),
                constraints=ra.get("constraints", []),
                evidence=evidence,
                confidence=0.8,
            ))

        return actions

    def build(self, units: List[ProceduralUnit]) -> List[ActionIR]:
        """Build Action IR records from procedural units."""
        if self.use_llm:
            return self._llm_build(units)
        return self._rule_build(units)


def main():
    import argparse
    from utils import read_jsonl, write_jsonl
    from llm_client import OpenAIClient

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="procedural_units.jsonl")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="action_ir_candidates.jsonl")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--model", default="kimi-latest")
    parser.add_argument("--base-url", default="http://localhost:9999/v1")
    args = parser.parse_args()

    llm = None
    if args.use_llm:
        llm = OpenAIClient(model=args.model, base_url=args.base_url)

    builder = ActionIRBuilder(llm=llm, use_llm=args.use_llm)
    records = read_jsonl(args.input)

    all_results = []
    for rec in records:
        units = [ProceduralUnit.from_dict(u) for u in rec["units"]]
        actions = builder.build(units)
        all_results.append({
            "doc_id": rec["doc_id"],
            "actions": [a.to_dict() for a in actions],
        })

    write_jsonl(args.output, all_results)
    total_actions = sum(len(r["actions"]) for r in all_results)
    print(f"Built {total_actions} Action IR records from {len(records)} docs → {args.output}")


if __name__ == "__main__":
    main()
