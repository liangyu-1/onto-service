#!/usr/bin/env python3
"""Run all paper2 action extraction experiments and save results."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from utils import ensure_dir, read_jsonl, write_json, write_jsonl, utc_ts, snapshot_environment, file_hash
from action_ir import ActionIR, ProcedureGraph
from metrics import DatasetMetrics
from llm_client import OpenAIClient
from kimi_cli_client import KimiCLIClient

from baselines.rule_baseline import RuleBaseline
from baselines.llm_only_baseline import LLMOnlyBaseline
from baselines.llm_ontology_prompt_baseline import LLMOntologyPromptBaseline
from baselines.ours_baseline import OursBaseline

from agents.document_synthesizer import DocumentSynthesizer
from agents.validator import Validator


RUNNER_VERSION = "paper2_extraction_v1"


def get_llm_client(args) -> Any:
    """Create LLM client based on CLI args."""
    if args.use_kimi_cli:
        return KimiCLIClient(model=args.model)
    elif args.use_heuristic_client:
        # For paper2, heuristic client is not meaningful — use rule baseline instead
        return None
    else:
        return OpenAIClient(model=args.model, base_url=args.base_url)


def run_method(
    method_name: str,
    docs: List[Dict[str, Any]],
    extractor: Any,
    validator: Optional[Validator] = None,
) -> Dict[str, Any]:
    """Run a single extraction method on all documents."""
    results = []
    start_time = time.time()

    for doc in docs:
        doc_id = doc["doc_id"]
        doc_text = doc["text"]

        try:
            result = extractor.extract(doc_text, doc_id=doc_id)
        except Exception as e:
            print(f"  ERROR in {method_name} for {doc_id}: {e}")
            result = {
                "doc_id": doc_id,
                "actions": [],
                "graph": {"nodes": [], "edges": []},
                "doc_text": doc_text,
                "error": str(e),
            }

        # Validate if validator provided
        if validator and "error" not in result:
            actions = [ActionIR.from_dict(a) for a in result.get("actions", [])]
            graph = ProcedureGraph.from_dict(result["graph"]) if result.get("graph") else None
            val_report = validator.validate(actions, graph, doc_text)
            val_report.doc_id = doc_id
            result["validation"] = val_report.to_dict()

        results.append(result)

    elapsed = time.time() - start_time

    return {
        "method": method_name,
        "results": results,
        "elapsed_seconds": elapsed,
    }


def evaluate_method(
    method_result: Dict[str, Any],
    gt_docs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate a method's results against ground truth."""
    dataset_metrics = DatasetMetrics()

    for result in method_result["results"]:
        doc_id = result["doc_id"]
        gt_doc = gt_docs.get(doc_id, {})

        gt_actions = [ActionIR.from_dict(a) for a in gt_doc.get("ground_truth_actions", [])]
        pred_actions = [ActionIR.from_dict(a) for a in result.get("actions", [])]

        gt_graph = gt_doc.get("ground_truth_graph")
        pred_graph = result.get("graph")
        gt_graph_obj = ProcedureGraph.from_dict(gt_graph) if gt_graph else None
        pred_graph_obj = ProcedureGraph.from_dict(pred_graph) if pred_graph else None

        validation_report = result.get("validation")

        dataset_metrics.add_doc(
            doc_id=doc_id,
            ground_truth=gt_actions,
            predicted=pred_actions,
            gt_graph=gt_graph_obj,
            pred_graph=pred_graph_obj,
            validation_report=validation_report,
        )

    agg = dataset_metrics.aggregate()
    agg["method"] = method_result["method"]
    agg["elapsed_seconds"] = method_result["elapsed_seconds"]
    return agg


