"""Evaluation metrics for ontology-grounded action extraction."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from action_ir import ActionIR, EvidenceSpan, ProcedureGraph


def _normalize(text: str) -> str:
    return text.lower().strip().replace("_", " ")


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


class ExtractionMetrics:
    """Computes all paper metrics for a single document extraction."""

    def __init__(self, ground_truth: List[ActionIR], predicted: List[ActionIR]):
        self.gt = ground_truth
        self.pred = predicted

    # ------------------------------------------------------------------
    # Action Mention F1
    # ------------------------------------------------------------------
    def action_mention_f1(self) -> Tuple[float, float, float]:
        """F1 for action mention detection (action_type match)."""
        gt_types = {a.action_type for a in self.gt}
        pred_types = {a.action_type for a in self.pred}

        tp = len(gt_types & pred_types)
        fp = len(pred_types - gt_types)
        fn = len(gt_types - pred_types)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return precision, recall, _f1(precision, recall)

    # ------------------------------------------------------------------
    # Action-Type Accuracy
    # ------------------------------------------------------------------
    def action_type_accuracy(self) -> float:
        """Accuracy of action type mapping (per-action, not set-based)."""
        if not self.gt or not self.pred:
            return 0.0

        # Match predicted to ground truth by action_type
        gt_by_type = {a.action_type: a for a in self.gt}
        correct = 0
        total = 0

        for p in self.pred:
            total += 1
            if p.action_type in gt_by_type:
                correct += 1

        return correct / total if total > 0 else 0.0

    # ------------------------------------------------------------------
    # Target Grounding Accuracy
    # ------------------------------------------------------------------
    def target_grounding_accuracy(self) -> float:
        """Accuracy of target object type grounding."""
        if not self.gt or not self.pred:
            return 0.0

        gt_by_type = {a.action_type: a for a in self.gt}
        correct = 0
        total = 0

        for p in self.pred:
            if p.action_type not in gt_by_type:
                continue
            total += 1
            gt_action = gt_by_type[p.action_type]
            if p.target_type == gt_action.target_type:
                correct += 1

        return correct / total if total > 0 else 0.0

    # ------------------------------------------------------------------
    # Parameter Grounding F1
    # ------------------------------------------------------------------
    def parameter_grounding_f1(self) -> Tuple[float, float, float]:
        """F1 for parameter recovery (key match, not value match)."""
        gt_by_type = {a.action_type: a for a in self.gt}
        tp, fp, fn = 0, 0, 0

        for p in self.pred:
            gt_action = gt_by_type.get(p.action_type)
            if not gt_action:
                continue

            gt_params = set(gt_action.parameters.keys())
            pred_params = set(p.parameters.keys())

            tp += len(gt_params & pred_params)
            fp += len(pred_params - gt_params)
            fn += len(gt_params - pred_params)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return precision, recall, _f1(precision, recall)

    # ------------------------------------------------------------------
    # Evidence-Span F1
    # ------------------------------------------------------------------
    def evidence_span_f1(self) -> Tuple[float, float, float]:
        """F1 for evidence span traceability.

        Simplified: count documents with any evidence vs none.
        A more sophisticated version would do span overlap.
        """
        gt_with_evidence = sum(1 for a in self.gt if a.evidence)
        pred_with_evidence = sum(1 for a in self.pred if a.evidence)

        # For per-action evidence, check if predicted action has evidence
        gt_by_type = {a.action_type: a for a in self.gt}
        tp, fp, fn = 0, 0, 0

        for p in self.pred:
            gt_action = gt_by_type.get(p.action_type)
            if not gt_action:
                continue

            gt_has = bool(gt_action.evidence)
            pred_has = bool(p.evidence)

            if gt_has and pred_has:
                tp += 1
            elif not gt_has and pred_has:
                fp += 1
            elif gt_has and not pred_has:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return precision, recall, _f1(precision, recall)

    # ------------------------------------------------------------------
    # Control-Flow Edge F1
    # ------------------------------------------------------------------
    def control_flow_edge_f1(
        self, gt_graph: Optional[ProcedureGraph], pred_graph: Optional[ProcedureGraph]
    ) -> Tuple[float, float, float]:
        """F1 for control-flow edge correctness."""
        if not gt_graph or not pred_graph:
            return 0.0, 0.0, 0.0

        gt_edges = set()
        for e in gt_graph.edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            rel = e.get("relation", "")
            gt_edges.add((src, tgt, rel))

        pred_edges = set()
        for e in pred_graph.edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            rel = e.get("relation", "")
            pred_edges.add((src, tgt, rel))

        tp = len(gt_edges & pred_edges)
        fp = len(pred_edges - gt_edges)
        fn = len(gt_edges - pred_edges)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return precision, recall, _f1(precision, recall)

    # ------------------------------------------------------------------
    # Validation Pass Rate
    # ------------------------------------------------------------------
    def validation_pass_rate(self, validation_reports: List[Dict[str, Any]]) -> float:
        """Percentage of actions passing validation."""
        total = 0
        passed = 0
        for report in validation_reports:
            for ar in report.get("action_reports", []):
                total += 1
                if ar.get("passed"):
                    passed += 1
        return passed / total if total > 0 else 0.0

    # ------------------------------------------------------------------
    # Full summary
    # ------------------------------------------------------------------
    def compute_all(
        self,
        gt_graph: Optional[ProcedureGraph] = None,
        pred_graph: Optional[ProcedureGraph] = None,
        validation_reports: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Compute all metrics."""
        am_p, am_r, am_f1 = self.action_mention_f1()
        ata = self.action_type_accuracy()
        tga = self.target_grounding_accuracy()
        pg_p, pg_r, pg_f1 = self.parameter_grounding_f1()
        es_p, es_r, es_f1 = self.evidence_span_f1()
        cf_p, cf_r, cf_f1 = self.control_flow_edge_f1(gt_graph, pred_graph)
        vpr = self.validation_pass_rate(validation_reports or []) if validation_reports else 0.0

        return {
            "action_mention_precision": am_p,
            "action_mention_recall": am_r,
            "action_mention_f1": am_f1,
            "action_type_accuracy": ata,
            "target_grounding_accuracy": tga,
            "parameter_grounding_precision": pg_p,
            "parameter_grounding_recall": pg_r,
            "parameter_grounding_f1": pg_f1,
            "evidence_span_precision": es_p,
            "evidence_span_recall": es_r,
            "evidence_span_f1": es_f1,
            "control_flow_precision": cf_p,
            "control_flow_recall": cf_r,
            "control_flow_f1": cf_f1,
            "validation_pass_rate": vpr,
        }


