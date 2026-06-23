# 面向本体动作层的研究：协作构建、文档抽取与智能体执行

> 版本：2026-06-23
> 定位：`action_layer_research_plan_zh.pptx` 的详细扩展稿
> 原则：区分已完成工作、初步证据和研究计划，不将设想表述为既成贡献。

## 1. 研究目标

本研究关注操作型本体中的 **Action Layer**。传统本体主要描述对象、属性、关系和规则，能够回答“领域中有什么”和“对象之间有什么关系”。面向 LLM Agent 和操作型系统，还需要回答：

- 当前可以执行哪些动作；
- 动作由谁执行并作用于哪个对象；
- 参数分别承担什么语义角色；
- 执行前必须满足哪些对象状态和业务条件；
- 执行后哪些对象、属性和关系发生变化；
- 哪条 policy、SOP、API 或执行证据支持该动作定义；
- 当条件不满足时，应该查询状态、补充参数、请求确认还是选择其他动作。

因此，本研究的目标不是为 Agent 增加一组独立的安全规则，而是：

> 构建可协作生成、可从程序文档持续扩充，并可供 Agent 理解、验证和执行的本体 Action Layer。

大论文采用“领域本体基础层 + Action Layer”的递进结构，三篇论文分别研究：

1. 数据本体如何从 Live Schema 低成本协作生成并持续演化；
2. 程序文档如何基于已有领域本体产生有证据、可验证的 Action IR；
3. 已发布的 Action IR 如何在运行时影响 Agent 的动作理解、可执行性判断和修复。

## 2. 核心研究问题

### 2.1 大论文研究对象为什么成立

当前存在四类彼此分离的知识载体：

| 知识载体 | 主要表达内容 | 对动作语义的不足 |
|---|---|---|
| 领域本体 | 对象、属性、关系、分类和静态约束 | 动作经常只是名称，缺少完整执行语义 |
| 程序文档 | 步骤、条件、异常、业务规则和经验 | 自然语言存在歧义，难以直接计算和复用 |
| API / Tool Schema | 接口名称、参数类型和调用格式 | 缺少对象状态、参数角色、业务条件和效果 |
| Agent Runtime | 对话历史、工具结果和临时状态 | 状态与领域本体、文档证据和动作定义割裂 |

大论文研究的不是某个工具调用规则，而是这四类表示之间的断裂：

> 领域本体缺少可操作的动作语义，程序文档中的动作知识难以进入本体，已经定义的动作语义又难以在 Agent 运行时被一致理解和使用。

因此，大论文的核心研究问题是：

> **如何把以静态概念描述为主的领域本体，扩展为可构建、可演化、可执行的动作知识层，并支撑智能体在动态环境中理解和使用动作语义？**

这里的“可执行”不是要求本体直接执行代码，而是要求动作知识具有足够明确的对象、角色、状态、条件、效果和证据，使其能够被确定性投影到运行时系统。

### 2.2 三个子问题与三篇论文

- **RQ1：Action Layer 所依赖的领域本体基础如何持续构建和演化？**
  如何从 Live Database Schema 发现对象和关系，并通过数据验证、多人确认和漂移重验证形成版本化数据本体？

- **RQ2：非结构化程序文档如何产生动作知识？**
  如何从 SOP、维修手册和业务策略中抽取动作、对象、参数角色、状态、条件和效果，并将其 grounding 到已有领域本体？

- **RQ3：动作知识如何被 Agent 在运行时使用？**
  如何把已发布的 Action IR 转化为运行时动作表示和本体状态，使 Agent 能够判断动作是否适用、缺少什么信息以及如何修复？

三个子问题构成完整生命周期：

```text
Live Schema 与采样数据
        ↓
协作式数据本体生成
        ↓
Versioned Data Ontology
        ↓
程序文档抽取与本体对齐
        ↓
Canonical Action IR
        ↓
运行时理解、验证和修复
        ↓
执行反馈与本体演化
```

三篇论文不是都输出 Action IR，而是形成“基础本体构建 → 动作知识获取 → 动作知识使用”的递进链条。

### 2.3 API Schema 案例只是问题说明

以 tau2 Retail 中的 `return_delivered_order_items` 为例，工具 Schema 可以定义：

```text
order_id: string
item_ids: array<string>
payment_method_id: string
```

Schema 可以约束字段名称、数据类型和是否必填，却不能完整表达：

- `order_id` 必须引用一个已观察到的 `Order` 个体；
- 该订单必须属于当前已认证用户；
- 当前订单状态必须为 `delivered`；
- `item_ids` 的语义角色是该订单中的 `source_items`；
- 所有商品必须真实属于同一订单；
- `payment_method_id` 必须引用该订单可使用的支付方式；
- 用户确认必须绑定到同一个动作及同一组参数；
- 动作执行后订单进入 `return requested` 状态；
- 这些语义分别来自哪条 policy、SOP 或执行证据。

这说明：

> API Schema 描述动作的调用语法；Action Layer 描述动作在业务世界中的语义。

这个例子只用于说明“工具接口与业务动作语义之间存在表示缺口”。它对应 Paper 3 的实验动机，但不是大论文总体研究问题。

## 3. 国内外研究现状

### 3.1 综合对照