def main():
    parser = argparse.ArgumentParser(description="Run paper2 action extraction experiments")
    parser.add_argument("--use-kimi-cli", action="store_true", help="Use Kimi CLI client")
    parser.add_argument("--use-heuristic-client", action="store_true", help="Use heuristic client (not for paper)")
    parser.add_argument("--model", default="kimi-latest", help="Model name")
    parser.add_argument("--base-url", default="http://localhost:9999/v1", help="OpenAI-compatible API base URL")
    parser.add_argument("--methods", nargs="+", default=["Rule", "LLM-Only", "LLM-Ontology", "Ours"],
                        help="Methods to evaluate")
    parser.add_argument("--output-dir", type=pathlib.Path, default=BASE_DIR / "results",
                        help="Output directory")
    parser.add_argument("--num-docs", type=int, default=None,
                        help="Limit number of documents (for testing)")
    parser.add_argument("--generate-docs", action="store_true",
                        help="Regenerate synthetic documents")
    parser.add_argument("--action-bank", type=pathlib.Path,
                        default=BASE_DIR.parent / "paper3_agent_planning" / "data" / "action_bank" / "retail_action_bank.json")
    parser.add_argument("--tasks", type=pathlib.Path,
                        default=BASE_DIR.parent / "paper3_agent_planning" / "data" / "raw" / "retail" / "tasks.json")
    parser.add_argument("--split", type=pathlib.Path,
                        default=BASE_DIR.parent / "paper3_agent_planning" / "data" / "raw" / "retail" / "split_tasks.json")
    parser.add_argument("--split-name", default="test")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    timestamp = utc_ts()
    out_dir = ensure_dir(args.output_dir / f"run_{timestamp}")
    print(f"Output directory: {out_dir}")

    # Copy ground truth action bank to our data dir
    gt_dir = ensure_dir(BASE_DIR / "data" / "ground_truth")
    import shutil
    shutil.copy(args.action_bank, gt_dir / "action_bank.json")

    # ------------------------------------------------------------------
    # Generate or load synthetic documents
    # ------------------------------------------------------------------
    docs_path = BASE_DIR / "data" / "synthetic_docs" / f"{args.split_name}_docs.jsonl"
    if args.generate_docs or not docs_path.exists():
        print("Generating synthetic documents...")
        synth = DocumentSynthesizer(
            action_bank_path=args.action_bank,
            tasks_path=args.tasks,
            split_path=args.split,
        )
        docs = synth.generate(split_name=args.split_name, out_path=docs_path)
        print(f"  Generated {len(docs)} documents")
    else:
        print(f"Loading synthetic documents from {docs_path}")
        docs = [SyntheticDocument.from_dict(d) for d in read_jsonl(docs_path)]
        from action_ir import SyntheticDocument
        docs = [SyntheticDocument.from_dict(d) for d in read_jsonl(docs_path)]
        print(f"  Loaded {len(docs)} documents")

    if args.num_docs:
        docs = docs[:args.num_docs]
        print(f"  Limited to {len(docs)} documents")

    # Convert to dicts for processing
    doc_dicts = [d.to_dict() for d in docs]
    gt_docs = {d["doc_id"]: d for d in doc_dicts}

    # ------------------------------------------------------------------
    # Initialize extractors
    # ------------------------------------------------------------------
    llm = get_llm_client(args) if not args.use_heuristic_client else None

    extractors = {}
    if "Rule" in args.methods:
        extractors["Rule"] = RuleBaseline(action_bank_path=args.action_bank)
    if "LLM-Only" in args.methods and llm:
        extractors["LLM-Only"] = LLMOnlyBaseline(llm=llm)
    if "LLM-Ontology" in args.methods and llm:
        extractors["LLM-Ontology"] = LLMOntologyPromptBaseline(
            llm=llm, action_bank_path=args.action_bank
        )
    if "Ours" in args.methods and llm:
        extractors["Ours"] = OursBaseline(
            llm=llm,
            action_bank_path=args.action_bank,
            use_llm_units=True,
            use_llm_ir=True,
        )

    # ------------------------------------------------------------------
    # Validator
    # ------------------------------------------------------------------
    validator = Validator(action_bank_path=args.action_bank)

    # ------------------------------------------------------------------
    # Run experiments
    # ------------------------------------------------------------------
    all_method_results = {}
    all_evaluations = {}

    for method_name, extractor in extractors.items():
        print(f"\n{'='*60}")
        print(f"Running method: {method_name}")
        print(f"{'='*60}")

        method_result = run_method(method_name, doc_dicts, extractor, validator=validator)
        all_method_results[method_name] = method_result

        # Save per-method results
        method_out = out_dir / f"{method_name}_results.json"
        write_json(method_out, method_result)
        print(f"  Saved results → {method_out}")

        # Evaluate
        eval_result = evaluate_method(method_result, gt_docs)
        all_evaluations[method_name] = eval_result

        print(f"  Elapsed: {eval_result['elapsed_seconds']:.1f}s")
        print(f"  Action Mention F1:      {eval_result.get('action_mention_f1_mean', 0):.3f}")
        print(f"  Action-Type Accuracy:   {eval_result.get('action_type_accuracy_mean', 0):.3f}")
        print(f"  Target Grounding Acc:   {eval_result.get('target_grounding_accuracy_mean', 0):.3f}")
        print(f"  Parameter Grounding F1: {eval_result.get('parameter_grounding_f1_mean', 0):.3f}")
        print(f"  Evidence Span F1:       {eval_result.get('evidence_span_f1_mean', 0):.3f}")
        print(f"  Control-Flow Edge F1:   {eval_result.get('control_flow_f1_mean', 0):.3f}")
        print(f"  Validation Pass Rate:   {eval_result.get('validation_pass_rate_mean', 0):.3f}")

    # ------------------------------------------------------------------
    # Save combined results
    # ------------------------------------------------------------------
    combined = {
        "run_id": f"paper2_{timestamp}",
        "runner_version": RUNNER_VERSION,
        "methods": list(extractors.keys()),
        "num_docs": len(docs),
        "evaluations": all_evaluations,
        "metadata": {
            "timestamp": timestamp,
            "model": args.model,
            "use_kimi_cli": args.use_kimi_cli,
            "environment": snapshot_environment(),
            "action_bank_hash": file_hash(args.action_bank),
        },
    }

    combined_path = out_dir / "combined_results.json"
    write_json(combined_path, combined)
    print(f"\nCombined results saved → {combined_path}")

    # ------------------------------------------------------------------
    # Print summary table
    # ------------------------------------------------------------------
    print("\n" + "="*80)
    print("PAPER 2: ONTOLOGY-GROUNDED ACTION EXTRACTION — SUMMARY")
    print("="*80)
    print(f"{'Method':<15} {'ActionF1':>10} {'TypeAcc':>10} {'TargetAcc':>10} {'ParamF1':>10} {'EvidF1':>10} {'FlowF1':>10} {'ValPass':>10}")
    print("-"*80)
    for method_name in args.methods:
        ev = all_evaluations.get(method_name, {})
        print(f"{method_name:<15} "
              f"{ev.get('action_mention_f1_mean', 0):>10.3f} "
              f"{ev.get('action_type_accuracy_mean', 0):>10.3f} "
              f"{ev.get('target_grounding_accuracy_mean', 0):>10.3f} "
              f"{ev.get('parameter_grounding_f1_mean', 0):>10.3f} "
              f"{ev.get('evidence_span_f1_mean', 0):>10.3f} "
              f"{ev.get('control_flow_f1_mean', 0):>10.3f} "
              f"{ev.get('validation_pass_rate_mean', 0):>10.3f}")
    print("="*80)


if __name__ == "__main__":
    main()
