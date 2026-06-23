# 面向本体动作层的研究：协作构建、文档抽取与智能体执行

## 大论文拟定大纲

### 第 1 章 绪论

- 操作型本体为什么需要 Action Layer
- 文档知识、结构化元数据和 Agent 运行时之间的表示断裂
- 研究问题、总体框架和主要贡献

### 第 2 章 理论基础与统一 Action IR

- 操作型本体与动作语义
- Action IR 的核心字段、可选字段和形式化约束
- Action IR、Action Ontology、Procedure Graph 和 ActionBank 的关系
- 证据、版本、可信度与协作治理模型

### 第 3 章 协作式动作本体生成与演化

对应小论文一：

**Collaborative Action Ontogenesis: A Multi-Agent Human-in-the-Loop Framework for Building and Evolving Ontology Action Layers**

- 多源证据接入：数据库 Schema、程序文档、API、执行日志和专家知识
- 多 Agent 分工：发现、抽取、对齐、验证、批判和仲裁
- Action IR Patch 的提案、验证、共识、发布和演化
- 人类专家以 micro-task 方式进行确认、反驳和裁决

### 第 4 章 非结构化程序文档中的本体动作抽取

对应小论文二：

**Ontology-Grounded Action Extraction from Unstructured Procedural Documents**

- 结构感知解析
- LLM Action IR 抽取
- 本体 grounding 与程序图构建
- 证据约束和结构化验证

### 第 5 章 面向智能体的本体动作理解与约束规划

对应小论文三：

**Ontology-Grounded Action Semantics for Policy-Constrained LLM Agents**

- Action IR 到 ActionBank 的运行时投影
- Runtime Ontology State
- Type-aware admissibility
- Ontology-guided repair 与失败分析

### 第 6 章 统一系统、跨域实验与讨论

- 三项方法的端到端集成
- Retail、Airline、Maintenance / Industrial SOP 跨域实验
- 本体质量、协作成本、执行收益和系统开销
- 局限、适用边界与未来工作

## 一、研究对象与总体问题

传统本体主要表示对象、属性、关系和规则，擅长回答“世界中有什么”。LLM Agent 和操作型系统还需要回答：

- 当前能执行哪些动作？
- 动作作用于哪个对象？
- 参数对应什么语义角色？
- 当前对象状态是否满足前置条件？
- 执行后状态如何变化？
- 哪条策略、SOP 或证据支持该动作？

因此研究对象不是泛化的知识图谱，而是操作型本体中的 **Action Layer**。

总体目标：

> 构建一个能够协作生成、从文档持续扩充、并可供 Agent 约束执行的本体动作层。

## 二、Action IR 是什么

### 2.1 定义

Action IR（Action Intermediate Representation）是数据与文档证据、领域本体、协作治理系统和 Agent 运行时之间的规范化中间表示。

它解决的是表示断裂：

`自然语言步骤 ≠ 本体动作节点 ≠ API Schema ≠ Agent 运行状态`

统一表示：

```text
ActionIR = <
  identity,
  actor,
  target,
  parameters and role bindings,
  preconditions,
  effects,
  constraints,
  state transitions,
  control flow,
  ontology grounding,
  evidence and provenance,
  runtime projection
>
```

### 2.2 字段分层

- 身份层：`id`、`name`、`type`、`action_kind`
- 对象层：`actor`、`target.object_type`
- 参数层：参数名、类型、必选性和语义角色
- 状态层：`preconditions`、`effects`、`state_transitions`
- 约束层：权限、确认、执行历史、引用完整性
- 流程层：前驱动作、禁止后续、条件和异常边
- 对齐层：ontology action/type/property IDs
- 证据层：来源文档、证据 span、offset、置信度
- 运行层：tool name、grounding mode、是否可执行

### 2.3 具体例子

以 `return_delivered_order_items` 为例：

- Action type：`OrderReturn`
- Actor：`CustomerServiceAgent`
- Target：`Order`
- Parameters：
  - `order_id → target_identifier`
  - `item_ids → source_items`
  - `payment_method_id → payment_method`
