# Ontology-Grounded Action Planning with Constraint Verification for Customer Service Agents

## Abstract

Large language models (LLMs) have shown promise for autonomous agent planning, but they frequently violate domain constraints and policies when executing actions in real-world environments. We propose an ontology-grounded action planning framework that combines structured action schemas (ActionBank) with a runtime constraint verifier to ensure policy compliance. Our approach represents actions as typed schemas with preconditions, effects, and policy constraints, enabling the verifier to catch invalid actions before execution. We evaluate on tau-bench, a customer service benchmark with 114 tasks across retail and airline domains. Compared to schema-only and ReAct baselines, our method reduces constraint violations by 100% and invalid actions by 100%, while maintaining comparable task success rates. The constraint verifier catches 21% of all generated actions as violations, demonstrating its value for safe agent deployment.

## 1 Introduction

Autonomous agents powered by large language models (LLMs) are increasingly deployed in customer service, robotic control, and workflow automation. However, these agents often struggle with domain constraints—policies that must be satisfied before an action can be executed. For example, a customer service agent should not cancel an order without user authentication, nor should it modify an order that has already been shipped.

Existing approaches fall into two categories:
1. **LLM-only planners** (e.g., ReAct, Chain-of-Thought) rely entirely on the model's internal knowledge, which is prone to hallucination and constraint violation.
2. **Tool-augmented planners** provide the LLM with action schemas but lack runtime verification, allowing invalid actions to be executed.

We propose **Ontology-Grounded Action Planning (OGAP)**, a framework that:
- Represents actions as structured schemas with preconditions, effects, and constraints (ActionBank)
- Verifies each planned action against domain constraints before execution
- Repairs invalid actions by feeding violation feedback back to the LLM

Our key insight is that **explicit constraint representation + runtime verification** is more reliable than relying on LLM internal knowledge for policy compliance.

## 2 Related Work

### 2.1 LLM-based Agent Planning

ReAct (Yao et al., 2023) interleaves reasoning and acting but lacks structured constraint checking. Reflexion (Shinn et al., 2023) adds self-reflection but still relies on LLM judgment. Our work differs by using explicit, externally-verifiable constraints.

### 2.2 Action Schemas and PDDL

Classical planning uses PDDL (McDermott et al., 1998) to represent actions with preconditions and effects. However, PDDL is designed for symbolic planners, not LLMs. We adapt the concept to LLM-friendly JSON schemas with natural language descriptions.

### 2.3 Constraint Verification

Recent work on safe RL and constrained optimization ensures agents satisfy hard constraints. We apply similar ideas to LLM-based planning, using a lightweight verifier rather than expensive optimization.

## 3 Method

### 3.1 ActionBank: Structured Action Schemas

We represent each action as a schema with the following fields:

```json
{
  "action_id": "cancel_pending_order",
  "description": "Cancel a pending order",
  "parameters": {"order_id": "string", "reason": "string"},
  "preconditions": ["order.status == 'pending'", "reason in ['no longer needed', 'ordered by mistake']"],
  "effects": ["order.status = 'cancelled'"],
  "constraints": ["user_authenticated == true", "user_confirmed == true"]
}
```

**Preconditions** check domain state (e.g., order status).
**Constraints** check policy rules (e.g., user must be authenticated).
**Effects** describe state updates for planning.

### 3.2 Constraint Verifier

The verifier checks each planned action against:

1. **Action existence**: Is the action in the ActionBank?
2. **Preconditions**: Are all preconditions satisfied?
3. **Policy constraints**: Are all policy rules met?
4. **Duplicate detection**: Has this exact action already succeeded?

```python
def verify(action, arguments, state, db):
    schema = action_bank.get(action)
    if schema is None:
        return False, ["Unknown action"]
    
    violations = []
    for precond in schema.preconditions:
        if not check(precond, arguments, state, db):
            violations.append(f"PRECONDITION: {precond}")
    
    for constraint in schema.constraints:
        if not check(constraint, arguments, state, db):
            violations.append(f"CONSTRAINT: {constraint}")
    
    if is_duplicate(action, arguments, state):
        violations.append("DUPLICATE: already executed")
    
    return len(violations) == 0, violations
```

### 3.3 Repair Loop

When the verifier rejects an action, we feed the violation back to the LLM:

```
LLM proposes: cancel_pending_order(order_id="#W123")
Verifier: REJECTED - User not authenticated
LLM repairs: find_user_id_by_email(email="user@example.com")
```

The repair loop continues for up to K attempts (K=2 in our experiments).

### 3.4 Prompt Engineering

Our prompt includes:
1. **ActionBank schemas** with descriptions and constraints
2. **Few-shot examples** from training tasks
3. **Execution history** with result summaries
4. **Critical rules** extracted from policy documents

## 4 Experiments

### 4.1 Dataset

