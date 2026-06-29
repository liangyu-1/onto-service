# 导师意见后的三篇论文重构方案

## 1. 总体研究主线

新的大论文不再把三篇论文都描述为 Action IR 的不同应用，而是研究本体从
静态对象语义走向可执行能力的三个连续层次：

```text
异构系统资产
  -> Paper 1：自动构建本体 Atomic Function Layer
  -> Paper 2：从程序文档生成 Ontology Workflow Skill
  -> Paper 3：噪声与攻击下的鲁棒、可控执行
```

三篇论文分别回答：

1. 在本体构建过程中，如何不依赖专家逐项审核，自动发现并验证原子能力？
2. 如何利用对象本体和原子 Function，将 SOP 转换为本体中的复合 Workflow？
3. 当 Workflow 面对环境噪声或恶意攻击时，如何维持任务效用与控制边界？

Palantir 只作为产业参照。论文研究对象必须是公开、平台无关、可复现的
Function Layer、Workflow Skill 和 Execution Control Envelope。

## 2. Paper 1：无人干预的本体 Function Layer 自动构建

### 2.1 论文定位

Paper 1 不是“将一份 API 文档转换成一个 JSON Tool Schema”，而是研究：

> 在自动构建 operational ontology 的场景下，如何从 Schema、API 文档、
> OpenAPI、调用样例和执行轨迹中，无需领域专家参与候选确认，自动构建与
> 对象层一致、可执行、可验证的 Atomic Function Layer？

这里的“无人干预”指方法运行阶段不需要专家审核每个 Function。实验仍然需要
人工金标，否则无法客观评价自动构建质量。

### 2.2 输入

- 数据库 Schema、对象元数据和数据类型；
- API 文档、OpenAPI、SDK 签名和请求响应样例；
- 调用日志、测试轨迹和错误码；
- 自动生成或已有的 Object Layer 草案。

Object Layer 可以来自元数据映射、已有系统模型或自动本体构建方法。Paper 1
不要求人工完成对象层，但需要研究对象层存在错误时 Function Layer 的鲁棒性。

### 2.3 输出

```text
OntologyFunction {
  function_id,
  bound_object_types,
  operation_kind,
  inputs[{type, semantic_role, ontology_property}],
  outputs[{type, ontology_property}],
  preconditions,
  effects,
  endpoint_binding,
  error_contract,
  evidence_set,
  confidence,
  unresolved_fields
}
```

所有 Function 直接写入 Function Layer，并与 Object Type、Property、Relation
和 State Predicate 建立引用关系。

### 2.4 核心难点

1. **自动语义对齐**：API 参数名与本体属性名不一致；
2. **对象归属识别**：判断函数读取、创建、修改或删除哪个本体对象；
3. **隐式状态语义恢复**：从文档、响应和轨迹推断前置状态与效果；
4. **证据冲突处理**：OpenAPI、文档、样例和运行轨迹可能不一致；
5. **自动质量控制**：没有专家裁决时，如何过滤错误 Function；
6. **对象层误差传播**：错误或不完整的 Object Layer 会污染 Function Layer。

### 2.5 方法主张

建议方法定义为 **evidence-triangulated autonomous construction**：

1. 多源发现 Function 候选；
2. 对象、属性和状态候选联合对齐；
3. 通过类型约束、图约束和输入输出闭包做静态验证；
4. 自动生成调用测试并进行 sandbox/trace replay；
5. 使用多证据一致性和执行结果自动校准 confidence；
6. 对冲突字段局部修复，无法支持的字段自动 abstain；
7. 按自动发布阈值生成 Function Layer，不进入人工审核流程。

这比“多 Agent 投票”更容易自圆其说。多个模型可以作为实现手段，但论文贡献
必须是自动验证与发布机制，而不是角色数量。

### 2.6 可证伪假设

- H1：多源证据三角验证比单一 API 文档抽取提高 Function semantic accuracy；
- H2：执行验证能显著降低不可调用或效果错误的 Function；
- H3：自动 abstention 能在给定 coverage 下提高 Function Layer precision；
- H4：对象层扰动下，联合对齐比顺序式“先对象、后 Function”具有更低误差传播；
- H5：自动构建的 Function Layer 能达到接近人工 Function Layer 的下游
  Workflow 可组合性。

### 2.7 关键指标

