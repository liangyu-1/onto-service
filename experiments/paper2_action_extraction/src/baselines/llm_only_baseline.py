"""LLM-only baseline: direct extraction without ontology context."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan
from llm_client import LLMClient


LLM_ONLY_PROMPT = """Extract all actions from the following procedural document.

For each action, output:
- action_type: the action name
- actor: who performs it
- target: the object it operates on
- target_type: the type of object (e.g., User, Order, Product)
- parameters: a dict of parameter names to values
- preconditions: list of prerequisites
- effects: list of outcomes
- constraints: list of policy constraints
- evidence: the text span that supports this action

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
      "evidence": ["..."]
    }
  ]
}

Document:
"""


class LLMOnlyBaseline:
    """Direct LLM extraction without ontology context or structured validation."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, doc_text: str, doc_id: str = "") -> Dict[str, Any]:
        prompt = LLM_ONLY_PROMPT + doc_text

        try:
            response = self.llm.chat_json(
                system_prompt="You are an action extraction assistant. Output only valid JSON.",
                user_prompt=prompt,
                temperature=0.0,
            )
            raw_actions = response.get("actions", [])
        except Exception as e:
            print(f"LLM extraction failed for {doc_id}: {e}")
            raw_actions = []

        actions = []
        for i, ra in enumerate(raw_actions):
            evidence = {}
            for j, ev_text in enumerate(ra.get("evidence", [])):
                evidence.setdefault("action_type", []).append(
                    EvidenceSpan(text=ev_text, start=0, end=len(ev_text))
                )

            actions.append(ActionIR(
                action_id=f"{doc_id}_action_{i}",
                action_type=ra.get("action_type", ""),
                actor=ra.get("actor", "agent"),
                target=ra.get("target", ""),
                target_type=ra.get("target_type", ""),
                parameters=ra.get("parameters", {}),
                preconditions=ra.get("preconditions", []),
                effects=ra.get("effects", []),
                constraints=ra.get("constraints", []),
                evidence=evidence,
                confidence=0.7,
            ))

        # Build simple sequential graph
        edges = []
        for i in range(len(actions) - 1):
            edges.append({
                "source": actions[i].action_id,
                "target": actions[i + 1].action_id,
                "relation": "sequential",
            })

        from action_ir import ProcedureGraph
        graph = ProcedureGraph(nodes=actions, edges=edges)

        return {
            "doc_id": doc_id,
            "actions": [a.to_dict() for a in actions],
            "graph": graph.to_dict(),
            "doc_text": doc_text,
        }
