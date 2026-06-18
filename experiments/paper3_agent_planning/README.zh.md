# 论文三：基于本体约束的 Action Planning 实验

本目录包含第三篇论文设想的实验代码：在策略约束的工具调用任务中，使用本体驱动的动作层提升 LLM agent 的规划与执行可靠性。

当前实验只围绕两类证据组织：

1. 官方 tau2 任务表现：方法是否能在官方 tau2/tau-bench runner 和 reward 下提升任务成功率。
2. 本体语义诊断：canonical Action IR、投影得到的 ActionBank、参数 grounding、约束 verifier 是否真的编码了论文声称的动作语义。

旧的本地 toy runner 和 Kimi 结果目录已经移除，因为它们不能支撑论文级 tau-bench task-performance claim。

关键 schema 约定如下：

```text
Paper2 SOP 抽取 -> canonical Action IR -> deterministic ActionBank projection -> Paper3 agent
```

`data/action_ir/retail_action_ir.json` 是 Paper2 和 Paper3 共享的 canonical schema。`data/action_bank/retail_action_bank.json` 从它编译生成，只保留 tau2 agent 运行所需字段。

运行时方法将 action 语义分成两类 grounding regime：

- Epistemic action（`action_kind=epistemic`，`grounding_mode=weak`）：用于获取世界状态，例如用户、订单、商品查询。它们需要具体输入 identifier 和认证等策略前提，但不能要求目标对象已经存在于 runtime cache 中。
- Mutating action（`action_kind=mutate`，`grounding_mode=strong`）：用于改变环境状态。它们必须要求目标对象已被工具观察到，参数完成角色绑定，并满足 policy precondition 与用户确认。

这个区分是论文主张的一部分：本体层不应只做拒绝器，还必须保留获取状态所需的探索动作，从而支撑后续状态变更动作的可靠 grounding。

## 代码用途

### 官方 tau2 实验链路

这条链路用于支撑论文中关于任务成功率提升的主实验结论。

| 文件 | 用途 |
| --- | --- |
| `tau2_ontology_agent.py` | 自定义 tau2 half-duplex agent。向官方 tau2 runner 暴露论文定义的 `schema`、`ontology_prompt`、`state_only`、`typed_admissibility` 和 `ontology_full`。 |
| `make_heldout_tau2_commands.py` | 排除已调试任务后采样 held-out task ids，并输出匹配的 schema/ontology tau2 命令。 |
| `run_official_tau2_pair.py` | 一键运行 baseline 与 ontology 方法的 paired comparison，并串联 import/report 步骤。 |
| `preflight_official_tau2.py` | 在昂贵实验前检查 Action IR projection、ActionBank、tau2 import、自定义 agent 注册和模型 endpoint。 |
| `import_tau2_results.py` | 将官方 tau2 输出目录或结果文件转换成后续分析使用的 paired JSON 格式。 |
| `analyze_results.py` | 计算 paired success delta、McNemar/binomial test、task-cluster sign test，以及 claim-readiness 阻塞原因。 |
| `report_official_results.py` | 从导入后的官方结果生成论文表格用 markdown report。 |
| `validate_official_results.py` | 在把数字写进论文前做 fail-fast 校验。 |
| `compile_action_ir_to_action_bank.py` | 将 canonical Action IR 编译成 Paper3 使用的 runtime ActionBank JSON。 |

### 本体语义诊断链路

这条链路用于证明 ontology/action-layer 机制本身实现一致，而不是只看端到端成功率。

| 文件 | 用途 |
| --- | --- |
| `run_ontology_benchmarks.py` | 运行确定性诊断，包括状态敏感 admissibility、counterfactual state test、role binding、effect consistency 和组件消融。 |
| `src/action_bank.py` | 加载 canonical Action IR 或投影后的 runtime ActionBank schema。 |
| `src/runtime_ontology.py` | 仅根据已观察工具结果重建认证、对象状态、成功调用、mutation 历史和 action-bound confirmation。 |
| `src/argument_grounder.py` | 根据 ActionBank 的 target binding 和 parameter role，将 arguments 绑定到已观察本体对象。 |
| `src/ontology_repair.py` | 将 verifier violation 转换为缺失谓词，并通过 ActionBank predicate provider 选择 enabling action。 |
| `src/verifier.py` | 检查本地本体 precondition 和 policy constraint。 |
| `src/simulator.py` | 用于本体诊断的 retail tool-effect simulator；不参与官方 tau2 scoring。 |
| `src/state_manager.py` | 本体诊断使用的 dialogue/action state 表示。 |
| `src/data_loader.py` | 加载本地 retail tau-bench 数据，仅用于本体诊断和本地检查。 |

