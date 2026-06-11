# 研究方案：工业本体增强与 SOP 到动作层抽取

日期范围：最近四年按 `2022-05-14` 到 `2026-05-14` 处理。

本文覆盖两个研究想法：

1. 从 BoM、BoP、SysML 及相关工业文档/模型中抽取知识，对从元数据生成的本体进行语义增强。
2. 从中文或英文非结构化数据中抽取 Standard Operating Procedure（SOP），再生成 ontology 系统中的动作层。

## 总体判断

第二个想法更容易用公开数据做可验证实验。SOP / 流程抽取有 PET、WONDERBREAD、SOPBench、SOP-Bench、BREX/BPRF 以及若干 procedural graph benchmark。

第一个想法的工业价值更强，但 benchmark 更难做。公开的 BoM/BoP/SysML 风格数据通常以标准、模板、模型示例或信息模型的形式出现，而不是“元数据本体 + 文档语义增强 gold label”的成对数据集。因此，这条线更适合先构建自己的 benchmark。

建议定位：

- 短论文 / 第一阶段实验：先做 SOP-to-action，因为评估更清晰。
- 更强的工业研究线：元数据优先的本体 + 文档语义增强，但需要自建 benchmark。
- 最佳组合方向：用元数据建立本体骨架，用 SOP / 文档抽取补语义增强和动作候选。

## 想法 1：元数据本体 + 文档语义增强

### 研究问题

非结构化或半结构化工业来源，能否为元数据派生的本体补充定义、别名、规则、约束、状态语义、过程知识、证据链接和动作相关语义，同时不破坏本体骨架？

### 什么算“元数据本体”

可能的元数据来源：

- 数据库 schema
- API schema
- OPC UA NodeSet
- AAS submodel template
- SysML v2 文本模型
- AutomationML 文件
- BoM / BoP 表格
- MES / PLM / ERP 对象模型

由元数据生成的本体应包含：

- classes / object types
- properties
- relations
- 枚举值
- 生命周期状态
- ID、标签、溯源信息

### 什么算“语义增强”

不要让文档抽取自由创建正式本体。应把抽取结果放到增强层：

| 增强类型 | 示例 |
|---|---|
| 定义 | WorkOrder 表示针对某个物料和工序下达的生产任务。 |
| 别名 | WorkOrder = 工单 = 生产任务单 = WO |
| 状态语义 | REWORK_REQUIRED 表示质检失败，需要返修。 |
| 业务规则 | temperature > 80 C 时需要 stopEquipment。 |
| 约束 | 焊接电流必须在 110-130 A。 |
| 流程 | 停机、创建工单、检查冷却系统。 |
| 角色策略 | 质检员确认检验结果。 |
| 证据 | 来源文档、页码、章节、文本片段、置信度。 |

### 可用公开数据 / benchmark 候选

| 数据集 / 来源 | 用途 | 优点 | 局限 |
|---|---|---|---|
| Text2KGBench, https://github.com/cenguix/Text2KGBench | 面向 ontology 约束的文本到 KG 抽取。 | 有 ontology、句子和期望事实，适合衡量 ontology conformance。 | 通用领域，不是工业领域。 |
| OntoEKG, https://github.com/LiberAI/OntoEKG | 从非结构化企业文本构建端到端 ontology。 | 提供代码和小规模企业场景评估。 | 规模小；与 BoM/BoP/SysML 的直接对应有限。 |
| AAS Submodel Templates, https://github.com/admin-shell-io/submodel-templates/tree/main/published | 工业元数据模板，覆盖资产、类似 BoM 的层级、维护、质量、工艺参数。 | 很适合工业元数据本体。 | 多数是模板，不是文本到增强的 gold label。 |
| OPC UA NodeSets, https://github.com/OPCFoundation/UA-Nodeset | 工业信息模型，XML/CSV 形式。 | 结构化元数据来源，覆盖多个领域。 | 不是非结构化数据，需要额外文档或人工标注。 |
| SysML v2 Release examples, https://github.com/Systems-Modeling/SysML-v2-Release | SysML 文本模型、模型库和示例。 | 适合 model-to-ontology 转换。 | 公开的具体工业场景有限。 |
| AutomationML RobotCell example, https://www.automationml.org/news/example-file-of-a-robotcell/ | 机器人单元的 XML 工厂工程模型。 | 半结构化工程模型，适合作为输入。 | 示例很小，不是标注数据集。 |
| 2024 年制造服务 KG 数据集 | 制造服务、认证、位置、网站。 | 工业 KG，结合结构化/非结构化网页数据。 | 更偏供应商/服务发现，不是 BoM/BoP/SysML。 |