- Function discovery precision/recall；
- object/function binding accuracy；
- parameter-role 和 property-linking F1；
- precondition/effect F1；
- executable invocation rate；
- full-function exact match；
- autonomous accepted coverage；
- risk-coverage curve；
- 每个已发布 Function 的错误率；
- 下游 Workflow executable rate；
- Object Layer 噪声下的性能退化斜率。

## 3. Paper 2：本体约束的 Workflow Skill 自动生成

### 3.1 论文定位

Paper 2 不是一般流程图抽取。它研究：

> 给定 Object Layer、Paper 1 生成的 Function Layer，以及用户说明书、SOP
> 或标准操作文档，如何自动生成一个以本体对象状态为语义基础、以本体
> Function 为原子节点的可执行 Workflow Skill？

### 3.2 本体具体体现在哪里

本体不是 Prompt 背景，而是 Workflow 的类型系统和状态语义：

| Workflow 组成 | 本体作用 |
|---|---|
| Node | 必须引用 Function Layer 中的 Function ID |
| Variable | 必须属于 Object Type 或 Property datatype |
| Input/output binding | 通过 ontology property 和 relation path 连接 |
| Condition | 表达为对象属性或关系上的 State Predicate |
| State transition | 由 Function effect 更新对象状态 |
| Edge | 由 effect-precondition compatibility 约束 |
| Invariant | 来源于对象约束、policy 和 cardinality |
| Exception | 表示无法满足本体谓词后的替代分支 |
| Skill output | 仍是本体对象、关系或状态变化 |

因此输出不是普通 DAG，而是一个 **ontology-grounded state-transition
workflow**。

### 3.3 输出

```text
OntologyWorkflowSkill {
  skill_id,
  goal_predicate,
  typed_inputs,
  typed_outputs,
  object_variables,
  nodes[OntologyFunctionCall | UserInteraction | Decision | End],
  control_edges,
  dataflow_edges,
  state_predicates,
  invariants,
  exception_paths,
  evidence,
  unresolved_regions
}
```

### 3.4 核心难点

1. 文档步骤到 Function Layer 的多对一、一对多对齐；
2. 跨步骤对象身份和变量生命周期保持；
3. 基于本体 effect/precondition 恢复缺失依赖；
4. 条件、并行、循环和异常的语义作用域；
5. Function 缺失与文档省略的区分；
6. 图结构正确但本体状态迁移不可执行的问题。

### 3.5 方法主张

1. 结构感知文档解析；
2. 程序单元识别；
3. Function 和 Object 联合候选检索；
4. 本体约束的节点、数据流和控制流联合生成；
5. effect-precondition compatibility 推理；
6. 类型、状态、可达性和副作用静态验证；
7. sandbox 中的执行验证和局部修复。

### 3.6 必须增加的消融

- No Object Ontology；
- No Function Layer；
- No State Predicate；
- No Effect-Precondition Reasoning；
- No Typed Dataflow；
- No Execution Validation。

只有这些消融能够证明论文二不是换了名称的 PAGED 或 BPMN 生成。

### 3.7 指标

- node/edge F1 和 graph edit distance；
- Function grounding accuracy；
- Object binding accuracy；
- typed dataflow F1；
- state predicate F1；
- effect-precondition compatibility accuracy；
- executable workflow rate；
- ontology violation rate；
- hallucinated Function rate；
- downstream task success。

## 4. Paper 3：噪声与攻击下的鲁棒、可控 Workflow 执行

### 4.1 论文定位

> 在工具输出、用户输入、工具描述、运行状态和 Workflow 本身受到随机噪声或
> 恶意攻击时，如何利用 Ontology Workflow 的对象、状态、动作和边界约束，
> 提高 Agent 的鲁棒性与可控性，并抬高经验最坏情况下的性能下界？

### 4.2 威胁模型

#### 随机噪声

- timeout、rate limit、partial response；
- 字段缺失、类型变化和 Schema drift；
- 状态观测过期、冲突或缺失；
- 相似工具增加和无关工具干扰；
- 用户表述改写和任务信息不完整。

#### 对抗攻击

- 工具输出中的 indirect prompt injection；
- 恶意工具描述和 ToolHijacking；
- 用户请求中的越权、跳步和目标漂移；
- memory/state poisoning；
- 多轮渐进式 objective drifting；
- 伪造错误信息诱导 transfer 或危险补偿。

### 4.3 方法：Ontology-Compiled Execution Envelope

1. 将 Workflow Skill 编译为允许控制状态、动作集合、对象绑定、状态迁移、
   invariant 和 side-effect budget；