| 区域 | 研究方向 | 已有代表工作或实践 | 本研究切入点 |
|---|---|---|---|
| 国外 | 本体构建与协作演化 | DILIGENT、NeOn 研究分布式贡献和版本演化；HyWay、IDEA2 研究 LLM、专家反馈和共识；CQ、ORSD 支持需求获取和范围验证 | 动作专用 Patch、可执行验证、运行反馈触发的重验证 |
| 国外 | 程序文档与流程抽取 | Text2Event、PET 研究事件、参与者和流程关系；PAGED、Universal Prompting 研究程序图；OMPD、NL2ProcessOps 连接工业程序表示和执行 | 对已有本体的 grounding、完整 Action IR、证据与确定性运行投影 |
| 国外 | 工具智能体与运行约束 | ToolRerank、ToolLLM 研究工具检索与选择；tau-bench、ToolSandbox、WorkArena 评估有状态交互；AgentSpec、Progent 研究运行规则 | 显式本体状态、类型感知 admissibility、ontology-guided repair |
| 国内 | 工业本体与知识图谱 | 重点描述设备、部件、工艺、故障和关系，用于查询、诊断、推荐、数据治理和数字孪生 | 补充动作对象、参数角色、状态、效果和可执行语义 |
| 国内 | SOP 与流程数字化 | 从工艺文档、维修手册和业务规程抽取实体关系、步骤序列、BPMN 或流程图 | 输出 ontology IDs、evidence、unresolved 字段和完整 Action IR |
| 国内 | 行业智能体与工具调用 | 使用 RAG、工具编排、工作流和平台规则；业务规则通常位于 Prompt、代码或流程配置中 | 让规则和动作约束来自 Action IR，并通过 `schema`/`ontology_full` 实验验证 |

### 3.2 国外研究的准确边界

国外相关工作已经分别解决了大量局部问题，因此不能笼统声称：

- 首次提出协作式本体构建；
- 首次用多 Agent 构建本体或知识图谱；
- 首次从程序文档抽取动作和流程；
- 首次表示动作前置条件和效果；
- 首次约束 Agent 的工具调用。

当前仍可研究的组合缺口是：

1. 用动作专用表示描述 `actor/target/roles/state/effect/constraints`；
2. 保留动作语义与原始文档、API 和执行轨迹之间的证据关系；
3. 将同一 canonical representation 用于协作构建、文档抽取和运行时执行；
4. 通过独立 benchmark 证明每个环节的机制收益。

### 3.3 国内研究的保守表述

不应使用“国内没有动作本体”或“国内尚未开展相关研究”这样的绝对结论。更准确的表述是：

> 国内在工业知识图谱、流程抽取、数字孪生、工作流编排和知识增强智能体方面已有广泛研究与应用，但公开成果通常分别输出实体关系、步骤流程、BPMN 或工具配置，尚缺少具有公开表示契约和可复现实验的 Action Layer 研究体系。

这个表述把研究缺口限定在：

- 表示契约是否公开；
- 动作语义是否完整；
- 构建、抽取和执行是否使用同一表示；
- 实验是否可以复现和对照。

### 3.4 CQ 能提供的有限帮助

Competency Questions、User Stories、Use Cases、Scenarios 和 ORSD 可以帮助 Paper 1：

- 从用户需求中确定 Action Layer 的覆盖范围；
- 把“系统应该支持什么”转化为专家可讨论的问题；
- 检查某个 Action IR 是否遗漏对象、状态、条件或效果；
- 为专家验收和版本变更提供需求依据。

但 CQ 不改变本研究主线：

- CQ 不是新的核心表示；
- 不需要提出 ACR 等新概念；
- CQ 不进入 Paper 2 的抽取主方法；
- CQ 不进入 Paper 3 的运行时方法；
- Paper 1 的创新不能建立在“使用了 CQ”之上。

CQ 的合理定位是 **Paper 1 的辅助需求工程工具**，而不是三篇论文的统一理论。

## 4. Palantir：最重要的产业参照

### 4.1 为什么 Palantir 是重点

Palantir Foundry Ontology 不只建立业务对象的语义模型，还把对象之上的动作、业务逻辑、权限和副作用组织为 operational layer。它直接证明了：

- Action Layer 不是纯理论抽象；
- 对象、动作和业务规则统一建模具有实际价值；
- 同一个动作定义可以跨应用复用；
- 动作执行需要权限、审计、监控和版本治理。

因此，Palantir 不是普通的相关产品案例，而是本研究最直接的产业参照和创新边界。

### 4.2 Palantir Ontology 的主要能力

Palantir 将 Ontology 中的元素区分为语义层和行为层。

#### Semantic Layer

- `Object Types`：业务对象类型；
- `Properties`：对象属性；
- `Link Types`：对象之间的语义关系；
- 将数据、模型和现实业务对象连接起来；
- 对象层同时包含安全、权限和变更治理。

#### Kinetic Layer

- `Action Types`：以事务方式修改对象、属性和链接；
- `Parameters`：动作输入；
- `Rules`：动作执行约束和业务逻辑；
- `Submission Criteria`：动作提交条件；
- `Functions`：封装和复用可演化业务逻辑；
- `Side Effects`：通知、Webhook 等外部效果。

#### Operational Governance

- 在多个应用中复用同一动作逻辑；
- 权限和动态安全控制；
- 动作监控与指标；
- `Action Log` 支持审计和问题追踪；
- Undo、Revert 和 Action Type branching 支持操作恢复与演化。

### 4.3 Palantir 已经覆盖了什么

| Palantir 能力 | 对本研究的直接启示 |
|---|---|
| Object/Link/Action Types 统一 | Action Layer 可以是领域本体的一等组成部分 |
| Parameters、Rules、Submission Criteria | 动作不只是工具名称，还需要参数语义和执行条件 |
| Functions | 动作规则应具有明确封装和版本边界 |
| Side Effects | Action IR 必须考虑动作对外部世界的影响 |
| Permissions 和动态安全 | actor、角色和权限属于动作语义 |
| Monitoring、Metrics、Action Log | 执行轨迹可以反向用于验证和演化动作定义 |
| Undo、Revert、Branching | Action Layer 需要版本、回滚和治理机制 |

### 4.4 本研究不能声称什么

由于 Palantir 已具备上述能力，本研究不能声称：

- 首次把动作加入本体；
- 首次把动作绑定到业务对象；
- 首次为本体动作定义参数、规则和提交条件；
- 首次表示动作副作用；
- 首次实现本体动作的权限、审计和版本治理。