- Precondition：`order.status == delivered`
- Constraints：
  - 用户已认证
  - 用户已确认
  - 同一订单尚未执行最终动作
  - item 和 payment 引用有效
- Effects：
  - `order.status = return requested`
  - `order.returned_items = item_ids`
- Evidence：来自 retail policy 的原始文本
- Runtime：投影为同名工具调用

这里 Action IR 比 API Schema 多表达了对象类型、参数角色、状态、约束、效果和证据。

### 2.4 Action IR 如何贯穿三篇论文

- Paper 2：从文档和本体生成 Action IR
- Paper 1：将 Action IR 转换为 Action Index Document，建立混合索引
- Paper 3：将 Action IR 确定性编译为 ActionBank，供 Agent 运行时使用

Action IR 是唯一 canonical representation。Action Index Document 和 ActionBank 都是面向特定任务的投影，不应被手工独立维护。

## 三、数据集如何使用

### 3.1 当前四个 processed JSONL 的真实状态

当前 `dataset/idea2_sop_action_benchmark/processed/*.jsonl` 只保留了文本和 metadata，四个文件中的 `annotations` 都是空值。因此：

- 可以用于无监督语料、LLM few-shot 文本池或重新转换的输入。
- 不能直接用于监督训练和 benchmark。
- 必须从 raw 数据重新解析官方 annotation。

### 3.2 已下载数据的可用性

| 数据集 | 实际可用标注 | 论文角色 | 限制 |
|---|---|---|---|
| MyFixit | 只有 Mac Laptop 子集的 1,497 manuals / 36,659 steps 有工具、部件和 removal verb 人标 | Paper 2 主数据：action、target、tool；Paper 1 的 document proposal 来源 | 其余 14 类主要是无标注语料；无 flow、state 和 ontology ID |
| MSPT | 230 篇 BRAT 标注，含 Operation、Material 和 argument relations，提供官方 split 文件 | Paper 2 主数据：action、material、parameter/argument | 科学合成语域；控制流和 ontology grounding 不完整 |
| PET | 45 篇专家标注的 activity、actor、gateway、condition 和 relations | Paper 2 控制流测试集 | 只有 test set，不适合训练；规模小且偏 BPM |
| OMIn | 维护事故文本，gold 主要覆盖 NER、coreference 和 NEL | Paper 2 辅助 target grounding；Paper 1 维护域证据源 | 不是 procedure；不能评估 Action IR 或流程 |
| ProPara | train/dev/test 过程段落及实体状态变化 | Paper 2 辅助 precondition/effect/state-transition 测试 | 非工业；无 action ontology grounding |
| BioProcess | 226 train / 70 test 文档的事件和 argument BRAT 标注 | Paper 2 辅助 action/argument extraction | 生物领域；无操作约束和工具执行 |
| ABCD | 8,034/1,004/1,004 对话，含 guidelines、action labels 和 action ontology | Paper 2 的 policy-to-action 辅助数据；Paper 3 外部 action-selection 验证 | 对话而非 SOP；动作语义与 tau2 不同 |
| Text-mined Synthesis | 31,782 solid-state + 9,518 sol-gel 银标记录 | Paper 2 预训练和 weak supervision | 自动抽取银标，不能作为最终 gold |
| tau2 Retail/Airline | 任务、policy、tools、数据库状态和官方 evaluator | Paper 3 主 benchmark；Paper 1 的执行反馈与 ontology evolution 场景 | 不提供文档级 Action IR 金标 |

### 3.3 尚缺且必须补充的数据

- PAGED：补充大规模 sequential/non-sequential action、constraint 和流程结构评估。
- 人工 Full Action IR Test Set：从维修手册、工业 SOP 或业务策略中完整标注 actor、target、parameters、preconditions、effects、constraints、flow、ontology IDs 和 evidence。
- Paper 1 Collaboration Benchmark：从 metadata、documents、API 和 execution traces 构造候选 patch、冲突意见、验证结果、专家决策和 schema evolution 事件。

