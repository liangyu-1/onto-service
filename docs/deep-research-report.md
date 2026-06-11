# 从非结构化工业文档抽取 ontology-grounded Action IR 的公开数据集调研

## 核心判断

如果把你的目标定义得很严格——输入是工业 ontology / KG / asset model / process model，加上非结构化或半结构化工业文档；输出是带 action span、actor、target、parameter、precondition/effect、control-flow、ontology grounding id 的完整 Action IR——那么当前**没有一个**公开数据集能一次性把这些维度都覆盖完整。公开资源更现实的使用方式，是把不同数据集按能力拼接成“组合 benchmark”：用 **PET / PAGED** 负责流程逻辑与 control-flow，用 **MyFixit / OMIn** 负责维护维修语域中的 equipment / part / tool / entity，用 **MSPT / PcMSP / ULSA** 负责工艺动作、材料对象和参数类型，用 **MaterioMiner / FlaMBé** 负责 ontology 或 ontology-like grounding。citeturn36view0turn36view1turn9view0turn10view0turn10view1turn15view0turn17view0turn18search0turn19view0turn18search4turn19view1turn25view1turn28view0turn30view0turn30view1

真正“工业 SOP / 作业指导书 / 工艺规程 / 维修手册 + 人工 action annotation + ontology grounding + control-flow”的公开 benchmark 仍然非常稀缺。维护与制造领域公开语料往往要么是**步骤级弱标注或局部标注**，要么是**incident / log / scientific procedure** 而不是标准化的 SOP / work instruction；而 text-to-process-model 方向虽然有 PET 和 PAGED 这类高价值数据集，但语域偏业务流程而非制造现场文档。这个稀缺性在过程抽取文献和维护领域基准构建论文中都被直接指出。citeturn17view0turn9view0turn37search6

对论文二而言，最现实的高质量方案不是“找一个完美数据集”，而是构建一个**分层 benchmark**：主 benchmark 选 3–5 个最接近的公开集合作为多任务基线，附加 1–2 个你自己重标或银标构造的数据切片，专门补齐 precondition/effect/state transition 与 ontology grounding 这两个公开资源最缺的维度。citeturn9view0turn25view1turn28view0turn15view1

## 数据集详评矩阵

下表只收录我认为**高置信、可获取、且确实能被训练/验证/组 benchmark** 的公开资源。表中“未显式提供”表示官方页面或论文没有清楚写出，我不做猜测。