2. 将用户文本、工具文本和工具元数据区分为 trusted control data 与
   untrusted content；
3. 只允许结构化、通过类型和来源验证的字段更新 ontology runtime state；
4. 对当前状态维护 uncertainty set，而不是相信单一观测；
5. 对不可逆动作采用 worst-case admissibility：只有在不确定集合内所有可行
   状态均满足约束时才执行；
6. 对查询类动作允许受控探索，以避免过度保守导致任务停滞；
7. 将恢复限制为 Workflow 允许的 observation、retry、rebind、branch、
   compensate 和 escalate；
8. 使用自适应攻击生成器持续搜索控制包络的薄弱边界。

### 4.4 不应声称的内容

- 不声称在有限 benchmark 上获得形式化 worst-case guarantee；
- 不声称检测所有 Prompt Injection；
- 不把自然语言理由或解释质量作为核心指标；
- 不把“拦截次数更多”直接视为鲁棒性更高。

论文报告的是 **empirical worst-case lower bound**，即在预定义攻击族、攻击
预算和置信水平下观测到的性能下界。

### 4.5 可证伪假设

- H1：Ontology Execution Envelope 在相同 clean utility 下具有更低 ASR；
- H2：在相同 constraint violation rate 下，受控探索比统一强阻断具有更高
  Utility under Attack；
- H3：对象、状态和 effect 约束能抵抗仅靠文本过滤无法阻止的工具劫持；
- H4：自适应攻击训练/搜索能发现静态攻击集未覆盖的薄弱边界；
- H5：随着攻击预算增加，完整方法的性能退化斜率和 worst-group loss 更低；
- H6：方法在未见领域只替换 ontology/workflow，不修改控制代码时仍保持收益。

### 4.6 核心量化指标

- Clean Task Success；
- Utility under Attack；
- Attack Success Rate；
- Workflow Conformance Rate；
- Constraint Violation Rate；
- Unsafe Side-Effect Rate；
- Over-blocking Rate；
- Recovery Success Rate；
- Net Resilient Performance；
- Robustness Degradation Slope；
- Worst-Attack Success；
- Worst-Group Success；
- 95% lower confidence bound of robust success；
- Robust Radius：满足 `ASR <= τ` 且 `utility >= α` 的最大攻击预算；
- token、latency 和 tool-call overhead。

### 4.7 实验协议

数据集和环境：

- AgentDojo：间接 Prompt Injection；
- InjecAgent：工具集成 Agent 攻击；
- Agent Security Bench：多类攻击与 NRP；
- tau-bench：有状态业务工作流；
- SOP-Bench：复杂程序执行；
- ReliabilityBench 风格的随机故障注入；
- 自建 ontology-workflow attack set。

基线：

- ReAct；
- Workflow Prompt；
- Prompt Injection detector/filter；
- AgentSpec；
- Agent-C；
- 仅文本隔离；
- 仅 Action local verifier；
- 完整 Ontology Execution Envelope。

攻击必须同时包含固定攻击和 adaptive attack。只在静态攻击集上有效不能支持
鲁棒性主张。

## 5. 三篇论文的依赖与隔离

```text
Paper 1:
System Artifacts -> Autonomous Ontology Function Layer

Paper 2:
Object Layer + Function Layer + Procedure Documents
  -> Ontology Workflow Skill

Paper 3:
Ontology Workflow Skill + Untrusted Runtime Environment
  -> Robust and Controlled Execution
```

实验必须隔离：

- Paper 1 独立测 Function Layer 自动构建；
- Paper 2 主实验使用金标 Function Layer，避免 Paper 1 误差污染结论；
- Paper 3 主实验使用金标 Workflow，避免 Paper 2 误差污染鲁棒性结论；
- 最后再做级联实验，测自动构建误差如何逐层传播。

## 6. 当前最关键的研究风险

1. Paper 1 若默认人工已有完整对象本体，自动构建故事仍然不完整；
2. Paper 1 若只测字段抽取，会被 ToolFactory 和 API KG 工作覆盖；
3. Paper 2 若不报告 ontology ablation，无法证明本体的必要性；
4. Paper 3 若只测普通 timeout 或静态 Prompt Injection，鲁棒性证据不足；
5. “worst case”必须限定攻击空间和预算，否则属于不可验证的夸大表述；
6. 无人工介入是方法约束，不代表可以没有人工金标和独立评估。
