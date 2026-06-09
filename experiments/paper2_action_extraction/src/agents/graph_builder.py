"""Agent 6: GraphBuilder — builds procedure graph with control-flow edges."""
from __future__ import annotations

import pathlib
import re
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan, ProcedureGraph


class GraphBuilder:
    """Builds a procedure graph from a sequence of Action IR records.

    Uses document order, numbering, headings, conditional markers,
    exception phrases, and table context to create edges:
    - sequential: default step-by-step flow
    - conditional: if/when branches
    - exception: error handling paths
    - loop: repeated steps
    - parallel: independent concurrent steps
    """

    def __init__(self):
        self.conditional_markers = re.compile(
            r"\b(if|when|once|provided that|given that|in case)\b",
            re.IGNORECASE,
        )
        self.exception_markers = re.compile(
            r"\b(if not|otherwise|else|in case of|when .* fails|error|exception|unable to|if .* unavailable)\b",
            re.IGNORECASE,
        )
        self.loop_markers = re.compile(
            r"\b(repeat|loop|while|until|for each|iteratively)\b",
            re.IGNORECASE,
        )
        self.parallel_markers = re.compile(
            r"\b(simultaneously|in parallel|concurrently|at the same time|while also)\b",
            re.IGNORECASE,
        )

    def _detect_relation(self, source: ActionIR, target: ActionIR) -> str:
        """Detect the control-flow relation between two consecutive actions."""
        # Check evidence text for markers
        texts = []
        for spans in target.evidence.values():
            for span in spans:
                texts.append(span.text)
        combined = " ".join(texts).lower()

        if self.loop_markers.search(combined):
            return "loop"
        if self.parallel_markers.search(combined):
            return "parallel"
        if self.exception_markers.search(combined):
            return "exception"
        if self.conditional_markers.search(combined):
            return "conditional"

        return "sequential"

    def build(self, actions: List[ActionIR], doc_text: str = "") -> ProcedureGraph:
        """Build a procedure graph from a list of Action IR records."""
        nodes = list(actions)
        edges = []

        for i in range(len(nodes) - 1):
            relation = self._detect_relation(nodes[i], nodes[i + 1])
            edges.append({
                "source": nodes[i].action_id,
                "target": nodes[i + 1].action_id,
                "relation": relation,
                "evidence": f"Step {i+1} → Step {i+2}",
            })

        # Detect parallel groups: actions with same section path and no dependencies
        # (simplified: if two actions have the same parent chunk and are not sequential)
        # For now, we keep the simple sequential model with conditional/exception overlays

        return ProcedureGraph(nodes=nodes, edges=edges)

    def build_all(self, actions_per_doc: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build graphs for multiple documents."""
        results = []
        for rec in actions_per_doc:
            actions = [ActionIR.from_dict(a) for a in rec["actions"]]
            graph = self.build(actions, doc_text=rec.get("doc_text", ""))
            results.append({
                "doc_id": rec["doc_id"],
                "graph": graph.to_dict(),
            })
        return results


def main():
    import argparse
    from utils import read_jsonl, write_jsonl

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="grounded_actions.jsonl")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="procedure_graphs.jsonl")
    args = parser.parse_args()

    builder = GraphBuilder()
    records = read_jsonl(args.input)

    results = builder.build_all(records)
    write_jsonl(args.output, results)

    total_edges = sum(len(r["graph"]["edges"]) for r in results)
    print(f"Built {len(results)} graphs with {total_edges} edges → {args.output}")


if __name__ == "__main__":
    main()