### 4.5 相对 Palantir 的学术增量

本研究需要证明的不是“是否也能实现一个 Action Type 平台”，而是：

1. **开放表示**
   提出可以公开、讨论和复现的 Canonical Action IR。

2. **自动与半自动生成**
   从程序文档、API Schema、数据库元数据和执行轨迹生成动作定义，而不是完全依赖人工平台配置。

3. **协作验证和演化机制**
   从 Live Schema 构建对象/关系基础层，并用机器证据、人类共识和漂移重验证管理本体演化；再研究该机制向动作定义的扩展。

4. **学术 benchmark**
   分别评估数据本体生成的质量—成本权衡、动作抽取质量和 Agent 执行效用。

5. **Agent 运行时机制**
   使用公开 Action IR 驱动 Runtime Ontology State、type-aware admissibility 和 ontology-guided repair。

### 4.6 Palantir 与三篇论文的对应关系

| Palantir 工程能力 | Paper 1 | Paper 2 | Paper 3 |
|---|---|---|---|
| Object/Link/Action 的统一基础 | 协作生成对象与关系本体基础层 | 基于 existing ontology 生成动作候选 | 消费已发布动作定义 |
| Parameters 和 Rules | 管理语义冲突和版本 | 从文档抽取参数角色与条件 | 检查运行时参数和状态 |
| Functions 和 Side Effects | 验证规则与效果定义 | 抽取效果和状态迁移 | 用效果更新运行状态 |
| Monitoring 和 Action Log | 运行失败触发重验证 | 可作为新证据来源 | 记录 violation、repair 和执行结果 |
| 平台复用 | 研究 canonical representation | 生成统一 Action IR | 确定性编译为 ActionBank |

### 4.7 与 Palantir 对照时的论文口径

推荐表述：

> Palantir Foundry Ontology 已经证明了对象、动作、规则与副作用统一建模的产业价值。本文不主张首次提出本体动作层，而是研究如何以开放 Action IR 为核心，从多源证据生成和演化动作语义，并通过公开 benchmark 定量验证其对智能体执行的作用。

## 5. 大论文框架

### 第 1 章：绪论

- Action Layer 的研究背景和问题定义；
- API Schema、程序文档、领域本体和 Agent 运行时之间的表示断裂；
- 研究问题、总体框架和贡献边界。

### 第 2 章：Action IR 理论与表示

- 动作身份、对象、角色、状态和效果；
- Core 与 optional schema；
- Action IR、Action IR Patch、ActionBank 和 Procedure Graph 的关系；
- evidence、provenance、version 和 unresolved；
- 跨 Retail、Airline 和 Maintenance/SOP 的字段边界。

### 第 3 章：协作式数据本体生成与演化

- 从 Live Database Schema 冷启动生成数据本体；
- Phase A 低成本候选发现；
- Phase B 采样验证与人工语义确认；
- 多用户共识、冲突裁决和来源追踪；
- Schema 漂移触发的软废弃和增量重验证；
- 研究该机制如何为 Action Layer 提供对象与关系基础。

### 第 4 章：程序文档中的动作抽取

- 文档结构解析；
- 动作、对象、参数和状态抽取；
- existing-ontology grounding；
- evidence 与 procedure graph；
- Full Action IR benchmark。

### 第 5 章：面向 Agent 的运行时动作语义

- Action IR 到 ActionBank 的编译；
- Runtime Ontology State；
- epistemic 与 mutating action；
- type-aware admissibility；
- ontology violation 与 guided repair。

### 第 6 章：统一系统和跨域评估

- 三项方法的集成关系；
- Retail、Airline、Maintenance/SOP 实验；
- 本体质量、专家成本、任务成功率和运行开销；
- 适用边界和失败分析。

## 6. 三篇论文的关系与推进顺序

### 6.1 逻辑关系

| 论文 | 核心问题 | 输入 | 输出 |
|---|---|---|---|
| Paper 1 | 数据本体如何从 Live Schema 低成本协作生成和演化？ | Schema + Sampled Data + User Feedback | Versioned Data Ontology |
| Paper 2 | 文档如何产生动作候选？ | Document + Existing Ontology | Grounded Action IR Patch |
| Paper 3 | 已发布动作语义如何影响执行？ | Goal + History + ActionBank | Tool Call 或 Violation/Repair |

三篇论文形成递进关系，而不是都共享同一个输出：

- Paper 1 生成可协作演化的对象/关系本体基础层；
- Paper 2 使用 existing ontology 进行文档动作抽取和 grounding；
- Paper 3 使用 Action IR/ActionBank 进行运行时理解、校验和修复。

### 6.2 实际推进顺序

实际顺序是：

1. **Paper 3**：已有代码和初步结果，先判断 Action Layer 是否具有下游价值；
2. **Paper 2**：建立规模化、可追踪的 Action IR 来源；
3. **Paper 1**：把现有方法文档工程化，补齐关系金标、计算成本、专家成本和漂移实验。

## 7. 当前研究基础

| 工作 | 当前状态 | 可核查证据 |
|---|---|---|
| Retail Action IR | 已有原型 | `experiments/paper3_agent_planning/data/action_ir/retail_action_ir.json` |
| Action IR 编译器 | 已实现 | `compile_action_ir_to_action_bank.py` |
| Retail ActionBank | 已生成 | `data/action_bank/retail_action_bank.json` |
| Paper 3 Runtime Ontology | 已实现原型 | `src/runtime_ontology.py` |
| Paper 3 admissibility/repair | 已实现原型 | `src/tau2_admissibility.py`、`src/ontology_repair.py` |
| Paper 3 tau2 试验 | 有初步正向信号 | 341 个配对样本：44.9% → 55.7% |
| Paper 2 抽取试验 | 有内部结果 | 40 篇文档，四种方法 |
| Paper 1 协作式数据本体生成 | 已有完整方法文档和 Kyuubi 工作流设计 | `docs/collaborative-data-ontogenesis.docx`；代码与 benchmark 尚未在当前仓库形成可复现闭环 |
| Full Action IR Test Set | 尚未构建 | 公开数据只能覆盖部分字段 |