重要限制：我没有找到直接配对的公开 benchmark，能够同时提供 BoM/BoP/SysML 元数据和语义增强 gold label。因此，这条研究线大概率需要自己构造 benchmark。

### 近期论文

| 年份 | 论文 | 相关性 |
|---|---|---|
| 2022 | Natural Language Processing for Systems Engineering: Automatic Generation of SysML Diagrams | 从规格/手册/报告生成 SysML 图，和 SysML 抽取直接相关。 |
| 2022 | Towards Ontology Reshaping for KG Generation with User-in-the-Loop: Applied to Bosch Welding | 工业 KG schema 重新塑形，和元数据/本体非常相关。 |
| 2022 | Query-based Industrial Analytics over Knowledge Graphs with Ontology Reshaping | 工业分析场景下的 ontology reshaping。 |
| 2023 | Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | ontology 约束抽取的核心 benchmark。 |
| 2023 | Construction of Knowledge Graphs: State and Challenges | KG 构建综述，适合定位 pipeline 和质量保证。 |
| 2023 | Enhancing Knowledge Graph Construction Using Large Language Models | 用 LLM 做 KG 和 ontology 构建。 |
| 2023 | Semantic Modelling of Organizational Knowledge as a Basis for Enterprise Data Governance 4.0 | 元数据驱动的企业治理和语义 web 方法。 |
| 2024 | Generation of Asset Administration Shell with Large Language Model Agents | 相关于工业数字孪生语义模型的 AAS 自动生成。 |
| 2024 | Building A Knowledge Graph to Enrich ChatGPT Responses in Manufacturing Service Discovery | 从结构化/非结构化来源构建制造服务 KG。 |
| 2024 | Automated Extraction and Creation of FBS Design Reasoning Knowledge Graphs from Structured Data in Product Catalogues | 从产品目录/规格构建 FBS ontology KG，接近 BoM / 设计元数据增强。 |
| 2025 | OntoRAG: Enhancing QA through Automated Ontology Derivation from Unstructured Knowledge Bases | 从非结构化知识库推导 ontology，和文档到 ontology pipeline 直接相关。 |
| 2026 | LLM-Driven Ontology Construction for Enterprise Knowledge Graphs | 从企业文本抽 classes / properties / hierarchy。 |
| 2026 | TRACE-KG for Context-Enriched Knowledge Graphs from Complex Documents | schema induction + traceable KG，适合证据驱动增强。 |
| 2026 | From Prompt to Graph: Comparing LLM-Based IE Strategies in Domain-Specific Ontology Development | 制造/铸造 ontology 构建。 |
| 2026 | Ontology-Compliant Knowledge Graphs | ontology compliance、匹配、对齐和指标。 |

### 实验设计

#### 任务定义

输入：

- 元数据本体骨架，例如来自 AAS / OPC UA / SysML / DDL
- 文档语料，例如手册、submodel 描述、维修说明、质量模板、SOP

输出：

- 绑定到本体元素的语义增强标注
- 每条标注必须有证据片段和审查状态

建议输出 schema：

```json
{
  "target_kind": "ObjectType|Property|Relation|State|Action",
  "target_id": "Equipment.temperature",
  "enrichment_type": "definition|alias|rule|constraint|procedure|state_semantics|role_policy",
  "content": {},
  "evidence": {
    "document_id": "",
    "page": null,
    "section": "",
    "text_span": ""
  },
  "confidence": 0.0
}
```

#### Baselines

1. 仅元数据本体：不做文档增强。
2. 仅文本 LLM ontology 抽取：不使用元数据骨架。
3. 元数据 + 向量 RAG：按 ontology 标签检索，再让 LLM 总结。
4. ontology 约束抽取：只抽取与现有本体元素绑定的增强类型。
5. ontology 约束抽取 + verifier：加入 SHACL / JSON schema 校验、证据检查和矛盾检测。
6. 人工在环主动学习：把不确定映射送人工修正。

#### 指标

