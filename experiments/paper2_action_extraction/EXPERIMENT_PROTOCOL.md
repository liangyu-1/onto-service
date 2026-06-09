# Paper 2 Experiment Protocol

Ontology-Grounded Action Extraction from Unstructured Procedural Documents

## Overview

This module evaluates how well different methods can extract structured action
representations from procedural documents and ground them to an ontology action
layer. We use **synthetic procedural documents** generated from tau-bench retail
tasks as a controlled, reproducible evaluation.

## Directory Structure

```
paper2_action_extraction/
├── data/
│   ├── synthetic_docs/      # Generated SOPs/scripts/manuals
│   ├── ground_truth/        # ActionBank as ground truth
│   └── splits/              # Train/test splits
├── src/
│   ├── agents/              # Multi-agent pipeline modules
│   ├── baselines/           # Baseline methods
│   ├── action_ir.py         # Action IR dataclasses
│   ├── metrics.py           # Evaluation metrics
│   ├── llm_client.py        # LLM clients (from paper3)
│   └── utils.py             # Shared utilities
├── run_experiments.py       # Main entry point
├── analyze_results.py       # Statistical analysis
├── export_paper_metrics.py  # LaTeX/Markdown export
└── EXPERIMENT_PROTOCOL.md   # This file
```

## Multi-Agent Pipeline

| Stage | Agent | Role |
|-------|-------|------|
| 0 | DocumentSynthesizer | Generate synthetic SOPs from ActionBank + tasks |
| 1 | StructureParser | Parse documents into structured chunks |
| 2 | UnitExtractor | Extract procedural units (operations, conditions, etc.) |
| 3 | ActionIRBuilder | Compile units into Action IR records |
| 4 | OntologyGrounder | Ground Action IR fields to ontology candidates |
| 5 | GraphBuilder | Build procedure graph with control-flow edges |
| 6 | Validator | Validate against ontology schema + evidence traceability |
| 7 | Evaluator | Compute metrics against ground truth |

## Methods

- **Rule**: Regex + keyword matching, no LLM
- **LLM-Only**: Direct LLM extraction without ontology context
- **LLM-Ontology**: LLM extraction with ActionBank in prompt
- **Ours**: Full multi-agent pipeline with structure parsing, unit extraction, grounding, validation

## Metrics

| Metric | Description |
|--------|-------------|
| Action Mention F1 | Did we find the right actions? |
| Action-Type Accuracy | Correct action type mapping? |
| Target Grounding Accuracy | Correct target object type? |
| Parameter Grounding F1 | Correct parameters recovered? |
| Evidence-Span F1 | Evidence text traceable to source? |
| Control-Flow Edge F1 | Correct control-flow relations? |
| Validation Pass Rate | % of actions passing ontology validation |

## Running Experiments

### Full run (paper-grade)

```bash
cd experiments/paper2_action_extraction
python run_experiments.py \
  --use-kimi-cli \
  --model kimi-latest \
  --methods Rule LLM-Only LLM-Ontology Ours \
  --output-dir results_kimi \
  --generate-docs
```

### Quick smoke test (rule baseline only)

```bash
cd experiments/paper2_action_extraction
python run_experiments.py \
  --methods Rule \
  --num-docs 3 \
  --output-dir /tmp/paper2_smoke \
  --generate-docs
```

### Individual pipeline stages

```bash
# 1. Generate documents
python src/agents/document_synthesizer.py \
  --action-bank ../paper3_agent_planning/data/action_bank/retail_action_bank.json \
  --tasks ../paper3_agent_planning/data/raw/retail/tasks.json \
  --split ../paper3_agent_planning/data/raw/retail/split_tasks.json \
  --out data/synthetic_docs/test_docs.jsonl

# 2. Parse structure
python src/agents/structure_parser.py \
  --input data/synthetic_docs/test_docs.jsonl \
  --output data/parsed_chunks.jsonl

# 3. Extract units
python src/agents/unit_extractor.py \
  --input data/parsed_chunks.jsonl \
  --output data/procedural_units.jsonl

# 4. Build Action IR
python src/agents/action_ir_builder.py \
  --input data/procedural_units.jsonl \
  --output data/action_ir_candidates.jsonl

# 5. Ground to ontology
python src/agents/ontology_grounder.py \
  --input data/action_ir_candidates.jsonl \
  --output data/grounded_actions.jsonl \
  --action-bank ../paper3_agent_planning/data/action_bank/retail_action_bank.json

# 6. Build graph
python src/agents/graph_builder.py \
  --input data/grounded_actions.jsonl \
  --output data/procedure_graphs.jsonl

# 7. Validate
python src/agents/validator.py \
  --input data/procedure_graphs.jsonl \
  --output data/validation_report.json \
  --action-bank ../paper3_agent_planning/data/action_bank/retail_action_bank.json \
  --docs data/synthetic_docs/test_docs.jsonl

# 8. Evaluate metrics
python src/metrics.py \
  --ground-truth data/synthetic_docs/test_docs.jsonl \
  --predicted data/grounded_actions.jsonl \
  --validation data/validation_report.json \
  --output data/metrics.json
```

## Analysis

```bash
# Statistical analysis
python analyze_results.py results_kimi/run_YYYYMMDD_HHMMSS --out analysis.json

# Export paper tables
python export_paper_metrics.py results_kimi/run_YYYYMMDD_HHMMSS \
  --json-out results_kimi/paper_metrics.json \
  --md-out results_kimi/paper_metrics.md
```

## Claim Guidance

Supported claims when results are present:
- Multi-agent extraction improves action mention F1 over rule-based and LLM-only baselines
- Ontology grounding improves target type accuracy and parameter recovery
- Structured validation catches extraction errors that LLM-only methods miss

Not supported without additional evaluation:
- Generalization to real-world SOPs (synthetic documents only)
- Cross-domain transfer
- Human evaluation of evidence faithfulness