| Dataset | 领域 | 公开/下载 | 许可 | 规模/格式 | Split | 人工标注 | 标注内容 | Action | Actor / Target / Param | Pre / Eff | Flow | Ontology / KG / schema | 适配结论 | 主要缺陷 | 资源 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MyFixit | 维修手册 / repair manuals | 是；GitHub 直接下载 JSON | CC BY-NC-SA 3.0 | 31,601 manuals / 15 类；其中人工标注部分为 Mac Laptop 1,497 manuals、36,659 steps；JSON、column corpus | 未见官方 split | 是 | 每步所需工具、拆解部件、removal verbs | 是；step span 明确，verb span 明确 | Actor 基本隐含；Target/part 强；Parameter 弱 | 否 | 否 | 否 | **高**；最接近“maintenance procedure + equipment/action/object annotation” | 只有 1 个主类目有完整人工标注；无 control-flow、无 grounding | citeturn10view0turn10view1turn14view2turn13view0 |
| PET | text-to-process-model / BPMN 风格流程文本 | 是；HF 下载 v1.0.1 | 数据集页面公开，但单独数据许可未显式写清；论文为 CC BY 4.0 | 45 个 business process narrative docs；INCEpTION schema / HF dataset | 官方页面未见固定 split | 是 | activities、gateways、actors、flow information、activity data 等 | 是 | Actor 强；Target/Activity Data 有；Parameter/condition 有限 | 部分；有 condition / constraint 语义，但不是 state transition gold | **是** | BPMN/流程 schema 强 | **高**；最适合做 control-flow / process graph 主 benchmark | 非工业制造语域；样本偏小 | citeturn36view0turn36view1 |
| PAGED | procedural document → graph | 是；GitHub 下载 | 基于原流程图集合的 CC BY-NC-SA 3.0 衍生使用；数据集本身公开 | 3,394 document-graph pairs；图用 DOT-like 表示 | **有**；train/val/test = 3:1:2 | 不是传统人工逐条标注；底层图来自高质量流程模型，文档经生成与人工评估校验 | actors、actions、constraints、XOR/OR/AND gateways、constraint flow | 是 | Actor 有；Target/parameter 不系统 | Constraint 有；state transition 仍弱 | **是** | 流程图 schema 强 | **中高**；非常适合训练/评估 control-flow 与 constraint extraction | 语料为生成式程序文档，不是工业原始 SOP；对象/参数层次不够细 | citeturn9view0turn38search7 |
| ULSA / synthesis-action-retriever | 无机材料合成程序 | 是；GitHub data 直接下载 | 仓库页面未见明确 licence | 论文报告 535 paragraphs 上 3040 条标注句/动作单元；JSON | 未显式提供固定 split | 是 | 8 类统一 action terms；脚本可抽 temp/time/environment 并构图 | **是** | Target/subject 与参数主要靠规则抽取；Actor 无 | 否 | 部分；可构 flowchart，但作者显式采用线性顺序假设 | **有**；ULSA 是 ontology-like action schema | **高**；非常适合 action type 和 parameter schema 迁移 | 金标主要覆盖 action，目标材料/属性并非完整联合金标 | citeturn25view1turn25view0 |
| Materials Science Procedural Text Corpus | 材料合成 procedure | 是；GitHub BRAT | MIT | 230 synthesis procedures；BRAT standoff；含 NER / frame extraction 划分文件 | **有**；NER 与 supervised frame extraction 有 train/dev/test | 是；领域专家 | synthesis operations、typed arguments、labeled graph edges | **是** | Target/material/parameter 强；Actor 无 | 否 | 部分；有 labeled graph，但非完整 branching workflow | schema 强，ontology 弱 | **高**；最适合做 action-object-parameter 结构抽取 | 不是工业手册；不含 ontology grounding IDs | citeturn18search0turn19view0 |
| PcMSP | 多晶材料合成 procedure | 是；GitHub JSON / original | MIT | 305 open-access articles；repo 含 mat_train/dev/test，且因 licence limit 与论文数字略有差异 | **有** | 是；两阶段人工标注 | 句子分类、实体识别、关系分类、joint extraction，用于 action graph extraction | 部分；偏 action graph 的实体/关系层 | Target/material/parameter 有；Actor 弱 | 否 | 否 | schema 强，ontology 弱 | **中高**；适合做 scientific procedure 的实体-关系层 benchmark | 主要是句内实体/关系，不是完整 step-flow 图 | citeturn18search4turn19view1 |
| OMIn | 运行维护 incident / maintenance intelligence | 是；GitHub 或 Zenodo | 仓库页面未见明确 licence | 2,748 short docs；100 条 gold-standard records；文本 + structured fields | 无典型 train/dev/test；100 gold sample 用于评测 | 是 | NER、coreference、NEL；UTFAA GS 509 entities；NEL 到 Wikidata QIDs | 否；不是步骤语料 | Actor/asset/system/entity 强；Target 强；Parameter 一般 | 否 | 否 | **有**；NEL 到 Wikidata | **中**；适合 maintenance entity grounding / domain adaptation | 不是 procedure；无 action-flow gold；无 RE gold standard | citeturn15view0turn17view0turn16view0 |
| MaterioMiner | 材料力学 ontology-grounded NER | 是；Fordatis / GitLab | CC BY 4.0 | 4 篇 OA 论文；2191 entities；179 classes；CoNLL/TSV/TTL ontology | 可构成 FG-NER / CG-NER benchmark；官方未按常规 train/dev/test 强调 | 是；3 名标注者 | 细粒度 ontology-linked entity classes；linked ontology | 否 | Target/entity 丰富；参数和材料属性强；Actor 无 | 否 | 否 | **有**；materials mechanics ontology + IRIs | **中**；最适合补“ontology grounding / schema-conformal extraction” | 几乎没有 procedural action / control-flow | citeturn28view0 |
| Text-mined dataset of inorganic materials synthesis recipes | 固相合成“工艺配方”银标 | 是；GitHub 下载 .json.xz | 论文 CC BY 4.0；仓库本身未单列 | 论文版 19,488 synthesis entries / 53,538 paragraphs；GitHub 更新版 31,782 solid-state reactions + 9,518 sol-gel | 无标准 split | 不是逐条金标；自动抽取，系统级验证 | target、starting compounds、operations、conditions、reaction equation | 部分；有 operation sequence/conditions | Target/parameter 强；Actor 无 | 否 | 线性 procedure，非 branching | schema 强，ontology 弱 | **中**；很适合作银标预训练或 distant supervision | 自动抽取噪声不可忽略；不是人工 gold benchmark | citeturn23search0turn22view0 |
| Dataset of solution-based inorganic materials synthesis procedures | 溶液法合成“工艺配方”银标 | 是；GitHub / figshare 下载 JSON | CC BY 4.0 | 35,675 procedures；每条含 precursor、target、quantities、actions、attributes、reaction formula | 无标准 split | 不是逐条金标；自动抽取并人工检查系统质量 | quantities、actions、attributes、reaction formula | 部分 | Target/parameter 很强；Actor 无 | 否 | 线性 procedure，非 branching | ULSA 风格 action schema 关联较强，但非逐条 grounding | **中**；非常适合 parameter/value 抽取预训练 | 自动抽取；非工业 SOP；无 control-flow gold | citeturn20view0turn19view2turn21view2turn18search14 |
| FlaMBé | 生物医学 workflow / methods | 是；GitHub / Zenodo / HF | CC BY 4.0 | 55 full papers + 1,195 abstracts，近 710k tokens；workflow 约 400 relations | 可按发布文件直接使用；未强调单一官方 split | 是；专家整理 | tissue/tool NER、NED、workflow tuples、tool-context、sequence | 部分；workflow tuple 级 | Actor 弱；Target/tool/context 强；Parameter 一般 | 否 | **是**；sequence file 明确工具对序列 | **有**；NCI Thesaurus IDs、标准工具名 | **中**；适合 ontology grounding + workflow relation 迁移 | 生物医学语域，与工业手册差距较大 | citeturn30view0turn30view1turn29search6 |
| CLIP | 临床出院行动项 | **部分公开**；PhysioNet credentialed access | PhysioNet / MIMIC 合规访问 | 718 discharge summaries，107,494 sentences；character-level JSON + sentence CSV | **有**；518/100/100 | 是；4 physicians + 1 resident | 7 类 action item，character-level spans 与 sentence labels | **是** | Actor 隐含；Target/action item 强；Parameter 一般 | 否 | 否 | 否 | **中**；适合 span-based action extraction 迁移 | 不是 procedural flow；医疗访问门槛高 | citeturn42view0turn31search0 |
| English Recipe Flow Graph Corpus | 烹饪流程图 | 论文公开；稳定数据入口在论文页未显式给出 | 论文公开；单独数据许可未显式给出 | 300 recipes；r-NE + recipe flow graph | 未见官方 split 说明 | 是 | 实体、工具、食材、中间产物与 flow graph | **是** | Target/tool/product 强；Actor 弱；Parameter 一般 | 否 | **是** | schema 强，ontology 弱 | **中**；适合 step-graph / object interaction 迁移 | 领域过于日常；下载入口不如 GitHub 数据集稳定 | citeturn40view0 |
| wikiHow-FG Corpus | 开放域 how-to flow graph | 是；GitHub JSON | LICENSE 存在，但页面未解析出具体条款 | 120 articles / 4 domains；steps + labeled flows + URL | 未显式官方 split | 是 | token-level step 表示、edge labels | **是** | Actor/target 一般；Parameter 弱 | 否 | **是** | schema 强，ontology 弱 | **中**；适合 open-domain instruction → flow graph 迁移 | 非工业；规模不大；无 grounding | citeturn39search0turn40view1 |