### Smoke Test

这些脚本只用于快速发现代码级回归，不能单独作为论文实验。

| 文件 | 用途 |
| --- | --- |
| `smoke_tau2_admissibility.py` | 检查 ontology gate 的拒绝逻辑、repair hints 和 deterministic repair。 |
| `smoke_tau2_response_guard.py` | 检查 tau2 agent 输出相关的 response handling。 |
| `smoke_import_tau2_mechanism.py` | 检查官方结果导入和 ontology-gate trace 抽取。 |
| `smoke_report_official_results.py` | 使用合成导入结果检查 report 生成逻辑。 |
| `smoke_task_cluster_stats.py` | 检查 task-cluster 显著性分析逻辑。 |
| `smoke_action_ir_projection.py` | 检查提交的 ActionBank 是否确实是 canonical Action IR 的确定性投影。 |
| `smoke_epistemic_action_semantics.py` | 检查 read/lookup action 使用 weak grounding，而 mutating action 保持 strong grounding。 |
| `smoke_method_alignment.py` | 检查角色投影、结构化 evidence binding、跨订单反例和 predicate-driven repair。 |
| `smoke_variant_isolation.py` | 检查 baseline/ablation 的 ActionBank、runtime state、gate 和 repair 严格隔离。 |

## 数据与 Action Schema

| 路径 | 含义 |
| --- | --- |
| `data/action_ir/retail_action_ir.json` | Canonical ontology-grounded Action IR。包含 actor、target binding、结构化参数、preconditions、effects、constraints、state transitions、control-flow hints、evidence、grounding 和 runtime projection metadata。 |
| `data/action_bank/retail_action_bank.json` | 从 `data/action_ir/retail_action_ir.json` 生成的 runtime ActionBank projection。用于 agent prompt、admissibility gate 和本体诊断。 |
| `data/raw/retail/` | 本地 tau-bench retail 数据。只用于 ontology diagnostics 和 local checks；官方 tau2 runner 使用其自身安装路径下的数据。 |

官方 tau2 agent 不允许读取 `data/raw/retail/db.json` 或任何完整环境数据库。正式实验中的对象 grounding 只能使用：

- 当前对话；
- trajectory 中已经观察到的官方工具输出；
- ActionBank / ontology schema。

这个限制用于避免 hidden database leakage。

正式 agent 的 Method 执行路径为：

```text
Canonical Action IR
  -> ActionBank(target binding, parameter roles, predicates, providers)
  -> RuntimeOntologyState(observed evidence only)
  -> Type-aware admissibility
  -> Missing predicate
  -> Ontology provider action
  -> Repaired candidate
```

订单状态、认证、重复调用和确认均由结构化状态判定。对话文本只用于提取用户明确提供的参数，
不能代替跨对象状态绑定。确认记录绑定到具体 action 和目标参数，不能授权其他订单或其他
mutation。

正式实验 variant：

| `agent-kind` | ActionBank prompt | Runtime state prompt | Gate | Full conditions | Repair |
| --- | ---: | ---: | ---: | ---: | ---: |
| `schema` | 否 | 否 | 否 | 否 | 否 |
| `ontology_prompt` | 是 | 否 | 否 | 否 | 否 |
| `state_only` | 是 | 是 | 否 | 否 | 否 |
| `typed_admissibility` | 是 | 是 | 是 | 是 | 否 |
| `ontology_full` / `ontology` | 是 | 是 | 是 | 是 | 是 |

`ontology_lite` 仅作为旧的 structural-gate 调试 variant 保留，不用于论文主表。

当前实现聚焦 tau2 retail。Airline 相关 prototype 文件已经移除，因为官方 agent 链路尚未实现独立的 airline ActionBank/gate。

## 推荐执行流程

先运行 smoke checks：

