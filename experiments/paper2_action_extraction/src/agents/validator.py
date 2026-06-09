"""Agent 7: Validator — validates extracted actions against ontology schema and evidence."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, ProcedureGraph


class ValidationReport:
    """Report from validation of a single document."""

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.action_reports: List[Dict[str, Any]] = []
        self.graph_report: Dict[str, Any] = {}
        self.overall_passed = True

    def add_action_report(self, action_id: str, passed: bool, checks: Dict[str, Any]) -> None:
        self.action_reports.append({
            "action_id": action_id,
            "passed": passed,
            "checks": checks,
        })
        if not passed:
            self.overall_passed = False

    def add_graph_report(self, passed: bool, checks: Dict[str, Any]) -> None:
        self.graph_report = {
            "passed": passed,
            "checks": checks,
        }
        if not passed:
            self.overall_passed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "overall_passed": self.overall_passed,
            "action_reports": self.action_reports,
            "graph_report": self.graph_report,
        }


class Validator:
    """Validates extracted Action IR and procedure graph.

    Checks:
    1. Action type exists in ontology
    2. Target type satisfies action constraints
    3. Parameters are compatible with target objects
    4. Control-flow edges reference valid actions
    5. Evidence text is traceable to source document
    """

    def __init__(self, action_bank_path: pathlib.Path):
        with open(action_bank_path) as f:
            data = json.load(f)
        self.action_bank = {a["action_id"]: a for a in data.get("actions", [])}
        # Build target type → allowed actions mapping
        self.target_actions: Dict[str, List[str]] = {}
        for action_id, schema in self.action_bank.items():
            target = schema.get("target_object", "")
            if target:
                self.target_actions.setdefault(target, []).append(action_id)

    def _validate_action_type(self, action: ActionIR) -> Tuple[bool, str]:
        """Check if action type exists in ontology."""
        if action.action_type in self.action_bank:
            return True, f"Action type '{action.action_type}' found in ontology"
        return False, f"Action type '{action.action_type}' NOT found in ontology"

    def _validate_target_type(self, action: ActionIR) -> Tuple[bool, str]:
        """Check if target type satisfies action constraints."""
        schema = self.action_bank.get(action.action_type, {})
        expected_target = schema.get("target_object", "")

        if not expected_target:
            # Action has no target requirement
            return True, "No target type required"

        if not action.target_type:
            return False, f"Target type missing; expected '{expected_target}'"

        if action.target_type == expected_target:
            return True, f"Target type '{action.target_type}' matches ontology"

        return False, f"Target type '{action.target_type}' != expected '{expected_target}'"

    def _validate_parameters(self, action: ActionIR) -> Tuple[bool, str]:
        """Check if parameters are compatible with action schema."""
        schema = self.action_bank.get(action.action_type, {})
        schema_params = schema.get("parameters", {})

        if not schema_params:
            return True, "No parameters required"

        missing = []
        for param_name in schema_params:
            if param_name not in action.parameters or action.parameters[param_name] is None:
                missing.append(param_name)

        if missing:
            return False, f"Missing required parameters: {missing}"

        return True, f"All required parameters present ({len(schema_params)} params)"

    def _validate_evidence(self, action: ActionIR, doc_text: str = "") -> Tuple[bool, str]:
        """Check if evidence text is traceable to source document."""
        if not action.evidence:
            return True, "No evidence required (rule-based extraction)"

        untraceable = []
        for field, spans in action.evidence.items():
            for span in spans:
                if doc_text and span.text not in doc_text:
                    untraceable.append(f"{field}: '{span.text[:50]}...'")

        if untraceable:
            return False, f"Untraceable evidence spans: {untraceable[:3]}"

        return True, "All evidence spans traceable"

    def _validate_graph(self, graph: ProcedureGraph) -> Tuple[bool, str]:
        """Check if control-flow edges reference valid actions."""
        action_ids = {n.action_id for n in graph.nodes}
        invalid_edges = []

        for edge in graph.edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src not in action_ids:
                invalid_edges.append(f"Invalid source: {src}")
            if tgt not in action_ids:
                invalid_edges.append(f"Invalid target: {tgt}")

        if invalid_edges:
            return False, f"Invalid edges: {invalid_edges[:3]}"

        return True, f"All {len(graph.edges)} edges reference valid actions"

    def validate(
        self,
        actions: List[ActionIR],
        graph: Optional[ProcedureGraph],
        doc_text: str = "",
    ) -> ValidationReport:
        """Validate a full extraction result for one document."""
        report = ValidationReport(doc_id="")

        for action in actions:
            checks = {}
            passed = True

            ok, msg = self._validate_action_type(action)
            checks["action_type"] = {"passed": ok, "message": msg}
            passed = passed and ok

            ok, msg = self._validate_target_type(action)
            checks["target_type"] = {"passed": ok, "message": msg}
            passed = passed and ok

            ok, msg = self._validate_parameters(action)
            checks["parameters"] = {"passed": ok, "message": msg}
            passed = passed and ok

            ok, msg = self._validate_evidence(action, doc_text)
            checks["evidence"] = {"passed": ok, "message": msg}
            passed = passed and ok

            report.add_action_report(action.action_id, passed, checks)

        if graph:
            ok, msg = self._validate_graph(graph)
            report.add_graph_report(ok, {"graph_validity": {"passed": ok, "message": msg}})

        return report

    def validate_all(
        self,
        docs: List[Dict[str, Any]],
    ) -> List[ValidationReport]:
        """Validate extraction results for multiple documents."""
        reports = []
        for doc in docs:
            # Support both flat format (actions + graph keys) and graph-only format
            actions = [ActionIR.from_dict(a) for a in doc.get("actions", [])]
            if not actions and doc.get("graph"):
                actions = [ActionIR.from_dict(n) for n in doc["graph"].get("nodes", [])]
            graph = ProcedureGraph.from_dict(doc["graph"]) if doc.get("graph") else None
            doc_text = doc.get("doc_text", "")
            report = self.validate(actions, graph, doc_text)
            report.doc_id = doc.get("doc_id", "")
            reports.append(report)
        return reports


def main():
    import argparse
    from utils import read_jsonl, write_json

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="procedure_graphs.jsonl or grounded_actions.jsonl")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="validation_report.json")
    parser.add_argument("--action-bank", type=pathlib.Path, required=True)
    parser.add_argument("--docs", type=pathlib.Path, help="synthetic_docs.jsonl for evidence traceability")
    args = parser.parse_args()

    validator = Validator(action_bank_path=args.action_bank)
    records = read_jsonl(args.input)

    # Load doc texts if provided
    doc_texts = {}
    if args.docs:
        doc_records = read_jsonl(args.docs)
        doc_texts = {d["doc_id"]: d["text"] for d in doc_records}

    reports = []
    for rec in records:
        actions = [ActionIR.from_dict(a) for a in rec.get("actions", [])]
        if not actions and rec.get("graph"):
            actions = [ActionIR.from_dict(n) for n in rec["graph"].get("nodes", [])]
        graph = ProcedureGraph.from_dict(rec["graph"]) if rec.get("graph") else None
        doc_text = doc_texts.get(rec["doc_id"], "")
        report = validator.validate(actions, graph, doc_text)
        report.doc_id = rec["doc_id"]
        reports.append(report.to_dict())

    summary = {
        "total_docs": len(reports),
        "passed_docs": sum(1 for r in reports if r["overall_passed"]),
        "passed_actions": sum(
            1 for r in reports for a in r["action_reports"] if a["passed"]
        ),
        "total_actions": sum(len(r["action_reports"]) for r in reports),
        "reports": reports,
    }

    write_json(args.output, summary)
    print(f"Validated {summary['total_docs']} docs, {summary['total_actions']} actions, "
          f"{summary['passed_actions']} passed → {args.output}")


if __name__ == "__main__":
    main()