没有一个公开数据集提供完整 Action IR，更没有公开数据集直接评估多 Agent 协作构建。因此两项人工构建资产不是可选增强，而是论文成立的必要实验基础。

### 3.4 训练与验证方式

1. 把不同数据集转换为统一文档记录格式。
2. 根据原始标注生成字段级 partial labels 和 mask。
3. 训练时只对数据集确实标注的字段计算 loss。
4. 使用已有本体或由训练集构建的 seed ontology 提供 grounding candidates。
5. 构建小规模人工审核的 full Action IR test set，完整标注状态、效果、约束、ontology IDs 和 evidence。
6. 由 Action IR 派生 Paper 1 的协作提案记录和 Paper 3 的 ActionBank。

### 3.5 数据划分原则

- 按 document / manual / process 划分，避免同一文档步骤泄漏到不同 split。
- 公开数据用于可复现字段级评估。
- 人工完整集用于 Action IR exact match、约束一致性和端到端验证。
- 跨域测试用于验证 schema 泛化，而不是要求同一模型零成本适配所有领域本体。

## 四、三篇论文

## Paper 1：Collaborative Action Ontogenesis

### 研究目标

现有本体构建方案存在三类问题：

- 全自动抽取覆盖高，但业务语义和约束不可靠。
- 全人工构建准确，但专家成本高且难以持续维护。
- 一次性构建无法响应 Schema、SOP、API 和业务策略变化。

因此，本研究把本体构建定义为持续循环，而不是一次性生成：

`Observe → Propose → Validate → Critique → Consensus → Commit → Monitor`

### 多 Agent 角色

- Schema Discovery Agent：从数据库 Schema、API 和元数据发现对象、字段和候选动作。
- Document Extraction Agent：从 SOP、手册和策略文档抽取 Action IR 候选。
- Grounding Agent：把动作、对象、参数和状态映射到现有本体。
- Validation Agent：使用类型约束、数据采样、工具测试和执行日志验证候选。
- Critic Agent：搜索冲突、重复、缺失前置条件和证据不足。
- Consensus Agent：聚合多 Agent 与多用户意见，决定接受、拒绝或待审。
- Human Owner：处理高风险、低置信度和争议提案。

### 核心数据结构

Action IR 只存储动作语义。协作治理信息放在独立的 Proposal Envelope 中：

```text
ActionIRPatch {
  base_version,
  semantic_delta,
  evidence,
  proposer,
  validators,
  confidence,
  votes,
  dispute_status,
  decision,
  audit_trail
}
```

这种分离避免把投票、贡献者和审核状态混入动作本体语义。

### 主要创新

- 用多源、多 Agent 证据循环持续构建 Action Layer。
- 用可验证的 Action IR Patch 替代整库自由生成。
- 将专家工作拆成确认、反驳、补充和争议裁决等 micro-tasks。
- 支持 provenance、可信度升级、冲突检测、软废弃和版本演化。

### 初步实验设想

- 实验任务：
  - Cold start：从数据库 Schema、文档和 API 构建动作层。
  - Noisy proposal：注入错误类型、错误参数角色、缺失前置条件和伪造证据。
  - Conflict：模拟不同 Agent 或用户提出相互冲突的 Action IR Patch。
  - Evolution：修改 Schema、SOP 或策略，测试重开验证与软废弃。
- Baselines：
  - Single-LLM generation
  - Sequential automatic pipeline
  - Human-only construction
  - Simple majority vote
- 指标：
  - Action IR field accuracy / exact accuracy
  - 覆盖率与 accepted actions 数量
  - 每个 accepted action 所需专家时间
  - Time-to-consensus
  - Conflict detection F1
  - Schema evolution recovery accuracy
- Ablations：No Critic、No Validator、No Human、No Provenance、No Revalidation。

## Paper 2：Ontology-Grounded Action Extraction

输入：

`Procedural Document + Existing Ontology`

输出：