| 指标 | 含义 |
|---|---|
| 实体链接 precision / recall / F1 | 抽取到的语义是否正确绑定到本体元素。 |
| 增强类型准确率 | 规则、别名、定义、约束等分类是否正确。 |
| 证据正确率 | 文本片段是否真的支持该增强。 |
| schema 一致性 | 输出是否符合目标类型与增强 schema。 |
| SHACL 违规数 | 增强后的图是否违反形式化约束。 |
| Competency question 提升 | 与仅元数据本体相比，增强是否改善问答能力。 |
| 检索提升 | 别名/定义增强是否提高检索命中率。 |
| 人工接受率 | 被审核通过的增强比例。 |
| 幻觉率 | 没有证据支持的抽取陈述比例。 |

#### benchmark 构建计划

1. 选择 3 个公开元数据来源：
   - AAS submodel templates：维护、工艺参数、质量控制、BoM 层级。
   - OPC UA NodeSets：机床、机器人、设备、传感器。
   - SysML v2 examples：需求、block、port、action、state。
2. 自动构建 metadata-derived ontology。
3. 收集配套公开文档：
   - template 说明
   - 模型文档
   - 维护说明
   - 公开手册或标准说明
4. 标注 200-500 条增强项：
   - 50 条定义
   - 50 条别名
   - 50 条规则/约束
   - 50 条状态/过程语义
   - 50 条流程/动作
5. 用上述 baselines 评估。

### 预期贡献

更有价值的贡献不是“LLM 从文档抽 ontology”。这已经很拥挤。更强的表述是：

元数据本体结构可靠但语义较薄。我们提出一个有证据约束的语义增强层，在保留元数据骨架的前提下，补充文档派生的语义，并配合形式化验证和人工审核。

# SOP 抽取到 ontology 动作层

## 研究问题

能否把中文或英文非结构化文档抽出的 SOP，变成带对象、角色、参数、前置条件、后置效果、状态迁移、证据和可执行验证的 ontology action？

## 目标表示

不要直接生成平台专用动作。先生成一个中间 action IR：

```json
{
  "action_name": "submitQualityFailure",
  "target_object": "WorkOrder",
  "actor_role": "QualityInspector",
  "parameters": [
    {"name": "failure_reason", "type": "string", "required": true}
  ],
  "preconditions": [
    "WorkOrder.status == 'IN_INSPECTION'"
  ],
  "effects": [
    "create NonconformanceRecord",
    "set WorkOrder.status = 'REWORK_REQUIRED'"
  ],
  "exceptions": [],
  "evidence": {
    "document_id": "",
    "text_span": ""
  }
}
```

### 可用公开数据 / benchmark 候选

| 数据集 / 来源 | 用途 | 优点 | 局限 |
|---|---|---|---|
| PET, https://huggingface.co/datasets/patriziobellan/PET | 英文过程抽取。 | 标注了 activities、gateways、actors 和 flow information。本地已有 parquet。 | 规模小：只有 45 个样本。 |
| WONDERBREAD, https://github.com/HazyResearch/wonderbread | 从 workflow demonstrations 生成 SOP。 | 2,928 demonstrations，598 workflows，包含 SOP、录制、轨迹、关键帧。 | Web workflow，不是工业现场。 |
| SOPBench, https://github.com/Leezekun/SOPBench | agent 遵循 SOP 和约束。 | 903 test cases，167 tools/functions，可执行 verifier 和 trajectories。 | 重点是 SOP 遵循，不是 raw document 抽取。 |
| SOP-Bench, https://github.com/amazon-science/SOP-Bench | 复杂工业 SOP 执行 benchmark。 | 2,000+ tasks，12 个领域，自然语言 SOP、工具、测试用例。 | 合成/人机合成数据；许可证和版本需核查。 |
| BREX, https://huggingface.co/datasets/XiaopiYu/BREX | 中文 business rule flow 抽取。 | 409 文档，2,855 条 rules，支持顺序/条件/并行依赖。 | 规则流 benchmark，不是完整 SOP-to-action。 |
| BPRF / Business as Rulesual 相关论文 | 中文业务流程规则。 | 早期版本有 50 文档和 326 条 `<Condition, Action>` 规则。 | 数据集命名和版本似乎已演变为 BREX。 |
| PAGED | 文档中的 procedural graph 抽取。 | 直接相关 benchmark。 | 我没有核实到主要公开数据仓库。 |
| PcMSP | 科学/材料流程抽取。 | 305 个 synthesis procedures，含实体/关系。 | 领域高度特定。 |
| FlaMBé, https://zenodo.org/records/10050681 | 生物医学工作流抽取。 | 55 篇全文和 1,195 个摘要，带 workflow/tool/context 注释。 | 生物医药领域，不是 business/industrial SOP。 |
| FlowExtract, https://github.com/guille-gil/FlowExtract | 维护流程图抽取。 | 与工业 troubleshooting diagram 很相关。 | 公开仓库偏代码，源工业数据可能被脱敏或不可公开。 |