## 重点方向结论与 benchmark 建议

你特别关心的几个问题，可以比较明确地归纳如下。

在“**工业 SOP + action annotation**”这一点上，**MyFixit 是目前最接近公开可用主 benchmark 的资源**，但它更像维修拆解手册，而不是工厂现场 SOP；最近的 **SOP-Bench** 确实针对复杂工业 SOP、覆盖多个行业且任务量很大，但它面向的是 agent 执行评测，核心是任务、API 和 expected behavior，不是 span-level IE / grounding benchmark，因此更适合作为**压力测试或下游 agent evaluation**，不适合作为你的 Action IR 主训练集。citeturn10view0turn10view1turn35view0turn35view1

在“**work instruction + process graph / text-to-BPMN / text-to-process-model**”这条线上，**PET 和 PAGED 是最值得优先纳入的两套公开资源**。PET 的价值在于它是真正面向 process extraction from text 的人工标注语料，直接覆盖 activities、actors、gateways 和 flows；PAGED 的价值在于它把**sequential actions、non-sequential actions、constraints** 做成了大规模标准 benchmark，并且公开了 train/validation/test。对于你的论文二，二者非常适合作为 control-flow、gateway、constraint extraction 的主评测面。citeturn36view0turn36view1turn9view0

在“**manufacturing process plan + operation sequence / routing sheet / operation sheet**”这一点上，公开文本 benchmark 反而是**最大缺口**。我没有找到一个同时公开原始 routing sheet/operation sheet 文本、人工 action/object 标注、正式 split、并且可直接映射到工艺 ontology 的成熟 benchmark。当前最接近的替代品，是 **ULSA、MSPT、PcMSP** 这条“材料/合成工艺程序”路线，以及 **Ceder 组的固相/溶液法 synthesis recipes** 这类大规模银标 recipe 数据。它们对“operation type、material/object、parameter/value、步骤顺序”很有帮助，但距离工业 route sheet 仍有语域差距。citeturn25view1turn18search0turn19view0turn18search4turn19view1turn22view0turn20view0