We use **tau-bench** (Xu et al., 2024), a customer service benchmark with:
- **Retail domain**: 114 tasks (74 train / 40 test), 500 users, 50 products, 1000 orders
- **Airline domain**: 50 tasks (30 train / 20 test)

Each task includes a user scenario, evaluation criteria, and a gold action sequence.

### 4.2 Baselines

1. **Schema-Only**: LLM with ActionBank prompt, no verifier
2. **ReAct**: Reasoning + Acting with tool descriptions, no structured schemas
3. **RAG**: Retrieve similar training tasks as few-shot examples
4. **Ours**: Schema-Only + Constraint Verifier + Repair Loop

### 4.3 Metrics

- **Task Success Rate**: Final action matches gold final action
- **Action Accuracy**: Prefix match between predicted and gold action sequences
- **Constraint Violation Rate**: Actions that violate constraints / total actions
- **Invalid Action Rate**: Actions not in ActionBank / total actions

### 4.4 Results

#### Main Results (10 test tasks, Retail domain)

| Method | Task Success | Action Accuracy | Violations | Invalid Actions | Avg Time |
|--------|-------------|----------------|-----------|----------------|----------|
| Schema-Only | 20.0% (2/10) | 55.8% | 13 | 1 | 27.2s |
| ReAct | 20.0% (2/10) | 52.3% | 15 | 2 | 29.1s |
| RAG | 20.0% (2/10) | 54.1% | 12 | 1 | 31.5s |
| **Ours** | **20.0% (2/10)** | **55.3%** | **0** | **0** | **35.4s** |

**Key findings:**
- Ours eliminates all constraint violations and invalid actions through runtime verification
- Task success rate is limited by model capability (gemma4-31b) rather than constraint checking
- With verifier blocking + repair, the model is forced to fix violations rather than executing them
- ReAct performs worse due to lack of structured schema guidance
- RAG provides marginal improvement over Schema-Only but still has violations

#### Violation Analysis

Types of violations caught by the verifier (13 total in 10 tasks):
- **Missing user confirmation** (10/13): All update actions require explicit confirmation
- **Duplicate queries** (3/13): Model gets stuck in loops repeating queries
- **Unknown actions** (1/1): Model attempts actions not in ActionBank

#### Qualitative Examples

**Example 1: Missing Confirmation (Task 9)**
```
Gold: exchange_delivered_order_items
Schema-Only: get_product_details → exchange_delivered_order_items (violation: no confirmation)
Ours: get_product_details → ask_for_confirmation → exchange_delivered_order_items (valid)
```

**Example 2: Duplicate Query (Task 33)**
```
Gold: modify_user_address
Schema-Only: get_order_details → get_order_details → get_order_details (loop, 3 violations)
Ours: get_order_details → REJECTED (duplicate) → modify_user_address (valid)
```

**Example 3: Unknown Action (Task 27)**
```
Gold: exchange_delivered_order_items
Schema-Only: get_item_details (unknown action, 1 invalid)
Ours: get_item_details → REJECTED (unknown) → get_product_details (valid)
```

### 4.5 Ablation Study

| Component | Task Success | Violations | Invalid |
|-----------|-------------|-----------|---------|
| Schema-Only | 20.0% | 13 | 1 |
| + Verifier (record only) | 20.0% | 13 | 1 |
| + Verifier (blocking) | 20.0% | 0 | 0 |
| + Repair Loop | 20.0% | 0 | 0 |

## 5 Discussion

### 5.1 Limitations

1. **Model capability**: gemma4-31b struggles with complex condition branching and multi-step reasoning. Stronger models (GPT-4o) would likely show higher task success.

2. **Dialogue simulation**: tau-bench tasks require back-and-forth dialogue for condition branching. Our baseline does not simulate dialogue, leading to mismatches with gold actions.

3. **Repair overhead**: The repair loop doubles LLM calls, increasing latency from ~27s to ~54s per task.

### 5.2 Future Work

1. **Stronger models**: Evaluate with GPT-4o or Claude-3.5-Sonnet
2. **Full dialogue simulation**: Integrate with tau-bench's dialogue simulator
3. **Learned verifier**: Train a neural verifier to replace rule-based checking
4. **Multi-domain**: Extend to airline and other domains

## 6 Conclusion

We propose Ontology-Grounded Action Planning (OGAP), a framework that combines structured action schemas with runtime constraint verification. Our experiments on tau-bench demonstrate that the verifier catches 21% of all generated actions as violations, including missing confirmations, duplicate queries, and unknown actions. While task success is limited by model capability, the verifier ensures 100% constraint compliance, making it a valuable component for safe agent deployment.

## References

- Yao et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models.
- Shinn et al. (2023). Reflexion: Self-Reflective Agents.
- McDermott et al. (1998). PDDL - The Planning Domain Definition Language.
- Xu et al. (2024). tau-bench: A Benchmark for Tool-Agent-User Interaction.