class DatasetMetrics:
    """Aggregates metrics across a dataset of documents."""

    def __init__(self):
        self.per_doc_metrics: List[Dict[str, Any]] = []

    def add_doc(
        self,
        doc_id: str,
        ground_truth: List[ActionIR],
        predicted: List[ActionIR],
        gt_graph: Optional[ProcedureGraph] = None,
        pred_graph: Optional[ProcedureGraph] = None,
        validation_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metrics = ExtractionMetrics(ground_truth, predicted)
        report = validation_report or {}
        doc_metrics = metrics.compute_all(
            gt_graph=gt_graph,
            pred_graph=pred_graph,
            validation_reports=[report],
        )
        doc_metrics["doc_id"] = doc_id
        self.per_doc_metrics.append(doc_metrics)
        return doc_metrics

    def aggregate(self) -> Dict[str, Any]:
        """Compute mean and std across all documents."""
        if not self.per_doc_metrics:
            return {}

        keys = [k for k in self.per_doc_metrics[0].keys() if k != "doc_id"]
        result = {}
        for key in keys:
            values = [m[key] for m in self.per_doc_metrics if key in m]
            result[f"{key}_mean"] = sum(values) / len(values) if values else 0.0
            if len(values) > 1:
                import statistics
                result[f"{key}_std"] = statistics.stdev(values)
            result[f"{key}_values"] = values

        result["num_docs"] = len(self.per_doc_metrics)
        return result


def main():
    import argparse
    from utils import read_jsonl, read_json, write_json

    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", type=pathlib.Path, required=True, help="synthetic_docs.jsonl")
    parser.add_argument("--predicted", type=pathlib.Path, required=True, help="grounded_actions.jsonl or procedure_graphs.jsonl")
    parser.add_argument("--validation", type=pathlib.Path, help="validation_report.json")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    gt_docs = {d["doc_id"]: d for d in read_jsonl(args.ground_truth)}
    pred_docs = {d["doc_id"]: d for d in read_jsonl(args.predicted)}

    validation_reports = {}
    if args.validation:
        val_data = read_json(args.validation)
        for r in val_data.get("reports", []):
            validation_reports[r["doc_id"]] = r

    dataset_metrics = DatasetMetrics()

    for doc_id in gt_docs:
        gt_doc = gt_docs[doc_id]
        pred_doc = pred_docs.get(doc_id, {})

        gt_actions = [ActionIR.from_dict(a) for a in gt_doc.get("ground_truth_actions", [])]
        pred_actions = [ActionIR.from_dict(a) for a in pred_doc.get("actions", [])]

        gt_graph = gt_doc.get("ground_truth_graph")
        pred_graph = pred_doc.get("graph")
        gt_graph_obj = ProcedureGraph.from_dict(gt_graph) if gt_graph else None
        pred_graph_obj = ProcedureGraph.from_dict(pred_graph) if pred_graph else None

        dataset_metrics.add_doc(
            doc_id=doc_id,
            ground_truth=gt_actions,
            predicted=pred_actions,
            gt_graph=gt_graph_obj,
            pred_graph=pred_graph_obj,
            validation_report=validation_reports.get(doc_id),
        )

    agg = dataset_metrics.aggregate()
    write_json(args.output, agg)

    print("=" * 60)
    print("PAPER 2: ONTOLOGY-GROUNDED ACTION EXTRACTION METRICS")
    print("=" * 60)
    print(f"Documents evaluated: {agg.get('num_docs', 0)}")
    print(f"Action Mention F1:     {agg.get('action_mention_f1_mean', 0):.3f}")
    print(f"Action-Type Accuracy:  {agg.get('action_type_accuracy_mean', 0):.3f}")
    print(f"Target Grounding Acc:  {agg.get('target_grounding_accuracy_mean', 0):.3f}")
    print(f"Parameter Grounding F1:{agg.get('parameter_grounding_f1_mean', 0):.3f}")
    print(f"Evidence Span F1:      {agg.get('evidence_span_f1_mean', 0):.3f}")
    print(f"Control-Flow Edge F1:  {agg.get('control_flow_f1_mean', 0):.3f}")
    print(f"Validation Pass Rate:  {agg.get('validation_pass_rate_mean', 0):.3f}")
    print("=" * 60)
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