当前不能声称：

- 三篇论文均已完成；
- Paper 3 已获得稳定的任务级显著提升；
- Paper 2 的完整方法已优于直接基线；
- Paper 1 文档中的“10 倍专家效率”等案例数字已经由可复现实验验证；
- Action IR 已完成跨域验证。

## 8. Canonical Action IR

### 8.1 表示契约

```text
ActionIR = <
  identity,
  actor,
  target,
  parameters_with_semantic_roles,
  preconditions,
  effects,
  constraints,
  control_flow,
  ontology_grounding,
  evidence,
  runtime_projection
>
```

### 8.2 字段作用

| 字段层 | 主要内容 | 解决的问题 |
|---|---|---|
| Identity | id、name、type、action kind | 动作是什么 |
| Actor | role、permission | 谁可以执行 |
| Target | object type、binding | 动作作用于什么对象 |
| Parameters | type、required、semantic role | 参数的业务含义 |
| State | preconditions、effects、transition | 执行前后状态 |
| Constraints | policy、confirmation、reference integrity | 业务和执行约束 |
| Workflow | previous、next、branch、forbidden follow-up | 动作在流程中的位置 |
| Grounding | ontology action/type/property IDs | 如何连接领域本体 |
| Evidence | document、span、source、confidence | 语义依据来自哪里 |
| Runtime | tool name、grounding mode、projection | 如何供 Agent 使用 |

### 8.3 设计原则

- Action IR 是唯一 canonical representation；
- 缺少证据的字段标记为 `unresolved`；
- LLM 不能静默猜测未提供的信息；
- 治理数据放在 Proposal Envelope 中；
- ActionBank 必须由 Action IR 确定性生成；
- 文档证据、本体 ID 和运行时工具之间必须可追踪。

### 8.4 当前资产

| 资产 | 路径 | 作用 |
|---|---|---|
| Retail Action IR | `experiments/paper3_agent_planning/data/action_ir/retail_action_ir.json` | canonical 动作定义 |
| 编译器 | `experiments/paper3_agent_planning/compile_action_ir_to_action_bank.py` | IR → ActionBank |
| Retail ActionBank | `experiments/paper3_agent_planning/data/action_bank/retail_action_bank.json` | Paper 3 运行时视图 |
| 投影检查 | `smoke_action_ir_projection.py` | 检查确定性投影 |
| 方法对齐检查 | `smoke_method_alignment.py` | 检查方法与实现一致性 |
| 变体隔离检查 | `smoke_variant_isolation.py` | 检查实验方法隔离 |

当前 Action IR 仍是 Retail 原型。跨域主张必须等待 Airline 和 Maintenance/SOP 的字段复用与差异分析。

## 9. Paper 1：Collaborative Data Ontogenesis

Paper 1 以 `docs/collaborative-data-ontogenesis.docx` 为主要依据。其原始研究对象是：

> 从真实数据库和数据湖的 Live Schema 出发，通过机器候选发现、选择性数据验证和多人语义确认，协作生成并持续演化数据本体。

它首先构建的是对象、字段和关系构成的数据本体基础层，不是 Action IR。它与大论文的连接方式是：

- 为 Paper 2 提供 existing ontology 中的对象类型、属性和关系；
- 为 Action Layer 提供可协作演化的领域基础；
- 将 Paper 1 的证据、共识、版本和漂移机制进一步扩展到动作定义；
- 不能反过来把 Paper 1 原始方法改写成一篇 Action IR Patch 论文。

### 9.1 研究问题

Paper 1 面对的是数据本体工程中的质量、覆盖率和成本矛盾：

- 自动 Schema matching 可以覆盖大量表和列，但难以判断真实业务语义；
- 纯人工建模准确，但冷启动慢、专家成本高且难以覆盖长尾数据；
- 对全部候选执行全表 JOIN 代价过高；
- 多人贡献会产生重复、冲突和责任边界问题；
- Schema 持续变化，静态数据目录容易快速失效。

Paper 1 的研究问题应写为：

> 能否通过成本分层的证据获取和多人协作治理，从 Live Database Schema 低成本生成高覆盖、可追踪、可持续演化的数据本体？

### 9.2 原文档中的两阶段方法

#### Phase A：低成本全量发现

Phase A 不执行 JOIN，目标是快速获得全局覆盖：

1. `SHOW DATABASES`；
2. `SHOW TABLES`；
3. `DESCRIBE FORMATTED`；
4. 有限制地采样数据；
5. 推断格式、类型和字段特征；
6. 根据列名、数据类型和可选 LLM 语义生成候选关系。

Phase A 的输出不是正式本体事实，而是候选关系集合：

```text
CandidateEdge {
  id,
  type,
  from,
  to,
  schema_evidence,
  confidence,
  status = candidate
}
```

#### Phase B：选择性证据验证

Phase B 只对用户选择、高价值或不确定的候选执行高成本操作：

1. `TABLESAMPLE JOIN` 验证候选关系；
2. 计算 match rate、null rate、distinct count 等统计画像；
3. 用户确认、反驳或补充业务语义；
4. 多用户独立确认；
5. Owner 审核和争议裁决；
6. 将通过验证的关系发布到数据本体。

两阶段分离的核心不是流程拆分本身，而是：

> 将“全量覆盖”与“昂贵证据获取”解耦，让验证预算集中在最有价值或最不确定的候选上。

### 9.3 文档中是否存在“提案”

当前文档没有定义独立的 `Proposal` 对象，但 candidate edge 已经承担隐式提案的功能：

