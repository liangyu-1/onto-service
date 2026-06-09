# Paper 3 实验显著性分析

> 分析日期: 2026-06-09  
> 模型: Kimi-latest (via Kimi CLI, temperature=0)  
> 样本量: 40 test tasks (tau-bench retail)  
> 主结果文件: `results_kimi_40/all_results_combined.json`  
> 分析脚本: `analyze_results.py`

---

## 一、主结果

### 1.1 汇总指标

| 指标 | Schema-Only | Ours | 变化 |
|------|-------------|------|------|
| Task Success Rate | 16/40 = **40.0%** | 18/40 = **45.0%** | +5pp |
| Avg Action Accuracy | **37.1%** | **37.9%** | +0.8pp |
| Total Violations | **83** | **0** | -83 |
| Total Invalid Actions | 0 | 0 | 0 |
| Avg Time per Task | 101.0s | 112.9s | +11.9s |

### 1.2 Paired Outcome

| Case Type | Count |
|---|---:|
| Both succeed | 12 |
| Schema fails, Ours succeeds | 6 |
| Schema succeeds, Ours fails | 4 |
| Both fail | 18 |

Exact McNemar/binomial test:

```text
b = 6
c = 4
chi-square = 0.40
exact two-sided p = 0.7539
```

Conclusion: the task-success improvement is **not statistically significant** at `p < 0.05`.

---

## 二、三类显著性判断

### 2.1 统计显著性

**Task success 不显著。**

虽然 Ours 从 40.0% 提升到 45.0%，但 paired improvement 很小：6 个任务改善，4 个任务变差。exact McNemar/binomial test 的 `p=0.7539`，不能声称 task success 显著提升。

**Violation reduction 是确定性的工程效果，但不等同于 task success 显著。**

Ours 的 verifier 阻断所有 observed executed violations，因此 executed violation 从 83 降到 0。这个结果幅度很大，但要注意它主要衡量 execution compliance，不是端到端任务完成能力。

### 2.2 实际效果显著性

**Constraint/violation control 显著。**

| 指标 | Schema-Only | Ours | 相对变化 |
|------|-------------|------|---------|
| Violation per task | 2.075 | 0 | 100%↓ |
| Executed violation count | 83 | 0 | 100%↓ |

**Task success 效果较弱。**

| 指标 | Schema-Only | Ours | 变化 |
|------|-------------|------|------|
| Success Rate | 40.0% | 45.0% | +5pp |

这个提升不能作为强贡献。论文应把主结论放在 runtime verification / execution compliance，而不是 action planning success。

### 2.3 论文论点显著性

| 论点 | 当前证据 | 评价 |
|------|---------|------|
| action layer verifier 减少执行违规 | 83 -> 0 | 强支持 |
| repair loop 提升 task success | 40% -> 45%, p=0.7539 | 弱支持，不显著 |
| action grounding 减少 invalid actions | 两边都是 0 | 无法区分 |
| 方法具备 state-aware planning 能力 | counterfactual SSA=20% | 不支持 |
| 方法解决复杂 policy / branch reasoning | 22/40 两边都失败 | 不支持 |

---

## 三、Violation 类型分析

Schema-Only 的 83 个 violations:

| Violation Type | Count | Ratio |
|---|---:|---:|
| Duplicate action | 74 | 89.2% |
| Missing user confirmation / constraint | 9 | 10.8% |
| Unknown action | 0 | 0% |
| Precondition failure | 0 | 0% |
| Policy violation | 0 | 0% |

Interpretation:

- 当前 verifier 最主要的作用是阻断重复查询循环。
- Kimi-latest 本身已经较好地 grounding 到 ActionBank，因此 invalid action 为 0。
- 当前实验没有证明 verifier 能大量修复复杂 precondition、policy 或 state-transition 错误。

---

## 四、Counterfactual State Test

结果文件: `results_kimi_counterfactual/counterfactual_20260608_172123.json`

| Task | Original Final | Modified State | Counterfactual Final | Changed |
|---|---|---|---|---|
| 5 | return | order=pending | return | No |
| 26 | return | order=pending | return | No |
| 32 | transfer_to_human | order=delivered | cancel | Yes |
| 38 | loop | order=delivered | loop | No |
| 51 | return | order=pending | return | No |

State Sensitivity Accuracy:

```text
SSA = 1/5 = 20%
```

Conclusion: current method is **not state-sensitive enough**. This result should be written as a diagnostic limitation, not as supporting evidence.

---

## 五、Ablation 状态

结果文件: `results_kimi_ablation_10/all_ablation_20260608_190950.json`

Valid ablations:

| Variant | Tasks | Success | Violations | Notes |
|---|---:|---:|---:|---|
| PrecondOnly | 10 | 5/10 | 15 | catches some confirmation issues, still allows duplicate loops |
| BlockingNoRepair | 10 | 2/10 | 0 | blocks violations but loses recoverability |

Invalid ablation:

| Variant | Problem |
|---|---|
| DupOnly | 10/10 runs failed with `DuplicateOnlyPlanner object has no attribute _build_system_prompt` |

Interpretation:

- Blocking improves compliance but can reduce task success when there is no repair.
- Repair is likely important for recoverability, but current ablation is only 10 tasks.
- DupOnly cannot be used until the implementation bug is fixed and rerun.

---

## 六、诚实结论

### 什么成立

1. Action-layer verifier can eliminate observed executed violations on 40 tau-bench retail tasks.
2. Most verifier benefit currently comes from duplicate-loop blocking and missing-confirmation blocking.
3. Repair can recover some tasks, but the end-to-end success gain is small and statistically non-significant.

### 什么不成立

1. Cannot claim significant task success improvement.
2. Cannot claim robust state-aware planning.
3. Cannot claim broad policy/precondition reasoning improvement, because observed violation diversity is limited.
4. Cannot use the DupOnly ablation until it is fixed and rerun.

### Recommended paper claim

The paper should claim:

> Action-layer verification is useful as a runtime execution-control mechanism for policy-constrained LLM agents. It reliably blocks observed violations, especially duplicate loops and missing confirmations, but it does not by itself solve state-aware branch reasoning or long-horizon dialogue planning.

It should not claim:

> The method significantly improves agent planning success or solves ontology-grounded state-aware planning.

