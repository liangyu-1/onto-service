"""Action schema definitions for ontology-grounded action planning."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionSchema:
    """An action schema with preconditions, effects, and constraints."""
    action_id: str
    description: str
    parameters: Dict[str, str]  # param_name -> type/description
    preconditions: List[str]  # boolean expressions as strings
    effects: List[str]  # state updates as strings
    constraints: List[str]  # policy constraints
    target_object: str = ""  # primary object type this action operates on

    def to_prompt_text(self) -> str:
        """Convert to a concise text for LLM prompting."""
        lines = [
            f"Action: {self.action_id}",
            f"  Description: {self.description}",
            f"  Target: {self.target_object}",
            f"  Parameters: {json.dumps(self.parameters, ensure_ascii=False)}",
        ]
        if self.preconditions:
            lines.append(f"  Preconditions:")
            for p in self.preconditions:
                lines.append(f"    - {p}")
        if self.effects:
            lines.append(f"  Effects:")
            for e in self.effects:
                lines.append(f"    - {e}")
        if self.constraints:
            lines.append(f"  Constraints:")
            for c in self.constraints:
                lines.append(f"    - {c}")
        return "\n".join(lines)


class ActionBank:
    """A collection of action schemas."""

    def __init__(self, schemas: List[ActionSchema]):
        self.schemas = {s.action_id: s for s in schemas}

    def get(self, action_id: str) -> Optional[ActionSchema]:
        return self.schemas.get(action_id)

    def list_actions(self) -> List[str]:
        return list(self.schemas.keys())

    def to_prompt_text(self) -> str:
        return "\n\n".join(s.to_prompt_text() for s in self.schemas.values())

    @classmethod
    def from_json(cls, path: pathlib.Path) -> "ActionBank":
        with open(path) as f:
            data = json.load(f)
        schemas = [ActionSchema(**s) for s in data.get("actions", [])]
        return cls(schemas)

    def save(self, path: pathlib.Path) -> None:
        data = {
            "actions": [
                {
                    "action_id": s.action_id,
                    "description": s.description,
                    "parameters": s.parameters,
                    "preconditions": s.preconditions,
                    "effects": s.effects,
                    "constraints": s.constraints,
                    "target_object": s.target_object,
                }
                for s in self.schemas.values()
            ]
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