| 当前机制 | 提案语义 |
|---|---|
| 机器推测 candidate edge | 生成关系提案 |
| `source = candidate` | 尚无验证证据 |
| sampled JOIN | 自动证据验证 |
| 用户确认/反驳/补充 | 人工评审 |
| `disputed / pending_review` | 冲突提案待裁决 |
| `team_approved` | 提案被接受和发布 |
| Schema drift 后重验证 | 已接受提案重新打开 |

因此，准确表述是：

> **Candidate Edge is an implicit Ontology Relation Proposal.**

如果后续正式化，不建议直接使用 Action IR Patch，而应使用：

```text
OntologyRelationProposal {
  proposal_id,
  base_schema_version,
  semantic_edge,
  machine_evidence[],
  human_feedback[],
  confidence,
  consensus_level,
  review_status,
  owner_decision,
  audit_trail
}
```

### 9.4 建议的数据结构重构

原文档把语义、证据和治理信息集中在 Edge 中。为了便于实验和版本管理，建议拆成三层。

#### Semantic Edge

```text
SemanticEdge {
  id,
  relation_type,
  source_entity,
  target_entity,
  semantic_note
}
```

表示最终进入数据本体的领域语义。

#### Evidence Ledger

```text
EvidenceRecord {
  evidence_type,
  method,
  score,
  sample_spec,
  schema_hash,
  timestamp
}
```

记录列名/类型匹配、LLM 判断、采样 JOIN 和统计画像。机器置信度属于这里。

#### Governance Record

```text
GovernanceRecord {
  contributors,
  confirmations,
  objections,
  consensus_level,
  review_status,
  owner,
  decision
}
```

记录人的判断、争议和发布状态。共识级别属于这里。

拆分后的关键原则是：

> `confidence` 表示机器证据强度；`consensus_level` 表示组织对关系的认可程度。两者不能混为一个分数。

### 9.5 完整方法流程

1. **Discover**
   枚举数据库、表、列、类型、分区和基础样本。
   目的：获得接近全量的数据资产覆盖。

2. **Propose**
   根据名称、类型、统计特征和 LLM 语义生成 candidate edges。
   目的：把无限开放的本体建模转化为有限候选审核。

3. **Prioritize**
   按候选价值、不确定性、预估验证成本和用户需求排序。
   目的：决定有限 JOIN 和专家预算应投入哪里。
   这是原文档可以进一步深化的关键步骤。

4. **Validate**
   使用 sampled JOIN 和统计画像获取数据证据。
   目的：过滤仅由列名相似造成的错误关系。

5. **Confirm**
   用户确认、反驳或补充业务语义。
   目的：处理数据统计无法识别的业务口径和语义差异。

6. **Govern**
   聚合独立贡献、识别冲突，并由 Owner 裁决高风险关系。
   目的：把个人判断转化为组织可采用的本体事实。

7. **Publish**
   将批准的 Semantic Edge 发布到版本化数据本体。
   目的：区分候选关系和生产可用关系。

8. **Monitor and Evolve**
   通过 Schema hash、表/列变化和验证失效定位受影响关系，进行软废弃和选择性重验证。
   目的：避免 Schema 变化后全量重建。

### 9.6 可以深化的三个创新点

#### 创新一：成本自适应的证据获取

现有 Phase A/Phase B 可以进一步形式化为预算约束下的候选验证问题：

```text
Given:
  candidate relations C
  validation cost cost(c)
  uncertainty u(c)
  business value value(c)
  budget B

Select S ⊆ C:
  maximize expected ontology quality and coverage
  subject to Σ cost(c) ≤ B
```

核心贡献不是“先粗后细”，而是证明：

- Phase A 可以保持接近全量的候选覆盖；
- Phase B 可以用更少 SQL 扫描和 JOIN 获得接近 full validation 的关系质量；
- 不确定性或价值驱动的选择优于随机验证。

#### 创新二：证据—共识双轨关系生命周期

关系状态不应只由一个 confidence 字段决定。建议定义：

```text
evidence_state:
  candidate
  sampled_supported
  sampled_rejected

governance_state:
  unreviewed
  single_confirmed
  dual_confirmed
  disputed
  owner_approved
```

这允许研究：

- 高统计证据但低业务共识的关系；
- 低统计匹配但被专家确认的业务语义关系；
- 多人意见冲突的识别和路由；
- 机器置信度是否经过良好校准。

#### 创新三：漂移感知的增量演化

为每个关系记录依赖的：

- database/table/column identifiers；
- schema hash 或 version；
- validation query；
- evidence timestamp。

当表、列、类型或分区变化时：

1. 定位受影响关系；
2. 标记为 `stale` 或 `soft_deprecated`；
3. 只重跑相关验证；
4. 保留旧版本和决策轨迹；
5. 重新进入人工确认或 Owner 审核。

需要证明选择性重验证相较全量重建：

- 恢复更快；
- SQL 扫描更少；
- 不降低恢复准确率；
- 能保留未受影响的已确认知识。

### 9.7 工程贡献与科学贡献的边界

下列内容有工程价值，但单独不足以构成论文创新：

- JSON/JSONL 目录结构；
- 按数据库或表分片；
- 使用 Git 合并；
- 飞书 Base 或共享文档作为协作后端；
- 图谱可视化面板。

它们应被表述为方法落地和可复现基础。

科学贡献必须落在：

- 关系发现质量；
- 证据选择策略；
- 置信度校准；
- 人类确认成本；
- 冲突处理；
- Schema 漂移恢复。

### 9.8 实验设计

#### 实验任务

1. **Cold Start**
   从未标注的 Live Schema 构建对象和关系本体。

2. **Budgeted Validation**
   在固定 SQL 调用、扫描数据量或时间预算下选择候选进行验证。

3. **Semantic Confirmation**
   比较不同候选排序和任务呈现方式对专家效率的影响。

4. **Conflict Resolution**
   注入不同用户对 relation type、方向或业务含义的冲突。

5. **Schema Evolution**
   注入表重命名、列重命名、类型变化、表删除和关系失效。

