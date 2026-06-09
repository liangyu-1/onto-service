"""Action Intermediate Representation (Action IR) dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceSpan:
    """A span of text in the source document that supports an extracted field."""
    text: str
    start: int  # character offset
    end: int    # character offset
    chunk_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSpan":
        return cls(**data)


@dataclass
class ActionIR:
    """Intermediate representation of an extracted action.

    Fields correspond to the paper's Action IR definition:
    ⟨id, type, actor, target, params, pre, eff, constraints, evidence, grounding⟩
    """
    action_id: str
    action_type: str
    actor: str = ""
    target: str = ""
    target_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    evidence: Dict[str, List[EvidenceSpan]] = field(default_factory=dict)
    grounding: Dict[str, Any] = field(default_factory=dict)
    control_flow: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    resolved: bool = True  # False if any field could not be grounded

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Convert nested EvidenceSpan objects
        d["evidence"] = {
            k: [e.to_dict() for e in v] for k, v in self.evidence.items()
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionIR":
        evidence = {}
        for k, spans in data.get("evidence", {}).items():
            evidence[k] = [EvidenceSpan.from_dict(s) for s in spans]
        return cls(
            action_id=data.get("action_id", ""),
            action_type=data.get("action_type", ""),
            actor=data.get("actor", ""),
            target=data.get("target", ""),
            target_type=data.get("target_type", ""),
            parameters=data.get("parameters", {}),
            preconditions=data.get("preconditions", []),
            effects=data.get("effects", []),
            constraints=data.get("constraints", []),
            evidence=evidence,
            grounding=data.get("grounding", {}),
            control_flow=data.get("control_flow", {}),
            confidence=data.get("confidence", 1.0),
            resolved=data.get("resolved", True),
        )


@dataclass
class ProcedureGraph:
    """Graph of actions with control-flow edges."""
    nodes: List[ActionIR] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": self.edges,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcedureGraph":
        return cls(
            nodes=[ActionIR.from_dict(n) for n in data.get("nodes", [])],
            edges=data.get("edges", []),
        )


@dataclass
class ProceduralUnit:
    """A procedural unit extracted from a document chunk."""
    unit_id: str
    unit_type: str  # operation, condition, constraint, exception, equipment, quality
    text: str
    chunk_id: Optional[str] = None
    parent_id: Optional[str] = None
    step_number: Optional[str] = None
    section_path: List[str] = field(default_factory=list)
    evidence: List[EvidenceSpan] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["evidence"] = [e.to_dict() for e in self.evidence]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProceduralUnit":
        evidence = [EvidenceSpan.from_dict(e) for e in data.get("evidence", [])]
        return cls(
            unit_id=data.get("unit_id", ""),
            unit_type=data.get("unit_type", ""),
            text=data.get("text", ""),
            chunk_id=data.get("chunk_id"),
            parent_id=data.get("parent_id"),
            step_number=data.get("step_number"),
            section_path=data.get("section_path", []),
            evidence=evidence,
        )


@dataclass
class ParsedChunk:
    """A structured chunk from document parsing."""
    chunk_id: str
    chunk_type: str  # heading, numbered_step, paragraph, table, warning, figure, appendix
    text: str
    section_path: List[str] = field(default_factory=list)
    step_number: Optional[str] = None
    table_context: Optional[Dict[str, Any]] = None
    evidence_offset: Optional[tuple] = None  # (start, end) in original doc

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParsedChunk":
        return cls(
            chunk_id=data.get("chunk_id", ""),
            chunk_type=data.get("chunk_type", ""),
            text=data.get("text", ""),
            section_path=data.get("section_path", []),
            step_number=data.get("step_number"),
            table_context=data.get("table_context"),
            evidence_offset=tuple(data["evidence_offset"]) if data.get("evidence_offset") else None,
        )


@dataclass
class SyntheticDocument:
    """A synthetic procedural document with ground-truth annotations."""
    doc_id: str
    title: str
    domain: str
    text: str
    source_tasks: List[str] = field(default_factory=list)
    ground_truth_actions: List[ActionIR] = field(default_factory=list)
    ground_truth_graph: Optional[ProcedureGraph] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "domain": self.domain,
            "text": self.text,
            "source_tasks": self.source_tasks,
            "ground_truth_actions": [a.to_dict() for a in self.ground_truth_actions],
            "ground_truth_graph": self.ground_truth_graph.to_dict() if self.ground_truth_graph else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyntheticDocument":
        gt_actions = [ActionIR.from_dict(a) for a in data.get("ground_truth_actions", [])]
        gt_graph = ProcedureGraph.from_dict(data["ground_truth_graph"]) if data.get("ground_truth_graph") else None
        return cls(
            doc_id=data.get("doc_id", ""),
            title=data.get("title", ""),
            domain=data.get("domain", ""),
            text=data.get("text", ""),
            source_tasks=data.get("source_tasks", []),
            ground_truth_actions=gt_actions,
            ground_truth_graph=gt_graph,
        )