### 近期论文

| 年份 | 论文 | 相关性 |
|---|---|---|
| 2023 | Large Language Models can accomplish Business Process Management Tasks | LLM 用于 BPM 任务，包括从文本挖流程模型。 |
| 2023 | Procedural Text Mining with Large Language Models | 用 ontology / few-shot prompt 从 PDF 文本抽流程。 |
| 2024 | WONDERBREAD | BPM benchmark，包含 SOP 生成、QA、验证和改进任务。 |
| 2024 | PAGED: A Benchmark for Procedural Graphs Extraction from Documents | procedure graph 抽取 benchmark。 |
| 2024 | Human Evaluation of Procedural Knowledge Graph Extraction from Text with LLMs | 抽步骤、动作、对象、设备、时间信息进入 procedural KG。 |
| 2025 | SOP-Agent | 用 decision graph 引导 agent 执行 SOP。 |
| 2025 | Agent-S | 用 agentic workflow 自动化 SOP。 |
| 2025 | SOPBench | 评估 language agents 遵循 SOP / constraints。 |
| 2025 | Business as Rulesual / BPRF | 中文业务规则抽取和依赖建模。 |
| 2025 | SOP-Bench: Complex Industrial SOPs | 工业风格 SOP 执行 benchmark。 |
| 2026 | JourneyBench | 面向 customer support 的 policy/SOP adherence benchmark。 |
| 2026 | SOPRAG | 工业 SOP 检索，使用 entity / causal / flow graph experts。 |
| 2026 | Procedural Knowledge Extraction from Industrial Troubleshooting Guides Using VLMs | 从工业 troubleshooting diagrams 抽取。 |
| 2026 | FlowExtract | 结合 CV/OCR/arrow-tracing 的流程图抽取。 |
| 2026 | SAGE | 从非结构化 SOP 到动态 dialogue graph 的图引导评估。 |
| 2026 | SupChain-Bench | 供应链 SOP / tool orchestration benchmark。 |

### 实验设计

#### 任务拆分

1. SOP 检测：
   - 判断一个文档片段是否包含流程 / SOP。
2. 步骤抽取：
   - 抽取有序步骤和嵌套步骤。
3. 语义角色抽取：
   - actor、object、input、output、equipment、material、parameter、quality check。
4. 控制流抽取：
   - 顺序、条件、并行、循环、异常。
5. 状态 / 动作抽取：
   - 将步骤映射到目标对象、前置条件、后置效果。
6. ontology 动作生成：
   - 生成带参数、权限、校验和效果的 action IR。
7. 可执行验证：
   - 在 simulator 或 rule engine 中测试生成动作。

#### Baselines

1. 直接 LLM 抽取为 JSON。
2. 两阶段抽取：先 SOP graph，再 action。
3. ontology 约束抽取：使用来自元数据本体的 object / action schema。
4. self-refine 图抽取：先抽、再验证、再修复。
5. code/pseudocode grounding：先把 SOP 规则转成可执行伪代码，再生成 action IR。
6. RAG baseline：检索文档片段，让 agent 按 SOP 执行，但不生成结构化 action。

#### 指标

| 阶段 | 指标 |
|---|---|
| SOP 检测 | 文档/片段分类 F1 |
| 步骤抽取 | step precision / recall / F1，排序准确率 |
| 角色/对象抽取 | entity F1，slot filling F1 |
| 控制流 | dependency F1，graph edit distance |
| Action IR | action 名称、目标对象、参数、前置条件、效果的 exact / fuzzy match |
| 证据 | action 是否绑定到正确原文片段的比例 |
| 执行 | task pass rate、tool-call accuracy、invalid-action rate |
| 安全/合规 | 禁止动作率、漏检前置条件率 |
| 多语言 | 中英迁移性能下降幅度 |

#### 具体实验轨道

Track A：英文文本到流程

- 数据集：PET。
- 输出：process graph 和 action candidates。
- 主要指标：entity / relation / control-flow F1。

Track B：中文业务规则流

- 数据集：BREX 或 BPRF。
- 输出：condition-action rules 和 dependencies。
- 主要指标：rule tuple F1 和 dependency F1。

Track C：SOP 到 agent / action 执行

- 数据集：SOPBench 或 SOP-Bench。
- 输出：ontology action IR 和可执行 tool plan。
- 主要指标：verifier pass rate、tool-call precision、precondition/effect correctness。

