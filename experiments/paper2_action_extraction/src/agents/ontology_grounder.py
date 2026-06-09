"""Agent 5: OntologyGrounder — grounds Action IR fields to ontology candidates."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan


class OntologyGrounder:
    """Grounds extracted Action IR fields to an ontology ActionBank.

    Uses lexical matching, dense retrieval (placeholder), and graph
    neighborhood expansion (placeholder) to map:
    - action_type → ontology action type
    - target → ontology object type
    - parameters → ontology parameter schema
    - preconditions/effects/constraints → ontology constraint definitions
    """

    def __init__(self, action_bank_path: pathlib.Path):
        with open(action_bank_path) as f:
            data = json.load(f)
        self.action_bank = {a["action_id"]: a for a in data.get("actions", [])}
        # Build keyword index for fuzzy matching
        self.keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, List[str]]:
        """Build a keyword → action_id index."""
        index: Dict[str, List[str]] = {}
        for action_id, schema in self.action_bank.items():
            # Index action name
            for token in action_id.replace("_", " ").split():
                token = token.lower()
                index.setdefault(token, []).append(action_id)
            # Index description words
            desc = schema.get("description", "").lower()
            for token in desc.split():
                token = re.sub(r"[^a-z0-9]", "", token)
                if len(token) > 2:
                    index.setdefault(token, []).append(action_id)
            # Index target object
            target = schema.get("target_object", "").lower()
            if target:
                index.setdefault(target, []).append(action_id)
        return index

    def _lexical_match(self, text: str) -> Optional[str]:
        """Find the best matching action type by lexical overlap."""
        text_lower = text.lower()
        tokens = [re.sub(r"[^a-z0-9]", "", t) for t in text_lower.split() if len(t) > 2]

        scores: Dict[str, int] = {}
        for token in tokens:
            for action_id in self.keyword_index.get(token, []):
                scores[action_id] = scores.get(action_id, 0) + 1

        if not scores:
            return None

        best_action = max(scores, key=lambda k: scores[k])
        best_score = scores[best_action]
        # Require at least one keyword match
        if best_score < 1:
            return None
        return best_action

    def _ground_action_type(self, action: ActionIR) -> Tuple[str, float]:
        """Ground action_type to ontology action type."""
        # Exact match first
        if action.action_type in self.action_bank:
            return action.action_type, 1.0

        # Lexical match
        matched = self._lexical_match(action.action_type)
        if matched:
            return matched, 0.7

        # Try matching against evidence text
        for field, spans in action.evidence.items():
            for span in spans:
                matched = self._lexical_match(span.text)
                if matched:
                    return matched, 0.5

        return action.action_type, 0.0

    def _ground_target_type(self, action: ActionIR, schema: Dict[str, Any]) -> Tuple[str, float]:
        """Ground target to ontology object type."""
        schema_target = schema.get("target_object", "")
        if not schema_target:
            return "", 0.0

        # If extracted target_type matches schema, high confidence
        if action.target_type == schema_target:
            return schema_target, 1.0

        # If target_type is empty but schema has one, suggest it
        if not action.target_type and schema_target:
            return schema_target, 0.6

        # Lexical match on target_type
        if action.target_type.lower() == schema_target.lower():
            return schema_target, 0.8

        return action.target_type, 0.0

    def _ground_parameters(self, action: ActionIR, schema: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Ground parameters to ontology parameter schema."""
        schema_params = schema.get("parameters", {})
        if not schema_params:
            return action.parameters, 1.0

        grounded = {}
        matched = 0
        for param_name in schema_params:
            if param_name in action.parameters:
                grounded[param_name] = action.parameters[param_name]
                matched += 1
            else:
                grounded[param_name] = None  # Mark as missing

        # Coverage score
        coverage = matched / len(schema_params) if schema_params else 1.0
        return grounded, coverage

    def _ground_preconditions(self, action: ActionIR, schema: Dict[str, Any]) -> Tuple[List[str], float]:
        """Ground preconditions to ontology precondition definitions."""
        schema_pre = schema.get("preconditions", [])
        if not schema_pre:
            return action.preconditions, 1.0

        # Simple overlap: if any extracted precondition contains schema precondition text
        matched = []
        for sp in schema_pre:
            found = False
            for ep in action.preconditions:
                if sp.lower() in ep.lower() or ep.lower() in sp.lower():
                    found = True
                    break
            if found:
                matched.append(sp)

        coverage = len(matched) / len(schema_pre) if schema_pre else 1.0
        return matched, coverage

    def _ground_constraints(self, action: ActionIR, schema: Dict[str, Any]) -> Tuple[List[str], float]:
        """Ground constraints to ontology constraint definitions."""
        schema_con = schema.get("constraints", [])
        if not schema_con:
            return action.constraints, 1.0

        matched = []
        for sc in schema_con:
            found = False
            for ec in action.constraints:
                if sc.lower() in ec.lower() or ec.lower() in sc.lower():
                    found = True
                    break
            if found:
                matched.append(sc)

        coverage = len(matched) / len(schema_con) if schema_con else 1.0
        return matched, coverage

    def ground(self, action: ActionIR) -> ActionIR:
        """Ground all fields of an Action IR to the ontology."""
        # Ground action type
        grounded_type, type_score = self._ground_action_type(action)
        schema = self.action_bank.get(grounded_type, {})

        # Ground target type
        grounded_target, target_score = self._ground_target_type(action, schema)

        # Ground parameters
        grounded_params, param_score = self._ground_parameters(action, schema)

        # Ground preconditions
        grounded_pre, pre_score = self._ground_preconditions(action, schema)

        # Ground constraints
        grounded_con, con_score = self._ground_constraints(action, schema)

        # Ground effects (copy from schema if missing)
        grounded_eff = action.effects if action.effects else schema.get("effects", [])
        eff_score = 1.0 if action.effects else (0.5 if schema.get("effects") else 1.0)

        # Compute overall confidence
        scores = [type_score, target_score, param_score, pre_score, con_score, eff_score]
        overall_confidence = sum(scores) / len(scores)

        # Mark unresolved if any critical field failed
        resolved = type_score > 0 and target_score >= 0

        # Build evidence for grounding
        grounding_evidence = {
            "action_type": f"Matched to ontology action '{grounded_type}' (score={type_score:.2f})",
            "target_type": f"Matched to ontology type '{grounded_target}' (score={target_score:.2f})",
            "parameters": f"Coverage={param_score:.2f}",
        }

        return ActionIR(
            action_id=action.action_id,
            action_type=grounded_type,
            actor=action.actor,
            target=action.target,
            target_type=grounded_target,
            parameters=grounded_params,
            preconditions=grounded_pre,
            effects=grounded_eff,
            constraints=grounded_con,
            evidence=action.evidence,
            grounding=grounding_evidence,
            control_flow=action.control_flow,
            confidence=overall_confidence,
            resolved=resolved,
        )

    def ground_all(self, actions: List[ActionIR]) -> List[ActionIR]:
        """Ground all actions in a list."""
        return [self.ground(a) for a in actions]


# Need re import for _build_keyword_index
import re


def main():
    import argparse
    from utils import read_jsonl, write_jsonl

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="action_ir_candidates.jsonl")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="grounded_actions.jsonl")
    parser.add_argument("--action-bank", type=pathlib.Path, required=True)
    args = parser.parse_args()

    grounder = OntologyGrounder(action_bank_path=args.action_bank)
    records = read_jsonl(args.input)

    all_results = []
    for rec in records:
        actions = [ActionIR.from_dict(a) for a in rec["actions"]]
        grounded = grounder.ground_all(actions)
        all_results.append({
            "doc_id": rec["doc_id"],
            "actions": [a.to_dict() for a in grounded],
        })

    write_jsonl(args.output, all_results)
    total = sum(len(r["actions"]) for r in all_results)
    resolved = sum(1 for r in all_results for a in r["actions"] if a.get("resolved"))
    print(f"Grounded {total} actions ({resolved} resolved) → {args.output}")


if __name__ == "__main__":
    main()