在“**maintenance procedure + equipment/action/object annotations**”这一点上，公开资源呈现出明显分裂：**MyFixit** 提供的是 procedure / step 维度的工具与部件标注，而 **OMIn** 提供的是 maintenance/operations 语域的 entity linking 与 domain NER/NEL，但不是 procedure。二者结合起来，恰好能形成“步骤抽取 + 设备/部件 grounding”的组合。citeturn10view0turn10view1turn15view0turn17view0

在“**ontology-grounded procedural extraction**”这一点上，最接近但仍不完整的公开资源是 **MaterioMiner、OMIn、FlaMBé 和 ULSA**。MaterioMiner 把材料力学文本与 ontology classes/IRIs 连起来；OMIn 把 maintenance entities 连到 Wikidata QIDs；FlaMBé 把 tissue/cell type 连到 NCI Thesaurus，并带 workflow tuples；ULSA 则提供了一个 ontology-like 的 action vocabulary。问题在于，它们分别覆盖的是**grounding、NER/NEL、workflow、action schema** 的不同切面，没有谁同时覆盖完整 industrial Action IR。citeturn28view0turn15view0turn17view0turn30view0turn30view1turn25view1

真正最稀缺的是 **preconditions / effects / state transitions**。公开资源里，这一层通常不是显式金标；PAGED 给了 constraints 和 gateway logic，但不是状态转移；Visual Recipe Flow 是少数明确把 object state changes 与 flow graph 联结起来的公开数据，但它是烹饪多模态数据，不能直接充当工业 benchmark，只能给你“状态变化建模”的思想与迁移信号。citeturn9view0turn41view0

如果你要写论文二，我会推荐一个非常务实的 benchmark 组装法：主 benchmark 选 **MyFixit + PET + PAGED + MSPT/PcMSP + ULSA**；辅助 grounding 选 **OMIn + MaterioMiner**；再从你自己的工业 SOP / 作业指导书中抽样，补一个**小而高质量的人工 test set**，专门标注 precondition / effect / state transition / ontology grounding ids。这样做比等待一个“完美公开数据集”更现实，也更容易在论文里说清楚每一部分能力到底由哪类数据支撑。citeturn10view0turn36view0turn9view0turn18search0turn19view0turn18search4turn19view1turn25view1turn15view0turn28view0

一个需要明确说明的限制是：若干数据集的**下载入口或 licence 页面并不完全规范**，尤其是 ULSA、PET、OMIn、wikiHow-FG 这类仓库/站点型资源；因此论文里最好把“官方公开”、“需 credentialed access”、“许可未显式声明”分开写，避免给审稿人留下数据合规性模糊的印象。citeturn25view0turn36view0turn15view0turn40view1turn42view0

## 最适合论文二直接使用的数据集