#### Baselines

- Name/type heuristic matching；
- LLM-only semantic matching；
- 对所有候选执行 full JOIN validation；
- Human-only catalog construction；
- Phase A without Phase B；
- Phase A + random Phase B validation；
- 完整的 prioritized Phase A + Phase B 方法。

#### 指标

关系质量：

- relation precision / recall / F1；
- relation type accuracy；
- direction accuracy；
- approved relation coverage。

计算成本：

- SQL query count；
- JOIN count；
- scanned rows/bytes；
- wall-clock latency。

人工成本：

- expert minutes per approved edge；
- confirmations per accepted edge；
- time-to-consensus；
- disagreement rate。

可信度质量：

- calibration error；
- Brier score；
- precision at confidence threshold。

演化能力：

- stale relation detection precision/recall；
- recovery accuracy；
- time-to-recovery；
- revalidated relation ratio。

#### 消融

- No Sampling Validation；
- No Human Confirmation；
- No Consensus；
- No Evidence Ledger；
- No Priority Selection；
- No Drift Revalidation。

### 9.9 当前证据和必须修正的表述

DOCX 中描述了以下案例数字：

- 冷启动从数周降低到数分钟；
- 单库探索从 1–2 天降低到 10–30 分钟；
- 用户投入降低 10 倍以上；
- 约 100 张表产生约 200 条候选关系；
- 约 60% 候选经验证成立；
- 用户补充约 30 条机器未发现关系。

这些数字目前应视为 **案例描述或 pilot observation**。在当前仓库中没有发现对应的可复现实验代码、原始日志、数据切分和统计报告，因此论文和 PPT 不能直接把它们写成已经验证的普遍结论。

需要补齐：

- 可运行 Kyuubi/Data Explorer 实现；
- 固定的数据快照和 Schema 版本；
- 关系金标及标注协议；
- SQL、扫描量和延迟日志；
- 用户任务和计时记录；
- 统计检验和误差分析。

### 9.10 独立成文门槛

Paper 1 至少需要证明：

- 相比名称/类型规则和 LLM-only，提高关系质量；
- 相比 full JOIN validation，显著降低计算成本且质量损失可控；
- 相比 Human-only，降低单位 approved edge 的专家时间；
- 证据—共识双轨设计优于单 confidence 状态；
- 漂移感知重验证优于全量重建和静态目录。

如果只能证明工具使用方便，而不能证明质量—计算成本—人工成本的联合优势，应将其定位为工程系统或大论文基础章节，而不是独立方法论文。

## 10. Paper 2：本体约束的程序动作抽取

### 10.1 输入输出

```text
Input:
  Procedural Document + Existing Ontology

Output:
  Grounded Action IR Patch
  + Procedure Graph
  + Evidence
```

### 10.2 方法步骤

1. 解析标题、表格、步骤号和版面结构；
2. 识别动作、条件、异常和规则单元；
3. 使用 LLM 生成受控 Action IR；
4. 检索 ontology candidates；
5. 使用类型、对象和参数角色约束 grounding；
6. 构建 control-flow；
7. 执行 schema 和 evidence 校验；
8. 对无法对齐的字段显式标记 `unresolved`。

### 10.3 当前 40 篇内部试验

结果文件：

`experiments/paper2_action_extraction/results_kimi_full40/run_20260609_142044/combined_results.json`

| 方法 | Action mention F1 | Action type accuracy | Target grounding | Parameter grounding F1 | Validation pass |
|---|---:|---:|---:|---:|---:|
| Rule | 54.2% | 65.3% | 92.5% | 81.1% | 7.3% |
| LLM-Only | 4.3% | 7.4% | 20.0% | 20.0% | 6.5% |
| LLM-Ontology | 85.1% | 80.3% | 98.4% | 88.8% | 81.0% |
| Ours | 79.2% | 78.3% | 98.5% | 91.6% | 22.8% |

当前结果说明：

- ontology grounding 明显优于 LLM-Only；
- `Ours` 在 target grounding 和 parameter grounding F1 上略高；
- `LLM-Ontology` 在 action mention、action type 和 validation pass 上更好；
- `Ours` 的 validation pass 只有 22.8%，是必须定位的问题；
- evidence span 和 control-flow 指标为 0，说明评测链路尚不完整。

因此当前不能声称完整方法最好。

### 10.4 数据集分工

| 数据 | 提供能力 | 限制 |
|---|---|---|
| MyFixit | action、part、tool | 只有部分子集人工标注 |
| MSPT | operation、material、argument | 缺 flow 和 ontology ID |
| PET | actor、gateway、control-flow | 45 篇，test-only |
| ProPara | 状态变化 | 非工业程序文档 |
| BioProcess | event、argument | 生物领域 |
| OMIn | target grounding | 不是 procedure |
| PAGED | 程序图和流程结构 | 需要补充下载与转换 |
| Text-mined Synthesis | weak supervision | 银标，不能作为最终 gold |
| Full Action IR Test Set | 完整输出契约 | 必须人工构建 |

当前 `dataset/idea2_sop_action_benchmark/processed/*.jsonl` 的 `annotations` 为空，不能将记录数量当作监督样本数量。

### 10.5 Full Action IR Test Set

需要标注：

- actor；
- target；
- parameters 和 semantic roles；
- preconditions；
- effects；
- constraints；
- control-flow；
- ontology IDs；
- evidence spans；
- unresolved fields。

建议：

- 100–200 个动作实例；
- 双人独立标注；
- 专家裁决；
- 报告 inter-annotator agreement；
- 文档级划分，防止同一手册步骤泄漏。

### 10.6 成立门槛

- 在公开数据上分别报告字段、grounding 和 flow 指标；
- 在 Full Action IR Test Set 上报告 exact match、evidence 和 validation；
- 完整方法优于 `LLM-Only` 和 `LLM-Ontology`，或证明可解释的质量/校验权衡；
- Action IR 能确定性生成 ActionBank；
- 生成的 ActionBank 能改善下游 Agent 指标。

