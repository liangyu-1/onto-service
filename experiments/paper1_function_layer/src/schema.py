"""Data structures for Paper 1 function-layer experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    source_type: str
    source_id: str
    claim: str
    confidence: float = 1.0


@dataclass(frozen=True)
class OntologyProperty:
    id: str
    type: str = "string"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObjectType:
    id: str
    aliases: tuple[str, ...] = ()
    properties: tuple[OntologyProperty, ...] = ()
    states: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObjectLayer:
    object_types: tuple[ObjectType, ...]

    def property_index(self) -> dict[str, tuple[str, OntologyProperty]]:
        index: dict[str, tuple[str, OntologyProperty]] = {}
        for obj in self.object_types:
            for prop in obj.properties:
                index[f"{obj.id}.{prop.id}"] = (obj.id, prop)
        return index


@dataclass
class FunctionField:
    name: str
    type: str = "string"
    semantic_role: str = "value"
    ontology_property: str | None = None
    required: bool = False


@dataclass
class EndpointBinding:
    method: str
    path: str
    operation_id: str | None = None


@dataclass
class FunctionCandidate:
    function_id: str
    endpoint_binding: EndpointBinding
    operation_kind: str
    description: str = ""
    bound_object_types: list[str] = field(default_factory=list)
    inputs: list[FunctionField] = field(default_factory=list)
    outputs: list[FunctionField] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    error_contract: list[str] = field(default_factory=list)
    evidence_set: list[Evidence] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "candidate"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
