"""LLM + Ontology Prompt baseline: LLM extraction with ActionBank in prompt."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan, ProcedureGraph
from llm_client import LLMClient


LLM_ONTOLOGY_PROMPT_TEMPLATE = """You are an ontology-grounded action extractor.

The ontology defines the following action types:
{action_bank_text}

Extract all actions from the following procedural document. For each action:
1. Map it to one of the ontology action types above
2. Identify the actor, target, and target_type
3. Extract parameters matching the ontology schema
4. Identify preconditions, effects, and constraints
5. Cite the evidence text span

Output as JSON:
{{
  "actions": [
    {{
      "action_type": "<must be one of the ontology action types>",
      "actor": "...",
      "target": "...",
      "target_type": "...",
      "parameters": {{...}},
      "preconditions": [...],
      "effects": [...],
      "constraints": [...],
      "evidence": ["..."]
    }}
  ]
}}

Document:
"""


class LLMOntologyPromptBaseline:
    """LLM extraction with ontology ActionBank provided in the prompt.

    This is the strongest baseline: the LLM knows the ontology schema
    but does not perform structured validation or grounding.
    """

    def __init__(self, llm: LLMClient, action_bank_path: pathlib.Path):
        self.llm = llm
        with open(action_bank_path) as f:
            data = json.load(f)
        # Format action bank as text for the prompt
        lines = []
        for a in data.get("actions", []):
            lines.append(f"- {a['action_id']}: {a['description']}")
            lines.append(f"  Target: {a.get('target_object', 'N/A')}")
            lines.append(f"  Parameters: {json.dumps(a.get('parameters', {}))}")
            if a.get("preconditions"):
                lines.append(f"  Preconditions: {a['preconditions']}")
            if a.get("effects"):
                lines.append(f"  Effects: {a['effects']}")
            if a.get("constraints"):
                lines.append(f"  Constraints: {a['constraints']}")
        self.action_bank_text = "\n".join(lines)

    def extract(self, doc_text: str, doc_id: str = "") -> Dict[str, Any]:
        prompt = LLM_ONTOLOGY_PROMPT_TEMPLATE.format(
            action_bank_text=self.action_bank_text,
        ) + doc_text

        try:
            response = self.llm.chat_json(
                system_prompt="You are an ontology-grounded action extractor. Output only valid JSON.",
                user_prompt=prompt,
                temperature=0.0,
            )
            raw_actions = response.get("actions", [])
        except Exception as e:
            print(f"LLM+Ontology extraction failed for {doc_id}: {e}")
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
                confidence=0.8,
            ))

        # Build simple sequential graph
        edges = []
        for i in range(len(actions) - 1):
            edges.append({
                "source": actions[i].action_id,
                "target": actions[i + 1].action_id,
                "relation": "sequential",
            })

        graph = ProcedureGraph(nodes=actions, edges=edges)

        return {
            "doc_id": doc_id,
            "actions": [a.to_dict() for a in actions],
            "graph": graph.to_dict(),
            "doc_text": doc_text,
        }