`Grounded Action IR + Procedure Graph`

方法：

1. 结构感知文档解析
2. 程序单元识别
3. LLM 生成受控 Action IR
4. 混合检索获得本体候选
5. 类型、角色和状态约束 grounding
6. 程序图构建、证据和 schema 验证

主要实验：

- 字段级：Action F1、Actor/Target F1、Parameter F1
- 对齐级：Ontology Grounding Accuracy
- 流程级：Control-flow Edge F1
- 证据级：Evidence Span F1
- 结构级：Validation Pass Rate、Full Action IR Exact Match
- 下游级：对 Paper 1 提案质量和 Paper 3 执行的影响

## Paper 3：Ontology-Grounded Agent Action Planning

输入：

`User Goal + Dialogue/Tool History + ActionBank`

运行过程：

1. 从 Action IR 编译 ActionBank。
2. 从对话和已观察工具结果维护 Runtime Ontology State。
3. LLM 提出候选动作。
4. Type-aware admissibility：
   - Epistemic action 使用弱 grounding，用于获取状态。
   - Mutating action 使用强 grounding，要求对象、状态、角色和确认。
5. 不满足条件时返回结构化 ontology violation。
6. Ontology-guided repair 选择认证、查询、确认或参数修复动作。

### 具体示例：取消订单

用户目标：

> “请取消订单 #123，因为我下错单了。”

初始状态中只有用户话语，没有认证状态，也不知道订单状态。执行过程如下：

1. LLM 不能直接执行 `cancel_pending_order`，因为目标订单尚未 grounded，状态未知，也没有确认。
2. Agent 先执行 epistemic action `find_user_id_by_email` 完成认证。
3. Agent 执行 epistemic action `get_order_details(order_id=#123)`。
4. 工具结果进入 Runtime Ontology State：
   - `order #123` 是已观察的 `Order` 个体；
   - `order.status = pending`；
   - `reason = ordered by mistake` 属于允许值。
5. Agent 执行 `ask_for_confirmation`，并将确认绑定到：
   `cancel_pending_order(order_id=#123, reason=ordered by mistake)`。
6. 用户回答 “Yes”。Runtime Ontology State 只为该动作签名设置 `user_confirmed = true`。
7. LLM 再次提出 `cancel_pending_order`。强 grounding 检查通过：
   - 用户已认证；
   - 目标订单已观察；
   - 订单状态是 pending；
   - reason 合法；
   - confirmation 与动作及参数一致。
8. 工具执行后，预期效果为：
   - `order.status: pending → cancelled`；
   - 触发退款。

反事实：

- 如果步骤 4 返回 `order.status = delivered`，Verifier 应返回 `PreconditionViolation`，不能执行取消。
- Repair 不能简单重试取消，而应根据用户目标和 ActionBank 选择退货、转人工或重新询问。

该例子体现 Paper 3 的核心：本体不是被动提示文本，而是决定动作是否 admissible、缺少什么状态以及应如何修复。

初步结果：

- 341 个严格配对样本，114 个任务，3 个完整 trials
- Schema-Only：44.9%
- Typed + Repair：55.7%
- paired McNemar `p = 0.0029`
- task-level sign test `p = 0.109`，未显著
- Transfer calls：323 → 62
- 平均延迟：190.6s → 260.3s

限制：

- 完整 8-trial 实验被模型配额中断。
- 发现 confirmation binding 缺陷。
- 修复版尚未完成端到端重跑。
- 当前只能声称 simulation-level 初步证据，不能声称通用 planning 已解决。

## 五、三篇论文的关系与边界

- Paper 1 回答：动作本体如何由多 Agent 和多人持续构建、验证和演化？
- Paper 2 回答：非结构化程序文档如何产生可验证的 Action IR 候选？
- Paper 3 回答：已经发布的 Action IR 如何在运行时约束 Agent 动作？

边界：