## 11. Paper 3：面向 Agent 的本体动作语义

### 11.1 方法主张

Paper 3 不是“在工具调用前增加规则列表”。完整机制要求：

- 动作定义来自 Canonical Action IR；
- Action IR 确定性编译为 ActionBank；
- 对话和工具结果被转换为 Runtime Ontology State；
- epistemic action 和 mutating action 使用不同 grounding 强度；
- 校验失败返回结构化 ontology violation；
- repair 根据违反的动作语义选择下一步。

### 11.2 为什么区分 epistemic 和 mutating action

#### Epistemic action

用于查询、认证和获取状态，例如：

- `find_user_id_by_email`；
- `get_order_details`；
- 检查账户、订单或支付状态。

这类动作使用弱 grounding，因为它们的目标就是获取未知信息。如果要求目标对象必须已缓存，会形成启动死锁。

#### Mutating action

用于修改对象状态，例如：

- 取消订单；
- 退货；
- 修改地址；
- 退款。

这类动作使用强 grounding，执行前检查：

- actor 和权限；
- target 对象；
- 参数语义角色；
- 前置状态；
- policy 约束；
- 与动作及参数绑定的用户确认。

### 11.3 当前实现

| 环节 | 文件 |
|---|---|
| Agent 主入口 | `experiments/paper3_agent_planning/tau2_ontology_agent.py` |
| Runtime Ontology State | `src/runtime_ontology.py` |
| Type-aware admissibility | `src/tau2_admissibility.py` |
| Ontology-guided repair | `src/ontology_repair.py` |
| IR 编译 | `compile_action_ir_to_action_bank.py` |
| Action IR | `data/action_ir/retail_action_ir.json` |
| ActionBank | `data/action_bank/retail_action_bank.json` |
| Epistemic 语义检查 | `smoke_epistemic_action_semantics.py` |
| 投影检查 | `smoke_action_ir_projection.py` |
| 方法对齐检查 | `smoke_method_alignment.py` |
| 变体隔离检查 | `smoke_variant_isolation.py` |

### 11.4 取消订单示例

用户请求：

> 请取消订单 #123，因为我下错单了。

执行逻辑：

1. 初始状态不知道用户身份、订单个体和订单状态；
2. 直接执行 `cancel_pending_order` 不满足 strong grounding；
3. Agent 先执行认证动作；
4. Agent 调用 `get_order_details(#123)`；
5. 工具结果进入 Runtime Ontology State：

```text
Order(#123).status = pending
User.authenticated = true
```

6. Agent 请求用户确认；
7. 确认绑定到：

```text
cancel_pending_order(
  order_id=#123,
  reason=ordered_by_mistake
)
```

8. strong grounding 检查 target、status、reason 和 confirmation；
9. 通过后执行动作；
10. 登记 `pending → cancelled`。

反事实：

- 若订单状态为 `delivered`，返回 `PreconditionViolation`；
- repair 不能继续重试取消；
- 应根据 ActionBank 转向退货、询问或人工处理。

### 11.5 当前初步结果

主分析：

- 341 个严格配对样本；
- 114 个任务；
- 3 个完整 trials。

| 方法 | Success |
|---|---:|
| Schema-Only | 44.9% |
| Typed + Repair | 55.7% |

其他结果：

- 提升 `+10.9` 个百分点；
- paired McNemar `p=0.0029`；
- task-level sign test `p=0.109`，未显著；
- transfer calls `323 → 62`；
- 平均延迟 `190.6s → 260.3s`。

### 11.6 结果如何解释

积极信号：

- ontology-aware 方法在严格配对样本上有明显提升；
- 错误 transfer 数量显著下降；
- 结果值得完成修复版全量重跑。

不能回避的限制：

- task-level 统计未显著；
- 计划的 8 trials 因模型配额中断；
- confirmation binding 存在缺陷；
- 修复版尚未完成端到端重跑；
- 成功率提升伴随约 36.6% 延迟增加；
- 当前结果不能支撑“通用 Agent planning 已解决”。

### 11.7 仍需完成的实验

1. 修复 confirmation binding；
2. 跑完 `schema` 与 `ontology_full` 全量 paired trials；
3. 完成 `No Repair`、`No Grounding` 等组件消融；
4. 报告 task cluster bootstrap、task-level test 和 effect size；
5. 分析 violation 类型、repair 成功率和无效 transfer；
6. 分析 latency 和 token 成本；
7. 在 Airline 或 ABCD 上做外部验证；
8. 加入 Oracle ontology 或人工金标状态，区分表示错误和决策错误。

### 11.8 成立门槛

- 完整 trials 下仍有稳定成功率提升；
- task-level 置信区间或检验支持跨任务收益；
- ontology_full 相比 schema 的收益可由 violation 和 repair 机制解释；
- 消融证明收益不是来自更长 prompt、更多重试或硬编码规则；
- 明确报告延迟、成本和适用边界。

## 12. 证据矩阵

| 论文主张 | 当前证据 | 必须补齐 | Go/No-Go |
|---|---|---|---|
| 两阶段协作生成改善关系质量—计算成本—人工成本权衡 | 方法文档和案例描述 | 关系金标、SQL/扫描日志、专家实验、漂移实验 | 无联合优势则收缩为工程系统 |
| 本体约束提高完整动作抽取 | 40 篇内部试验，结果混合 | 公开 benchmark、Full IR 金标、修复 evidence/flow/validation | 完整方法不能超过直接基线则收缩主张 |
| 本体动作语义提高 Agent 执行 | tau2 初步 `+10.9 pp` | 修复版完整 trials、task-level 统计、外部域 | 无稳定任务级收益则转为 verifier/diagnosis 论文 |

## 13. 推进计划与验收物

### 2026 Q3：Paper 3

