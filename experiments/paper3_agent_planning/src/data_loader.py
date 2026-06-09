"""Load and parse tau-bench data files."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetailDB:
    users: Dict[str, Any]
    products: Dict[str, Any]
    orders: Dict[str, Any]

    @classmethod
    def load(cls, path: pathlib.Path) -> "RetailDB":
        with open(path) as f:
            data = json.load(f)
        return cls(
            users=data["users"],
            products=data["products"],
            orders=data["orders"],
        )


@dataclass
class AirlineDB:
    users: Dict[str, Any]
    flights: Dict[str, Any]
    reservations: Dict[str, Any]

    @classmethod
    def load(cls, path: pathlib.Path) -> "AirlineDB":
        with open(path) as f:
            data = json.load(f)
        return cls(
            users=data["users"],
            flights=data["flights"],
            reservations=data["reservations"],
        )


@dataclass
class Task:
    task_id: str
    user_scenario: Dict[str, Any]
    evaluation_criteria: Dict[str, Any]
    gold_actions: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Task":
        ec = data.get("evaluation_criteria", {})
        return cls(
            task_id=str(data.get("id", "")),
            user_scenario=data.get("user_scenario", {}),
            evaluation_criteria=ec,
            gold_actions=ec.get("actions", []),
        )


def load_tasks(path: pathlib.Path) -> List[Task]:
    with open(path) as f:
        raw = json.load(f)
    return [Task.from_json(t) for t in raw]


def load_split(path: pathlib.Path) -> Dict[str, List[str]]:
    with open(path) as f:
        return json.load(f)


def get_task_by_id(tasks: List[Task], task_id: str) -> Optional[Task]:
    for t in tasks:
        if t.task_id == task_id:
            return t
    return None