Track D：多模态 workflow 到 SOP / action

- 数据集：WONDERBREAD。
- 输出：由录制/轨迹生成的 SOP 和 action graph。
- 主要指标：SOP 生成质量、step recall、demo validation F1、action trace 对齐。

Track E：工业图表到 SOP / action

- 数据集：FlowExtract 示例或合成/人工标注的流程图集。
- 输出：graph nodes、edges、decisions、action IR。
- 主要指标：node/edge F1 和 graph topology accuracy。

### 建议模型架构

```text
Document
  -> parser / OCR / layout extractor
  -> chunker with section / table / figure awareness
  -> SOP / procedure detector
  -> ontology-aware extractor
  -> procedural graph builder
  -> verifier / repair loop
  -> action IR generator
  -> rule engine / simulator
  -> human review queue
```

### 关键设计选择

不要训练系统直接输出 “Palantir action” 或 “iDME operation”。先生成平台无关的 action IR。平台专用动作生成应作为最后的编译步骤。

## 两个想法的统一方法

```text
metadata -> ontology backbone
documents/SOPs -> semantic enrichment + procedure graph
procedure graph -> ontology action IR
action IR -> executable operation / workflow / lifecycle transition
```

### 联合假设

H1：元数据派生的本体会通过约束对象类型、状态、参数和角色，提高 SOP 抽取质量。

H2：文档派生的语义增强会比仅元数据本体更能提升检索、QA 和 action 合成效果。

H3：通过显式中间图和 verifier，SOP 到 action 的生成比直接 LLM 生成更少幻觉、更安全。

H4：中文规则流数据与英文流程数据可以共享一个语言无关的 action IR，但抽取 prompt 和实体链接需要语言特化。

## 推荐的第一个实验

先做一个窄而可发表的原型：

题目建议：

Evidence-Grounded SOP-to-Action Extraction with Metadata-Constrained Ontology Enrichment.

最小可行实验：

1. 从元数据构建一个小本体：
   - WorkOrder、Equipment、Operation、Material、InspectionResult、Role、State。
2. 使用 PET 和 BREX：
   - PET 做英文流程抽取。
   - BREX 做中文条件-动作依赖抽取。
3. 生成统一的中间表示：
   - steps、roles、objects、conditions、actions、dependencies、evidence。
4. 加入 ontology 约束：
   - 目标对象必须存在于 ontology 中。
   - action 必须有 actor、precondition、effect 和 evidence。
5. 比较：
   - 直接 LLM
   - schema-constrained LLM
   - ontology-constrained LLM
   - ontology-constrained + verifier / repair
6. 评估：
   - 抽取 F1
   - dependency F1
   - action IR 正确率
   - evidence 正确率
   - verifier pass rate

这比直接解决完整的 BoM / BoP / SysML 增强更可控。

## 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 公开工业 BoM / BoP 数据稀缺 | 难以直接为想法 1 做 benchmark。 | 使用 AAS / OPC UA / SysML 示例并手工标 gold label。 |
| LLM 生成看似合理但无证据的语义 | 可能污染 ontology / action。 | 每条输出都要求 evidence span 和 review status。 |
| 纯文本 ontology 抽取会重复元数据概念 | 造成 ontology 膨胀。 | 文档抽取只作为增强候选，不直接创建正式 class。 |
| SOP 数据集不是工业车间 SOP | 存在领域偏差。 | 使用 SOP-Bench / FlowExtract，并尽量构造小型工业风格内部 benchmark。 |
| 中英 schema 不一致 | 跨语言迁移效果差。 | 使用语言无关 IR，并拆分 lexical / entity-linking 层。 |
| action 生成缺少 simulator 难评估 | 结论会偏弱。 | 使用 SOPBench / SOP-Bench 的可执行 verifier 和简单自定义 simulator。 |

## 最终建议

如果目标是尽快出结果，优先做想法 2。它有公开数据，也更容易做可执行评估。

如果目标是更强的工业本体研究，想法 1 应该作为长期方向，但要把问题表述为“基于证据的元数据本体语义增强”，而不是“直接从文档抽 ontology”。

最强的研究叙事是把两者结合起来：

1. 元数据建立可信的 ontology backbone。
2. 文档通过证据链补充语义增强。
3. SOP 抽取形成 procedural graph。
4. procedural graph 编译成 action IR。
5. action IR 再由 ontology 约束和可执行测试用例验证。