任务：

- 修复 confirmation binding；
- 完成全量 paired trials；
- 完成组件消融；
- 完成任务级统计和误差分析。

交付物：

- 可复现实验命令；
- 原始结果和 manifest；
- 统计报告；
- 论文表格和失败案例。

### 2026 Q3：固定共享模型

任务：

- 冻结 Action IR core schema；
- 验证 Airline 投影；
- 记录 Retail/Airline/Maintenance 的字段差异；
- 明确 core 和 optional 字段。

交付物：

- Action IR schema；
- compiler contract；
- projection tests；
- 跨域字段审计表。

### 2026 Q3-Q4：Paper 2

任务：

- 修复 processed converter；
- 修复 evidence/control-flow 评测；
- 引入 PAGED；
- 构建 100–200 个 Full Action IR；
- 完成公开 benchmark 和下游实验。

交付物：

- 转换后的公开数据；
- 专家金标与 agreement；
- 字段、结构和下游结果；
- 完整误差分析。

### 2026 Q4：Paper 1

任务：

- 将 DOCX 中的 Kyuubi/Data Explorer 工作流工程化；
- 固化 Candidate Edge、Evidence Ledger 和 Governance Record；
- 建立数据库关系金标和 Schema evolution 版本；
- 对比 heuristics、LLM-only、full JOIN 和 Human-only；
- 测量关系质量、SQL/扫描成本、专家分钟数和漂移恢复。

交付物：

- 可运行的两阶段协作系统；
- Candidate Edge、证据、共识、冲突和版本数据；
- 计算成本与专家实验；
- Paper 1 独立成文的 Go/No-Go 结论。

## 14. 需要导师作出的决策

1. **Paper 1 定位**
   是否认可 Paper 1 以 `Collaborative Data Ontogenesis` 为独立研究对象，并作为大论文对象/关系基础层，而不是 Action IR 构建论文？

2. **人工金标领域**
   维修手册、工业 SOP 还是业务策略？
   当前建议优先维修/工业 SOP。

3. **专家资源**
   能否协调 2–3 名领域专家完成 Action IR 标注、冲突裁决和时间记录？

4. **Paper 3 扩域门槛**
   是否以修复版获得稳定 task-level 收益作为扩展 Airline 的前提？

5. **Paper 2 投稿主线**
   以抽取准确率为主，还是以 executable representation 和 downstream utility 为主？

6. **可发布数据**
   能否获得可匿名发布的 SOP、Schema、API 和变更记录？

## 15. 导师可能追问

### 15.1 这是不是在复刻 Palantir？

不是。Palantir 是成熟的商业 operational ontology 平台。本研究不竞争平台功能，而研究：

- 开放 Action IR；
- 文档和多源证据生成；
- 协作验证与演化；
- 公开 benchmark；
- Agent 运行时机制和可复现实验。

### 15.2 Paper 1 不是 Action IR，三篇论文是否还能形成大论文？

可以，但不能声称三篇论文只共享 Action IR。更准确的层次关系是：

- Paper 1 构建可协作演化的数据本体基础层；
- Paper 2 基于已有本体从文档构建 Action Layer；
- Paper 3 使用 Action Layer 支撑 Agent 运行。

大论文统一性来自“基础本体 → 动作知识获取 → 动作知识使用”的递进关系。

### 15.3 CQ 是否是新的研究主线？

不是。CQ 只辅助 Paper 1 的需求获取和专家验收，不进入 Paper 2、Paper 3，也不作为总体创新。

### 15.4 Paper 3 是否只是规则 verifier？

若规则是独立手写列表，则确实只是 verifier。本文要求规则来自统一 Action IR，并同时驱动：

- Runtime Ontology State；
- admissibility；
- violation；
- repair；
- explanation；
- execution feedback。

### 15.5 Paper 1 是否只是数据目录工具？

如果只展示 Kyuubi 命令、JSON 文件和协作界面，它就是数据目录工具。必须通过预算约束的证据选择、证据—共识双轨生命周期和漂移感知重验证，以及质量、SQL 成本和专家成本实验，证明其方法贡献。

### 15.6 当前最薄弱的部分是什么？

- Paper 1 有完整方法文档，但可复现代码、关系金标和系统实验尚未闭环；
- Paper 2 完整方法没有全面优于 `LLM-Ontology`；
- Paper 2 的 evidence 和 flow 评测不完整；
- Paper 3 task-level 统计未显著；
- Paper 3 修复版尚未完成全量重跑；
- Action IR 尚未跨域验证。

## 16. 汇报口径

- 研究对象是 Action Layer，不是泛化知识图谱，也不是 CQ。
- Palantir 已证明 Action Layer 的产业价值，同时限定了“首次提出动作本体”等不可成立的主张。
- 学术增量必须落在开放表示、自动生成、协作演化和公开实验上。
- 已完成的是 Retail Action IR 原型和 Paper 3 运行时链路，不是完整体系。
- Paper 3 有正向信号，但尚无稳定任务级结论。
- Paper 2 当前结果暴露了方法和评测问题，不能包装为领先结果。
- Paper 1 的独立价值取决于关系质量、计算成本、专家成本和漂移恢复四类证据。
- 三篇论文的统一性来自“基础本体构建 → 动作知识获取 → 动作知识使用”的层次递进；每篇论文仍需独立实验支持。

## 17. 参考入口

- Palantir Foundry Ontology Overview: <https://www.palantir.com/docs/foundry/ontology/overview/>
- Palantir Action Types Overview: <https://www.palantir.com/docs/foundry/action-types/overview/>
- IDEA2: <https://arxiv.org/abs/2604.01344>
- OntoChat: <https://arxiv.org/abs/2408.15256>
- tau2 实验说明：`experiments/paper3_agent_planning/README.md`
- Paper 3 官方运行说明：`experiments/paper3_agent_planning/OFFICIAL_TAU2_RUNS.md`