| Dataset | Domain | Public? | Annotation | Ontology/KG? | Action/Step? | Control-flow? | License | Suitability | Link |
|---|---|---|---|---|---|---|---|---|---|
| MyFixit | 维修手册 / repair manuals | 是 | step 级工具、部件、removal verbs，人标 | 否 | 是 | 否 | CC BY-NC-SA 3.0 | **High**；最像“maintenance procedure + action/object” | citeturn10view0turn10view1turn13view0 |
| PET | process description → BPMN-like elements | 是 | activities、actors、gateways、flow，人标 | 流程 schema 强 | 是 | **是** | 数据许可未显式清楚；论文公开 | **High**；control-flow 主 benchmark | citeturn36view0turn36view1 |
| PAGED | procedural document → graph | 是 | actors、actions、constraints、gateways、paired graph | 流程 schema 强 | 是 | **是** | 公开；基于原流程图集合可用 | **High**；control-flow / constraint 最强，但非真实工业文本 | citeturn9view0turn38search7 |
| Materials Science Procedural Text Corpus | 材料合成 procedure | 是 | operation、typed arguments、relations，人标 | schema 有，ontology 弱 | **是** | 部分 | MIT | **High**；action-object-parameter 抽取很强 | citeturn18search0turn19view0 |
| ULSA | 无机合成 procedure | 是 | 8 类 action schema；配套脚本抽 time/temp/env | **有**；ontology-like action schema | **是** | 部分 | 未显式声明 | **High**；最适合 action type / parameter schema | citeturn25view1turn25view0 |
| PcMSP | 多晶材料合成 | 是 | sentence / entity / relation / action graph，人标 | schema 有，ontology 弱 | 部分 | 否 | MIT | **Medium**；适合实体-关系层，不足以单独做完整 IR | citeturn18search4turn19view1 |

## 可迁移使用的数据集

| Dataset | Original Domain | Useful Signal | How to Adapt | Limitation | Priority |
|---|---|---|---|---|---|
| OMIn | 航空运行维护 incident reports | 维护域 entity、system/component mentions、Wikidata grounding | 用于 equipment / component linking、domain adaptation、maintenance KG grounding | 不是 procedure；无 action-flow gold | Medium citeturn15view0turn17view0 |
| MaterioMiner | 材料力学论文 | ontology-grounded fine-grained entities、IRIs | 用于 ontology grounding 任务、schema-constrained NER/NEL | 几乎不含 procedural action | Medium citeturn28view0 |
| Text-mined dataset of inorganic materials synthesis recipes | 固相合成文献 | operation、condition、reaction equation 大规模银标 | 作为 weak supervision / pretraining，对 operation-resource-parameter 有帮助 | 自动抽取噪声；非工业手册 | Medium citeturn23search0turn22view0 |
| Dataset of solution-based inorganic materials synthesis procedures | 溶液法合成文献 | quantities、actions、attributes、reaction formula | 作为 parameter/value 抽取与 structured decoding 预训练语料 | 自动抽取；没有显式 control-flow gold | Medium citeturn20view0turn19view2turn21view2 |
| FlaMBé | 单细胞研究 workflow | NER + NED + workflow tuples + sequence | 迁移到 text-to-workflow、tool-context relation、ontology grounding | 生物医学语域差距大 | Medium citeturn30view0turn30view1 |
| CLIP | 临床 discharge action items | character-level action spans；7 类 action items；官方 split | 用于 action span 抽取、sentence / span multi-label 训练 | 非 procedural flow；需 credentialed access | Medium citeturn42view0turn31search0 |
| English Recipe Flow Graph Corpus | cooking recipes | step graph、tool/ingredient/product interaction | 迁移到 step-to-graph 与 object-flow 任务 | 领域通用；下载入口不够稳健 | Low-Medium citeturn40view0 |
| wikiHow-FG Corpus | open-domain how-to | flow graph、labeled edges、step tokens | 迁移到开放域指令 → flow graph；做零样本/少样本结构先验 | 非工业；规模小；无 grounding | Low-Medium citeturn39search0turn40view1 |

## 不建议使用或只能做背景的数据集

| Dataset | Reason | Risk |
|---|---|---|
| Friedrich 47 text-model pairs | 经典但很早；只有 47 对 text-model pairs，且现代可重用的细粒度标注与发布形态不如 PET | 容易被审稿人认为 benchmark 过小、过旧；更适合作历史背景而非主评测 citeturn37search17turn37search5 |
| Epure 2015 dataset | PAGED 对比表显示规模 34，且**非公开** | 不可复现，难以作为论文二 benchmark citeturn9view0 |
| Ferreira 2017 dataset | PAGED 对比表显示规模 56，且**非公开** | 同样存在可得性与复现风险 citeturn9view0 |
| Kuniyoshi all-solid-state battery corpus | 论文有 243 papers 的 synthesis flow graphs，但后续文献明确指出其 corpus **不公开** | 即使任务定义很接近，也无法作为公共 benchmark 主体 citeturn27search0turn27search7 |
| SOP-Bench | 行业 SOP 很强，但它是 agent execution benchmark，不是文本 IE / Action IR 金标语料；而且为 synthetic/highly controlled task generation | 若拿来当 IE benchmark，会被质疑 task mismatch；更适合作为下游 agent 压测 | citeturn35view0turn35view1 |

