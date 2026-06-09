# Paper 3: Agent Planning with Ontology-Grounded Action Layer

## Overview

This experiment validates the core hypothesis:

> **Does an ontology-grounded action layer with constraint verifier significantly
> reduce policy violations and invalid actions compared to LLM-only planning?**

## Structure

```
paper3_agent_planning/
├── data/
│   ├── raw/retail/          # tau-bench retail data (downloaded from GitHub)
│   ├── raw/airline/         # tau-bench airline data
│   └── action_bank/         # Hand-crafted action schemas
├── src/
│   ├── data_loader.py       # Parse tau-bench JSON files
│   ├── action_bank.py       # Action schema definitions
│   ├── state_manager.py     # Dialogue state tracking
│   ├── simulator.py         # Retail domain simulator
│   ├── verifier.py          # Constraint/precondition checker
│   ├── planner.py           # Our method: LLM + ActionBank + Verifier + Repair
│   ├── llm_client.py        # LLM wrappers (OpenAI / Local / Heuristic)
│   └── baselines/
│       ├── react_baseline.py      # ReAct (LLM-only)
│       ├── rag_baseline.py        # Tool Retrieval + LLM
│       ├── schema_baseline.py     # ActionBank prompt only
│       └── heuristic_llm.py       # Rule-based agent for pipeline validation
├── eval/
│   ├── metrics.py           # Evaluation metrics
│   ├── runner.py            # Single task runner
│   └── evaluate_all.py      # Run all baselines
└── results/                 # Experiment outputs
```

## Data Source

- **tau-bench** (sierra-research/tau2-bench on GitHub)
  - Retail: 114 tasks (train 74 / test 40)
  - Airline: 50 tasks (train 30 / test 20)
  - Each task has: user scenario, gold action sequence, evaluation criteria

## ActionBank

The retail ActionBank contains 16 action schemas with:
- Parameters (with types)
- Preconditions (e.g., `order.status == 'pending'`)
- Effects (e.g., `order.status = 'cancelled'`)
- Constraints (e.g., `user_authenticated == true`, `user_confirmed == true`)

## Baselines

1. **ReAct**: LLM-only, no action layer
2. **RAG**: Retrieve relevant tools then plan
3. **Schema-only**: Full ActionBank in prompt, no runtime verifier
4. **Ours**: ActionBank + Constraint Verifier + Repair Loop

## Metrics

- Task Success Rate
- Action Accuracy@k
- Policy Violation Rate
- Invalid Action Rate
- Constraint Violation Rate
- Repair Success Rate

## Running Experiments

### With OpenAI API (recommended)

```bash
export OPENAI_API_KEY="your-key"
cd experiments/paper3_agent_planning
python eval/evaluate_all.py
```

### With Local Model (Qwen2.5-3B or similar)

```bash
# Model will be downloaded automatically on first run
cd experiments/paper3_agent_planning
python eval/evaluate_all.py
```

### Pipeline Validation (no LLM)

```bash
cd experiments/paper3_agent_planning
python eval/runner.py
```

## Current Status

- ✅ Data downloaded and parsed
- ✅ ActionBank constructed (16 actions)
- ✅ Simulator implemented (all retail tools)
- ✅ Verifier implemented (precondition + constraint checking)
- ✅ Pipeline validated (gold baseline: 100% accuracy on 5 tasks)
- ⏳ Real LLM evaluation pending (needs OpenAI key or local model download)
- ⏳ Full test set evaluation pending

## Next Steps

1. Obtain OpenAI API key or download local model
2. Run all baselines on retail test set (40 tasks)
3. Compute statistical significance
4. If results are significant, start paper draft