- Paper 1 是治理和协作框架，不把所有抽取算法都声明为自身创新。
- Paper 2 是 Paper 1 中 Document Extraction Agent 的一种关键实现，但可独立评估。
- Paper 3 不负责构建本体，假设已存在经过发布和版本管理的 Action IR。
- 动作检索可以作为 Paper 1 的候选发现组件或 Paper 3 的大规模动作选择组件，但暂不作为独立论文主线。

## 六、建议推进顺序

1. 完成 Paper 3 修复版配额完整重跑和 component ablation。
2. 固定 Action IR core schema、Proposal Envelope 和人工完整测试集。
3. 完成 Paper 2 的字段级和结构级 benchmark。
4. 实现 Paper 1 的多 Agent proposal-validation-consensus loop。
5. 完成跨源和跨域评估：metadata + document + execution trace；retail → airline → maintenance。

## 七、希望导师重点判断

1. Action Layer 是否足以作为大论文的统一研究对象？
2. Action IR 的字段范围是否过宽，是否需要分 core / optional schema？
3. Paper 1 的多 Agent 协作框架是否具备独立论文价值，还是更适合作为大论文系统章节？
4. Paper 2 是否应优先聚焦维修手册或业务流程中的一个领域？
5. Paper 3 当前证据是否值得继续投入完整重跑和消融？

## 八、导师可能追问与回答口径

### 问题 1：三篇论文是否只是共享一个 Action IR 名称？

回答：不是。Paper 1 研究协作治理机制，Paper 2 研究文档抽取算法，Paper 3 研究运行时动作语义。三篇论文共享 canonical representation，但分别有独立的输入、机制、baseline 和评价指标。

### 问题 2：Paper 1 已经有 Document Extraction Agent，为什么还需要 Paper 2？

回答：Paper 1 把抽取器视为可替换的 proposal producer，创新在 proposal-validation-consensus-evolution loop；Paper 2 研究如何从复杂程序文档准确生成 Action IR Patch。若 Paper 2 不能在独立抽取 benchmark 上显著优于 LLM-only，它就不应作为独立论文。

### 问题 3：多 Agent 是否只是把一个 pipeline 拆成多个 prompt？

回答：如果只是串行调用多个 LLM，确实没有创新。本文必须证明角色异质性、独立证据、critic、冲突检测、共识和持续 revalidation 带来可测收益，并通过 No Critic、No Validator、No Human、No Provenance 和 No Revalidation 消融验证。

### 问题 4：公开数据集不能覆盖完整 Action IR，实验是否可信？

回答：公开数据集只评估各字段能力；完整语义由人工 Full Action IR Test Set 评估。论文会明确区分 partial-label public benchmark 与 full-label expert benchmark，不把弱标注包装成完整金标。

### 问题 5：Paper 3 是不是普通规则 verifier？

回答：不是单独规则列表。规则来自 Action IR 中的对象类型、参数角色、状态前置条件、效果和策略约束；同一表示还用于 runtime state、repair 和解释。关键机制是 epistemic weak grounding 与 mutating strong grounding 的类型感知差异。

### 问题 6：目前最薄弱的地方是什么？

回答：Paper 1 还处于框架设计阶段，没有 collaboration benchmark 和用户实验；Paper 2 的 processed converter 丢失了 annotation；Paper 3 的完整重跑仍受配额和 confirmation binding 修复验证影响。

## 九、需要导师提供的具体帮助

- 学术边界：确认 Collaborative Action Ontogenesis 是否具备独立论文强度，还是应作为大论文统一系统章节。
- 场景聚焦：确定 Full Action IR Test Set 优先选择维修手册、工业 SOP 还是业务策略。
- 专家资源：协助获得 2–3 名领域专家完成 Action IR 标注、冲突裁决和协作成本实验。
- 数据资源：协助争取可公开或可匿名发布的企业 SOP、元数据 Schema、API 和变更记录。
- 实验规范：确认人工评估规模、专家一致性统计和 human-subject study 是否需要伦理审批。
- 投稿定位：帮助判断三篇论文分别面向 ontology engineering / NLP extraction / agent systems 的投稿社区。
