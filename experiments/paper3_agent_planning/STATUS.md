# Paper 3: Agent Planning — Current Status

## ✅ Completed

### Infrastructure
- [x] tau-bench data downloaded (Retail 114 tasks, Airline 50 tasks)
- [x] ActionBank constructed (16 action schemas for retail)
- [x] Simulator implemented (all retail tools)
- [x] Verifier implemented (precondition + constraint checking)
- [x] LLM client (OpenAI-compatible, works with local vLLM)
- [x] Evaluation metrics and runner

### Verification Demo
The verifier successfully catches these common LLM errors:
1. **Cancel without auth** → FAIL (user not authenticated)
2. **Cancel non-pending order** → FAIL (wrong status)
3. **Exchange without confirmation** → FAIL (no user confirmation)
4. **Return from pending order** → FAIL (wrong status)
5. **Correct action** → PASS

### Pipeline Validation
- Gold baseline: 100% accuracy on test tasks (verifier + simulator work correctly)
- End-to-end pipeline runs without errors

## ⚠️ Current Limitation

### LLM Capability
The available local model (gemma4-31b) is **not capable enough** for multi-step action planning:
- Gets stuck repeating the same action
- Can't parse task descriptions correctly
- Doesn't learn from execution feedback
- Makes wrong assumptions about DB contents

This is actually **expected** and **valuable for the paper**:
- It demonstrates that even with ActionBank, weak LLMs fail
- The verifier catches their errors
- A stronger model + repair loop would be needed for "Ours"

## 🔜 Next Steps

### Option 1: Use Stronger Model (Recommended)
Get access to GPT-4o / Claude-3.5-Sonnet / Qwen3-72B:
```bash
export OPENAI_API_KEY="..."
python eval/evaluate_all.py
```

### Option 2: Improve Local Model
- Configure Qwen3.6-27B to output actual content (not just reasoning)
- Or download a stronger model (Qwen2.5-72B, Llama-3.1-70B)

### Option 3: Simplify Experiment
- Use fewer steps per task (1-2 actions)
- Focus on single-decision tasks (auth → action)
- Demonstrate verifier value on simple cases

### Option 4: Write Paper Draft
Start writing while solving the LLM issue in parallel:
- Introduction + Related Work
- Method section (ActionBank + Verifier architecture)
- Experiment setup (tau-bench, metrics)
- Placeholder for results

## 📊 Expected Results (Hypothesis)

With a capable LLM, we expect:

| Method | Task Success | Policy Violations | Invalid Actions |
|--------|-------------|-------------------|-----------------|
| ReAct (no action layer) | ~30% | High | High |
| Schema-only (no verifier) | ~50% | Medium | Medium |
| **Ours (Schema + Verifier)** | **~70%** | **Low** | **Low** |

## 📝 Paper Title Ideas

1. "Ontology-Grounded Action Planning with Constraint Verification for LLM Agents"
2. "ActionBank: Structured Action Layers for Policy-Constrained Agent Planning"
3. "Reducing Policy Violations in LLM Agents through Ontology-Grounded Action Verification"

## 🏗️ Architecture Diagram

```
User Request
    ↓
[Task Parser] → Goal + Constraints
    ↓
[ActionBank] → Relevant Action Schemas
    ↓
[LLM Planner] → Proposed Action
    ↓
[Constraint Verifier] → Check Preconditions + Policy
    ↓
    ├─ PASS → [Simulator] → Execute → Update State
    └─ FAIL → [Repair Loop] → Feedback to LLM → Retry
    ↓
[Response]
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `data/action_bank/retail_action_bank.json` | 16 action schemas |
| `src/simulator.py` | Retail domain simulator |
| `src/verifier.py` | Constraint/precondition checker |
| `src/planner.py` | Our method (LLM + ActionBank + Verifier) |
| `eval/verifier_demo.py` | Demonstrates verifier catching errors |
| `eval/runner.py` | End-to-end task runner |
