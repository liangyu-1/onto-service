"""Data structures for ontology Workflow Skill induction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentRecord:
    dataset: str
    source_id: str
    domain: str
    text: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FunctionSpec:
    function_id: str
    description: str = ""
    bound_object_types: tuple[str, ...] = ()
    inputs: tuple[dict[str, Any], ...] = ()
    outputs: tuple[dict[str, Any], ...] = ()
    preconditions: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()


@dataclass
class WorkflowNode:
    node_id: str
    node_type: str
    text: str
    function_id: str | None = None
    object_variables: list[str] = field(default_factory=list)
    state_predicates: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEdge:
    source: str
    target: str
    edge_type: str = "sequence"
    condition: str | None = None


@dataclass
class OntologyWorkflowSkill:
    skill_id: str
    source_id: str
    goal_predicate: str | None = None
    typed_inputs: list[dict[str, Any]] = field(default_factory=list)
    typed_outputs: list[dict[str, Any]] = field(default_factory=list)
    object_variables: list[dict[str, Any]] = field(default_factory=list)
    nodes: list[WorkflowNode] = field(default_factory=list)
    control_edges: list[WorkflowEdge] = field(default_factory=list)
    dataflow_edges: list[WorkflowEdge] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    exception_paths: list[WorkflowEdge] = field(default_factory=list)
    unresolved_regions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