```bash
python experiments/paper3_agent_planning/smoke_tau2_admissibility.py
python experiments/paper3_agent_planning/smoke_import_tau2_mechanism.py
python experiments/paper3_agent_planning/smoke_report_official_results.py
python experiments/paper3_agent_planning/smoke_task_cluster_stats.py
python experiments/paper3_agent_planning/smoke_action_ir_projection.py
```

编辑 canonical Action IR 后，重新生成 runtime ActionBank：

```bash
python experiments/paper3_agent_planning/compile_action_ir_to_action_bank.py
```

运行本体语义诊断：

```bash
python experiments/paper3_agent_planning/run_ontology_benchmarks.py \
  --split test \
  --output experiments/paper3_agent_planning/results/ontology_benchmark_test.json
```

运行官方 paired tau2 evaluation：

```bash
python experiments/paper3_agent_planning/run_official_tau2_pair.py \
  --domain retail \
  --agent-model GLM-5.1 \
  --agent-base-url https://open.bigmodel.cn/api/coding/paas/v4 \
  --api-key "$AGENT_API_KEY" \
  --user-llm openai/GLM-5.1 \
  --task-split-name base \
  --num-trials 1 \
  --max-concurrency 1 \
  --combined-output experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --report-output experiments/paper3_agent_planning/results_official_tau2/official_report.md
```

修改 method 后，不要反复复用手工调试的 10 个任务。应先生成 held-out 命令：

```bash
python experiments/paper3_agent_planning/make_heldout_tau2_commands.py \
  --split base \
  --num-tasks 40 \
  --seed 20260616
```

然后分别运行脚本打印出的 schema baseline 和 ontology full 命令。默认排除的调试任务是：

```text
0 1 2 3 4 5 6 8 9 11
```

这些任务已经用于 method debugging，不应作为主要论文结果。

如果 baseline 和 ontology agent 是手动分别运行的，需要显式导入官方 tau2 输出：

```bash
python experiments/paper3_agent_planning/import_tau2_results.py \
  --left-path /path/to/schema_run \
  --left-name Schema-Only \
  --right-path /path/to/ontology_run \
  --right-name Ours \
  --domain retail \
  --task-split-name base \
  --output experiments/paper3_agent_planning/results_official_tau2/combined.json
```

分析与校验：

```bash
python experiments/paper3_agent_planning/analyze_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json

python experiments/paper3_agent_planning/validate_official_results.py \
  experiments/paper3_agent_planning/results_official_tau2/combined.json \
  --left Schema-Only \
  --right Ours \
  --min-unique-tasks 40 \
  --min-paired-simulations 40 \
  --alpha 0.05 \
  --require-gate-trace
```

## 什么可以作为论文证据

有效证据：

- 通过 `import_tau2_results.py` 导入的官方 tau2 reward。
- 相同 task/trial key 上的 paired comparison。
- 正向 task-success delta，加上统计显著性。
- task-cluster significance，因为 repeated trials 不能当作独立任务样本。
- 如果论文声称机制有效，需要 proposed planner 的 ontology-gate traces。
- `run_ontology_benchmarks.py` 生成的确定性本体语义诊断结果。
- `smoke_action_ir_projection.py` 通过，证明 Paper3 使用的是 Paper2-compatible Action IR 的 runtime projection。

无效证据：

- 旧 local runner 的 success number。
- 单独的 smoke test。
- 临时 Kimi 结果目录。
- task/trial 覆盖不完整的 partial tau2 run。
- 只在手工调试任务集合上的结果。
- 官方 tau2 agent 读取完整本地 retail 数据库，而不是只使用已观察到的工具输出的结果。
- `schema` baseline 暗中使用 ontology normalization 或 gate logic 的运行结果。
- 手工修改过、已经不再匹配 canonical Action IR 的 ActionBank。

## 当前范围与限制

- 当前实现面向 tau2 retail。
- Ontology gate 是保守机制；它可以拒绝不安全或证据不足的 action candidate，但不能保证全局最优规划。
- 主结论必须等官方 paired results 通过 `validate_official_results.py` 后才成立。
- 生成的结果文件默认不进入 Git。写论文表格时，需要保留原始官方 tau2 输出路径以便审计。
