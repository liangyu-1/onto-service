from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from build_action_layer_ppt import (
    AMBER, BG, BLUE, GREEN, INK, LINE, MUTED, NAVY, PALE_AMBER,
    PALE_BLUE, PALE_RED, PALE_TEAL, RED, TEAL, WHITE, W, H,
    add_badge, add_card, add_footer, add_header, add_rich_text,
    add_text, line, rect, set_run,
)


OUT = __import__("pathlib").Path(__file__).with_name("action_layer_research_plan_zh.pptx")


def new_slide(prs, title=None, subtitle=None, section=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    if title:
        add_header(slide, title, subtitle, section)
    add_footer(slide, len(prs.slides))
    return slide


def add_table(slide, x, y, w, h, headers, rows, widths=None, font_size=12):
    table = slide.shapes.add_table(
        len(rows) + 1, len(headers), Inches(x), Inches(y), Inches(w), Inches(h)
    ).table
    if widths:
        for col, width in zip(table.columns, widths):
            col.width = Inches(width)
    for c, value in enumerate(headers):
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.text = value
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            for run in p.runs:
                set_run(run, font_size, True, WHITE)
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r % 2 else PALE_BLUE
            cell.text = str(value)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.04)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if c != 1 else PP_ALIGN.CENTER
                for run in p.runs:
                    set_run(run, font_size, c == 0, INK)
    return table


def stage(slide, x, y, w, number, title, body, color):
    rect(slide, x, y, w, 1.45, WHITE, color)
    add_badge(slide, x + 0.16, y + 0.14, 0.55, number, color)
    add_text(slide, x + 0.78, y + 0.14, w - 0.92, 0.35, title, 15, True, NAVY)
    add_text(slide, x + 0.18, y + 0.68, w - 0.36, 0.52, body, 12, False, MUTED, PP_ALIGN.CENTER)


def finalize_main_deck(prs, order):
    """Keep and reorder the advisor-facing main deck, then refresh page numbers."""
    slide_ids = list(prs.slides._sldIdLst)
    keep = set(order)
    for index, slide_id in enumerate(slide_ids):
        if index not in keep:
            prs.slides._sldIdLst.remove(slide_id)
            prs.part.drop_rel(slide_id.rId)
    remaining = list(prs.slides._sldIdLst)
    by_original_index = {
        original_index: slide_id
        for original_index, slide_id in zip(
            [i for i in range(len(slide_ids)) if i in keep],
            remaining,
        )
    }
    for slide_id in list(prs.slides._sldIdLst):
        prs.slides._sldIdLst.remove(slide_id)
    for original_index in order:
        prs.slides._sldIdLst.append(by_original_index[original_index])

    for page_number, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if (
                getattr(shape, "has_text_frame", False)
                and shape.left >= Inches(11.5)
                and shape.top >= Inches(6.3)
            ):
                shape.text_frame.paragraphs[0].text = f"{page_number:02d}"
                for run in shape.text_frame.paragraphs[0].runs:
                    set_run(run, 20 if page_number == 1 else 9, True, TEAL if page_number == 1 else MUTED)


def build():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    prs.core_properties.title = "面向本体动作层的研究：协作构建、文档抽取与智能体执行"
    prs.core_properties.subject = "三篇论文研究体系与实验计划"

    # 1
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    rect(slide, 0, 0, 0.18, 7.5, TEAL, TEAL, False)
    add_badge(slide, 0.85, 0.72, 1.65, "RESEARCH PLAN", TEAL)
    add_text(slide, 0.85, 1.42, 11.4, 1.2, "面向本体动作层的研究", 36, True, WHITE)
    add_text(slide, 0.87, 2.6, 11.0, 0.65, "协作构建 · 文档抽取 · 智能体理解与规划", 24, False, __import__("pptx").dml.color.RGBColor(198, 216, 228))
    line(slide, 0.87, 3.55, 5.7, 3.55, TEAL, 3)
    add_text(slide, 0.87, 4.0, 10.8, 0.8,
             "研究目标：构建可协作生成、从文档扩充、可供 Agent 理解与执行的本体 Action Layer",
             19, True, WHITE)
    add_text(slide, 0.87, 6.55, 7.5, 0.32, "导师汇报 · 2026年6月", 12, False,
             __import__("pptx").dml.color.RGBColor(170, 194, 210))
    add_text(slide, 11.7, 6.48, 0.75, 0.42, "01", 20, True, TEAL, PP_ALIGN.RIGHT)

    # Current research basis
    slide = new_slide(
        prs,
        "当前研究基础",
        "在明确研究问题和总体框架后，说明已有实现、初步证据和待决策事项",
        "CURRENT STATUS",
    )
    add_card(slide, 0.72, 1.85, 3.65, 4.55, "已经完成", [
        "Retail Action IR 与 ActionBank",
        "IR 编译器、运行状态、admissibility、repair",
        "Paper 2：40 篇内部试验",
        "Paper 1：已有方法文档与 Kyuubi 工作流设计",
    ], TEAL, 15)
    add_card(slide, 4.83, 1.85, 3.65, 4.55, "当前证据", [
        "Paper 3：44.9% → 55.7%",
        "但 task-level p = 0.109",
        "Paper 2：Ours 并非全面最优",
        "Paper 1：案例数字尚缺可复现 benchmark",
    ], BLUE, 15)
    add_card(slide, 8.94, 1.85, 3.65, 4.55, "需要决策", [
        "Paper 1 是否值得独立投入？",
        "人工金标选择哪个领域？",
        "能否协调 2–3 名专家？",
        "Paper 3 达到何种门槛再扩域？",
    ], AMBER, 15)

    # 3 Domestic and international research status
    slide = new_slide(
        prs,
        "国内外研究现状",
        "合并比较需求工程、动作抽取、运行约束与国内产业实践；六类内容完整保留",
        "RELATED WORK",
    )
    rows = [
        ("国外", "本体构建与协作演化",
         "DILIGENT / NeOn：分布式贡献与版本演化；HyWay / IDEA2：LLM + 专家验证与共识；CQ / ORSD：需求与范围验证",
         "缺动作 Patch、执行验证和运行反馈重验证"),
        ("国外", "程序文档与流程抽取",
         "Text2Event / PET：事件、参与者和流程；PAGED / Universal Prompting：程序图；OMPD / NL2ProcessOps：工业程序与执行连接",
         "缺已有本体 grounding 与完整 Action IR"),
        ("国外", "工具智能体与运行约束",
         "ToolRerank / ToolLLM：工具选择；tau-bench / ToolSandbox / WorkArena：有状态评测；AgentSpec / Progent：运行规则",
         "缺本体状态驱动校验、修复和解释"),
        ("国内", "工业本体与知识图谱",
         "描述设备、部件、工艺和故障；用于查询、诊断、推荐和数据治理",
         "补动作对象、角色、状态和效果；公开表示与实验"),
        ("国内", "SOP / 流程数字化",
         "输入工艺文档、维修手册和业务规程；输出实体关系、步骤、BPMN 或流程图",
         "补 ontology IDs、evidence、unresolved；Full IR 金标"),
        ("国内", "行业智能体与工具调用",
         "采用 RAG、工具编排、工作流和平台规则；规则多位于 Prompt、代码或配置",
         "规则来源于 Action IR；schema / ontology_full 对照"),
    ]
    add_table(
        slide, 0.34, 1.62, 12.65, 4.98,
        ["区域", "研究方向", "已有代表工作 / 实践", "本研究切入点"],
        rows, [0.72, 2.45, 5.72, 3.76], 9,
    )
    add_text(
        slide, 0.95, 6.68, 11.45, 0.26,
        "共同缺口：缺少公开 Action IR 契约，以及分别覆盖协作构建、文档抽取和 Agent 执行的可复现实验。",
        12, True, RED, PP_ALIGN.CENTER,
    )

    # 4 Palantir as the primary industrial reference
    slide = new_slide(
        prs,
        "Palantir：最重要的产业参照",
        "其 Ontology 已把语义模型与可执行动作统一到 operational layer；本研究必须正面说明继承点与学术增量",
        "INDUSTRY REFERENCE",
    )
    add_card(slide, 0.58, 1.72, 3.82, 3.72, "Semantic Layer", [
        "Object Types / Properties / Link Types",
        "连接数据、模型与现实业务对象",
        "可表达设备、产品、订单和交易",
        "安全、权限和变更治理贯穿对象层",
    ], BLUE, 13)
    add_card(slide, 4.76, 1.72, 3.82, 3.72, "Kinetic Layer", [
        "Action Types：一次事务修改对象、属性和链接",
        "Parameters + Rules + Submission Criteria",
        "Functions 承载可演化业务逻辑",
        "Side Effects：通知、Webhook 等外部效果",
    ], TEAL, 13)
    add_card(slide, 8.94, 1.72, 3.82, 3.72, "Operational Governance", [
        "同一动作逻辑在多个应用中复用",
        "Permissions、Monitoring、Metrics",
        "Action Log 支持审计",
        "Undo / Revert 与 Action Type branching",
    ], AMBER, 13)
    rect(slide, 0.72, 5.72, 12.0, 1.02, PALE_RED, RED)
    add_text(slide, 0.95, 5.85, 2.0, 0.28, "本研究不能声称", 13, True, RED)
    add_text(
        slide, 2.68, 5.82, 3.55, 0.62,
        "首次在本体中定义动作、参数、规则、效果或审计。",
        12, False, INK, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE,
    )
    add_text(slide, 6.25, 5.85, 1.75, 0.28, "真正学术增量", 13, True, TEAL)
    add_text(
        slide, 7.82, 5.76, 4.55, 0.72,
        "公开 Action IR；从文档和多源证据生成；协作验证与演化；在 tau2 等 benchmark 上量化 Agent 执行收益。",
        12, False, INK, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE,
    )

    # 5 Dissertation outline
    slide = new_slide(prs, "大论文框架", "每章必须有明确输入、输出和证据，不能只靠共享术语形成体系", "THESIS OUTLINE")
    items = [
        ("01", "绪论", "问题、研究目标与总体框架", TEAL),
        ("02", "Action IR", "字段契约、编译规则、跨域边界", BLUE),
        ("03", "协作式数据本体生成", "Live Schema → Versioned Data Ontology", GREEN),
        ("04", "文档抽取", "Document + Ontology → IR Patch", AMBER),
        ("05", "运行时语义", "ActionBank + State → Execute / Repair", RED),
        ("06", "统一评估", "质量、成本、成功率与运行开销", TEAL),
    ]
    for i, (num, title, body, color) in enumerate(items):
        row, col = divmod(i, 2)
        x = 0.8 + col * 6.25
        y = 1.78 + row * 1.55
        rect(slide, x, y, 5.75, 1.15, WHITE, color)
        add_badge(slide, x + 0.22, y + 0.18, 0.64, num, color)
        add_text(slide, x + 1.05, y + 0.16, 2.25, 0.35, title, 16, True, NAVY)
        add_text(slide, x + 1.05, y + 0.58, 4.3, 0.32, body, 13, False, MUTED)

    # Overall dissertation question
    slide = new_slide(
        prs,
        "核心研究问题",
        "如何把以静态概念描述为主的领域本体，扩展为可构建、可演化、可执行的动作知识层？",
        "PROBLEM",
    )
    add_card(slide, 0.72, 1.88, 3.55, 3.8, "现有表示断裂", [
        "本体描述对象、属性和关系",
        "程序文档描述操作步骤和条件",
        "API Schema 描述调用接口",
        "Agent 运行时维护临时状态",
    ], BLUE, 17)
    add_text(slide, 4.4, 3.22, 0.65, 0.45, "→", 30, True, TEAL, PP_ALIGN.CENTER)
    add_card(slide, 5.1, 1.88, 3.55, 3.8, "Action Layer 要统一", [
        "动作作用对象和参数角色",
        "前置状态、约束和执行效果",
        "文档证据与本体 grounding",
        "版本演化与运行反馈",
    ], TEAL, 16)
    add_text(slide, 8.78, 3.22, 0.65, 0.45, "→", 30, True, AMBER, PP_ALIGN.CENTER)
    add_card(slide, 9.48, 1.88, 3.15, 3.8, "三个研究问题", [
        "如何协作构建和演化？",
        "如何从文档获取？",
        "如何供 Agent 理解与执行？",
        "三者如何形成递进链条？",
    ], AMBER, 16)
    rect(slide, 1.35, 6.02, 10.6, 0.55, PALE_RED, RED)
    add_text(slide, 1.55, 6.15, 10.2, 0.28,
             "大论文主线：动作知识的表示、获取、演化与运行时使用，而不是单一 benchmark 的安全约束。",
             15, True, RED, PP_ALIGN.CENTER)

    # 4 What is Action IR
    slide = new_slide(prs, "统一表示：Action IR",
                      "IR = Intermediate Representation，不是简单 JSON，也不是新的本体副本", "ACTION IR")
    add_card(slide, 0.72, 2.0, 3.25, 3.25, "上游：文档语言", [
        "自然语言步骤",
        "表格、标题、条件句",
        "异常与安全说明",
    ], TEAL, 16)
    add_text(slide, 4.05, 3.16, 0.6, 0.45, "→", 28, True, NAVY, PP_ALIGN.CENTER)
    rect(slide, 4.72, 2.0, 3.9, 3.25, NAVY, NAVY)
    add_text(slide, 4.98, 2.55, 3.38, 0.55, "Canonical Action IR", 23, True, WHITE, PP_ALIGN.CENTER)
    add_text(slide, 5.08, 3.32, 3.18, 1.05,
             "动作身份 + 对象绑定\n参数角色 + 状态语义\n约束 + 流程 + 证据",
             16, False, WHITE, PP_ALIGN.CENTER)
    add_text(slide, 8.72, 3.16, 0.6, 0.45, "→", 28, True, NAVY, PP_ALIGN.CENTER)
    add_card(slide, 9.38, 2.0, 3.25, 3.25, "下游：任务投影", [
        "Action IR Patch",
        "Runtime ActionBank",
        "Procedure Graph",
    ], BLUE, 16)
    add_text(slide, 1.25, 5.88, 10.85, 0.55,
             "核心作用：保持文档证据、本体语义和运行时工具之间可追踪、可验证的映射。",
             16, True, TEAL, PP_ALIGN.CENTER)

    # 5 Schema
    slide = new_slide(prs, "Action IR 语义结构", "九个语义层区分核心字段与可选字段", "ACTION IR")
    layers = [
        ("Identity", "id / type / kind", BLUE),
        ("Actor", "role / permission", GREEN),
        ("Target", "object type / binding", TEAL),
        ("Parameters", "type / required / role", AMBER),
        ("State", "precondition / effect", RED),
        ("Constraints", "policy / confirmation", BLUE),
        ("Workflow", "previous / next / branch", GREEN),
        ("Grounding", "ontology IDs", TEAL),
        ("Evidence", "document / span / provenance", AMBER),
    ]
    for i, (title, body, color) in enumerate(layers):
        row, col = divmod(i, 3)
        x = 0.75 + col * 4.18
        y = 1.82 + row * 1.55
        rect(slide, x, y, 3.78, 1.15, WHITE, color)
        add_badge(slide, x + 0.16, y + 0.17, 1.12, title, color)
        add_text(slide, x + 1.43, y + 0.21, 2.12, 0.58, body, 14, False, INK, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    rect(slide, 1.2, 6.48, 10.9, 0.34, PALE_AMBER, AMBER)
    add_text(slide, 1.4, 6.51, 10.5, 0.24,
             "设计原则：缺失字段显式 unresolved；不能用 LLM 猜测替代原始证据。",
             12, True, AMBER, PP_ALIGN.CENTER)

    # 6 Worked example
    slide = new_slide(prs, "Action IR 示例",
                      "示例来自当前 retail_action_ir.json，展示它比 API Schema 多表达什么", "ACTION IR")
    add_card(slide, 0.68, 1.82, 3.2, 4.75, "工具 Schema 看到的内容", [
        "tool: return_delivered_order_items",
        "order_id: string",
        "item_ids: array<string>",
        "payment_method_id: string",
    ], BLUE, 15)
    add_text(slide, 3.98, 3.55, 0.55, 0.45, "+", 28, True, TEAL, PP_ALIGN.CENTER)
    add_card(slide, 4.62, 1.82, 3.85, 4.75, "Action IR 增加的语义", [
        "type = OrderReturn；target = Order",
        "item_ids 的角色是 source_items",
        "precondition: order.status = delivered",
        "constraints: authenticated + confirmed",
        "只能对同一订单执行一次最终动作",
        "引用必须属于当前订单和支付方式",
    ], TEAL, 14)
    add_text(slide, 8.58, 3.55, 0.55, 0.45, "→", 28, True, AMBER, PP_ALIGN.CENTER)
    add_card(slide, 9.22, 1.82, 3.4, 4.75, "可计算结果", [
        "状态迁移：delivered → return requested",
        "Grounding：映射到 ontology action/type/property IDs",
        "Evidence：保留 policy 原文",
        "Runtime：确定性投影为工具调用",
    ], AMBER, 14)

    # 7 Lifecycle
    slide = new_slide(prs, "从数据本体到 Action Layer", "Paper 1 提供对象/关系基础；Paper 2、3 负责动作知识的获取与运行使用", "ACTION IR")
    steps = [
        ("1", "Live Schema", "Paper 1：对象/字段/候选关系", TEAL),
        ("2", "数据本体", "采样验证 + 共识 + 演化", BLUE),
        ("3", "动作抽取", "Paper 2：Document → Action IR", AMBER),
        ("4", "运行投影", "Paper 3：IR → ActionBank", GREEN),
        ("5", "执行反馈", "violation / drift → revalidation", RED),
    ]
    for i, args in enumerate(steps):
        x = 0.55 + i * 2.56
        stage(slide, x, 2.15, 2.22, *args)
        if i < 4:
            line(slide, x + 2.24, 2.88, x + 2.5, 2.88, args[-1], 2.2, True)
    add_card(slide, 1.0, 4.55, 5.35, 1.45, "当前已落地", [
        "Paper 3 的 retail_action_ir.json → compiler → Agent",
    ], TEAL, 14)
    add_card(slide, 6.98, 4.55, 5.35, 1.45, "尚缺的闭环", [
        "Paper 1 工程化、Paper 2 金标，以及基础本体与 Action IR 的真实连接",
    ], BLUE, 14)

    # 8 Dataset audit
    slide = new_slide(prs, "数据可用性审计",
                      "当前四个 processed JSONL 的 annotations 均为空，必须回到 raw 官方标注重新转换", "DATA")
    rows = [
        ("MyFixit", "部分可用", "1,497 Mac manuals / 36,659 steps 人标", "Paper 2: action/part/tool", "其余类别无人工标注"),
        ("MSPT", "可用", "230 篇 BRAT + 官方 split", "Paper 2: operation/material/argument", "缺 flow 与 ontology IDs"),
        ("PET", "只作测试", "45 篇 expert process annotation", "Paper 2: actor/gateway/flow", "test-only，不能训练"),
        ("OMIn", "辅助可用", "gold 为 NER/CR/NEL", "Paper 2: target grounding", "非 procedure，不能测 Action IR"),
    ]
    add_table(slide, 0.4, 1.82, 12.52, 4.65,
              ["数据集", "结论", "真正可用的标注", "主要用于", "不能用于"],
              rows, [1.25, 1.2, 3.25, 3.0, 3.82], 11)
    add_text(slide, 1.2, 6.58, 10.9, 0.26,
             "必须修复 converter：现在的 18,995 / 230 / 45 / 1,156 条 JSONL 只保留文本，不是可用金标。",
             13, True, RED, PP_ALIGN.CENTER)

    # 9 Dataset allocation
    slide = new_slide(prs, "数据集分工", "每个数据集只支撑明确字段；缺失标注不能被包装成完整 Action IR", "DATA")
    rows = [
        ("Paper 1 数据本体", "Live Schema + sampled data + users", "候选关系、证据、共识、Schema 演化", "已有方法文档；需可复现 benchmark"),
        ("Paper 2 文档抽取", "MyFixit + MSPT", "action / target / tool / parameter", "主训练与字段级测试"),
        ("Paper 2 结构能力", "PET + ProPara + BioProcess + OMIn", "flow / state change / argument / grounding", "辅助测试，不合并成完整金标"),
        ("Paper 2 弱监督", "Text-mined Synthesis", "operations / conditions / recipes", "预训练，不能报告 gold score"),
        ("Paper 3 Agent", "tau2 Retail；计划 Airline/ABCD", "policy、tools、dialogue、execution", "目前只有 Retail 初步结果"),
    ]
    add_table(slide, 0.42, 1.8, 12.48, 4.82,
              ["论文", "数据来源", "提供的证据", "使用边界"],
              rows, [2.0, 3.55, 3.5, 3.43], 11)

    # 10 Missing data
    slide = new_slide(prs, "自建 Benchmark", "两套人工资产是 Paper 1 和 Paper 2 成立的实验前提", "DATA")
    add_card(slide, 0.72, 1.9, 5.75, 4.45, "Full Action IR Test Set（Paper 2）", [
        "从维修手册 / 工业 SOP / 业务策略抽样",
        "完整标注 actor、target、parameters",
        "preconditions、effects、constraints、flow",
        "ontology IDs、evidence span、unresolved fields",
        "双人标注 + 专家裁决 + agreement",
    ], TEAL, 15)
    add_card(slide, 6.88, 1.9, 5.75, 4.45, "Collaboration Benchmark（Paper 1）", [
        "Live Schema、采样数据和关系金标",
        "包含正确、错误、歧义和冲突的 candidate edges",
        "记录 JOIN 证据、用户确认、Owner decision",
        "注入 table / column / type evolution",
        "测关系质量、SQL 成本、专家时间和漂移恢复",
    ], GREEN, 15)

    # 11 Shared data roles
    slide = new_slide(prs, "共享数据资产", "Paper 1 提供对象/关系基础层；Paper 2、3 共享 Action IR 与运行资产", "DATA")
    add_card(slide, 0.72, 1.92, 3.65, 4.25, "Paper 1：需工程化", [
        "Live Schema 与候选关系",
        "采样 JOIN 证据和统计画像",
        "contributors / consensus / disputes",
        "Schema drift 与重验证记录",
    ], GREEN, 15)
    add_card(slide, 4.83, 1.92, 3.65, 4.25, "Paper 2：部分具备", [
        "已有 40 篇内部试验",
        "公开数据仅覆盖部分字段",
        "evidence / flow 当前为 0",
        "尚缺 Full Action IR 金标",
    ], TEAL, 16)
    add_card(slide, 8.94, 1.92, 3.65, 4.25, "Paper 3：已有原型", [
        "Retail Action IR / ActionBank",
        "341 个严格配对样本",
        "114 个任务、3 个 trials",
        "修复版全量重跑尚未完成",
    ], AMBER, 16)
    line(slide, 4.37, 4.0, 4.78, 4.0, GREEN, 2, True)
    line(slide, 8.48, 4.0, 8.89, 4.0, TEAL, 2, True)

    # 11 Research map
    slide = new_slide(prs, "论文关系与推进顺序", "Paper 1 构建对象/关系基础层；Paper 2、3 聚焦 Action Layer 的获取与运行使用", "RESEARCH MAP")
    add_text(slide, 0.75, 1.88, 1.4, 0.35, "逻辑顺序", 16, True, NAVY)
    stages_logic = [
        ("Paper 1", "Live Schema → Data Ontology", GREEN),
        ("Paper 2", "Document + Ontology → Action IR", TEAL),
        ("Paper 3", "IR → ActionBank → Execution", AMBER),
    ]
    for i, (title, body, color) in enumerate(stages_logic):
        x = 2.1 + i * 3.45
        rect(slide, x, 1.72, 2.85, 1.35, WHITE, color)
        add_badge(slide, x + 0.72, 1.9, 1.4, title, color)
        add_text(slide, x + 0.18, 2.48, 2.49, 0.28, body, 13, True, NAVY, PP_ALIGN.CENTER)
        if i < 2:
            line(slide, x + 2.88, 2.4, x + 3.35, 2.4, color, 2.4, True)
    line(slide, 0.75, 3.6, 12.55, 3.6, LINE, 1.2)
    add_text(slide, 0.75, 4.05, 1.4, 0.35, "推进顺序", 16, True, NAVY)
    stages_actual = [
        ("Paper 3", "先完成修复版全量试验\n判断是否有稳定任务级收益", AMBER),
        ("Paper 2", "修复当前评测缺陷\n建立完整 Action IR 金标", TEAL),
        ("Paper 1", "仅在前两篇证据成立后\n投入专家协作实验", GREEN),
    ]
    for i, (title, body, color) in enumerate(stages_actual):
        x = 2.1 + i * 3.45
        rect(slide, x, 3.9, 2.85, 1.65, WHITE, color)
        add_badge(slide, x + 0.72, 4.08, 1.4, title, color)
        add_text(slide, x + 0.18, 4.7, 2.49, 0.58, body, 12, False, MUTED, PP_ALIGN.CENTER)
        if i < 2:
            line(slide, x + 2.88, 4.75, x + 3.35, 4.75, color, 2.4, True)

    # 12 Paper1 concept
    slide = new_slide(prs, "Paper 1：协作式数据本体生成",
                      "以 collaborative-data-ontogenesis.docx 为主体：从 Live Database Schema 生长和演化数据本体", "PAPER 1")
    add_card(slide, 0.72, 1.9, 3.65, 4.15, "研究问题", [
        "全自动发现覆盖高但业务语义不可靠",
        "全人工建模准确但冷启动与维护成本高",
        "对所有候选执行全表 JOIN 验证代价高",
        "Schema 变化使已有关系快速过时",
    ], RED, 15)
    add_card(slide, 4.83, 1.9, 3.65, 4.15, "文档已有方法", [
        "Phase A：零 JOIN 的 Schema 发现与候选推测",
        "Phase B：采样 JOIN、统计画像与人工确认",
        "candidate → inferred → confirmed → approved",
        "冲突进入 disputed / pending_review",
        "Schema drift 触发软废弃和重验证",
    ], TEAL, 14)
    add_card(slide, 8.94, 1.9, 3.65, 4.15, "与大论文的关系", [
        "输出对象、字段和关系的本体基础层",
        "为 Paper 2 提供 existing ontology",
        "协作、证据和版本机制可扩展到动作定义",
        "Paper 1 本身不改写成 Action IR 论文",
    ], GREEN, 15)

    # 13 Paper1 loop
    slide = new_slide(prs, "Paper 1：方法",
                      "核心不是多 Agent，而是按成本分层获取证据，让候选关系经过验证、共识和演化", "PAPER 1")
    roles = [
        ("Discover", "SHOW / DESCRIBE\n+ sample", BLUE),
        ("Propose", "列名/类型/LLM\n候选关系", TEAL),
        ("Validate", "TABLESAMPLE JOIN\n+ statistics", AMBER),
        ("Confirm", "确认、反驳\n或补充语义", GREEN),
        ("Govern", "共识、Owner 审核\n与冲突裁决", RED),
        ("Evolve", "drift 检测\nsoft-deprecate / reopen", NAVY),
    ]
    for i, (title, body, color) in enumerate(roles):
        x = 0.45 + i * 2.13
        rect(slide, x, 1.85, 1.82, 1.55, WHITE, color)
        add_badge(slide, x + 0.28, 2.04, 1.26, title, color)
        add_text(slide, x + 0.12, 2.68, 1.58, 0.5, body, 12, False, MUTED, PP_ALIGN.CENTER)
        if i < 5:
            line(slide, x + 1.84, 2.64, x + 2.08, 2.64, color, 2, True)
    rect(slide, 3.15, 4.02, 7.05, 1.12, NAVY, NAVY)
    add_text(slide, 3.35, 4.18, 6.65, 0.32,
             "Candidate Edge = Implicit Ontology Relation Proposal", 18, True, WHITE, PP_ALIGN.CENTER)
    add_text(slide, 3.35, 4.58, 6.65, 0.28,
             "semantic edge | sampled evidence | contributors | consensus | status | schema version",
             12, False, WHITE, PP_ALIGN.CENTER)
    add_card(slide, 0.85, 5.55, 3.55, 0.95, "人工输入", [
        "只处理候选确认、业务补充和争议裁决",
    ], AMBER, 12)
    add_card(slide, 4.88, 5.55, 3.55, 0.95, "主要指标", [
        "relation quality + coverage + SQL / human cost",
    ], GREEN, 12)
    add_card(slide, 8.91, 5.55, 3.55, 0.95, "当前缺口", [
        "文档有案例描述；可复现代码与系统实验需补齐",
    ], RED, 12)

    # 14 Paper1 evaluation
    slide = new_slide(prs, "Paper 1：实验设计",
                      "验证两阶段证据获取能否在关系质量、计算成本和专家成本之间取得更优权衡", "PAPER 1")
    add_card(slide, 0.68, 1.82, 3.0, 4.62, "实验任务", [
        "Cold start：从 Live Schema 发现关系",
        "Budgeted validation：限制 JOIN / scan 预算",
        "Conflict：多人确认与业务语义冲突",
        "Evolution：表、列和类型发生变化",
    ], TEAL, 14)
    add_card(slide, 3.88, 1.82, 2.75, 4.62, "Baselines", [
        "Name/type heuristics",
        "LLM semantic matcher",
        "Full JOIN validation",
        "Human-only cataloging",
        "Ours：Phase A + B",
    ], BLUE, 14)
    add_card(slide, 6.83, 1.82, 3.0, 4.62, "质量与效率指标", [
        "Relation precision / recall / coverage",
        "SQL calls / scanned bytes / latency",
        "Expert minutes per approved edge",
        "Confidence calibration",
        "Drift recovery accuracy / time",
    ], AMBER, 14)
    add_card(slide, 10.03, 1.82, 2.62, 4.62, "Ablations", [
        "No Sampling",
        "No Human",
        "No Consensus",
        "No Evidence Ledger",
        "No Drift Revalidation",
    ], RED, 14)

    # Paper1 related work
    slide = new_slide(prs, "Paper 1：直接前驱", "不能再声称“首个协作式、多 Agent、动态本体构建框架”", "PAPER 1")
    rows = [
        ("HyWay (2025)", "LLM semantic mapping + iterative expert validation", "缺 multi-agent 独立证据与执行反馈"),
        ("IDEA2 (2026)", "专家协作、反复修订、共识与 provenance", "只覆盖 competency questions"),
        ("CooperKGC (2024)", "多 Agent entity/relation/event 抽取与纠错", "缺本体版本治理和 human ownership"),
        ("Clinical Multi-LLM KG (2026)", "schema-constrained RAG + consensus validation", "缺 action semantics 和真实 gold"),
        ("AutoPKG (ACL 2026 Findings)", "动态类型/属性诱导、决策 Agent、canonical graph", "Paper 1 最强直接竞争者"),
        ("Human-in-loop KG expansion", "候选推荐 + 人工验证 + 成本实验", "只解决新概念 parent placement"),
    ]
    add_table(slide, 0.42, 1.76, 12.5, 4.98,
              ["已有工作", "已经做到", "你的剩余空间"],
              rows, [2.7, 5.2, 4.6], 11)

    slide = new_slide(prs, "Paper 1：创新边界", "从现有文档中提炼三个可直接实验的贡献，避免泛称“人机协作”", "PAPER 1")
    add_card(slide, 0.7, 1.85, 3.82, 4.62, "成本自适应证据获取", [
        "Phase A 用 metadata 实现全量低成本覆盖",
        "Phase B 仅对高价值/不确定候选做采样 JOIN",
        "比较 full validation 的质量—计算成本前沿",
    ], TEAL, 15)
    add_card(slide, 4.76, 1.85, 3.82, 4.62, "证据—共识双轨生命周期", [
        "机器证据与人的业务确认分开记录",
        "confidence 不等于 consensus_level",
        "测 calibration、争议识别和专家时间",
    ], GREEN, 14)
    add_card(slide, 8.82, 1.85, 3.82, 4.62, "漂移感知的增量演化", [
        "Schema hash / version 定位受影响关系",
        "soft deprecation 后选择性重验证",
        "比较全量重建和静态目录的恢复成本",
    ], AMBER, 14)
    add_text(slide, 1.1, 6.58, 11.1, 0.25,
             "联邦文件存储和 Git 合并是工程贡献；论文创新必须由质量、计算成本、人力成本和漂移恢复实验支撑。",
             13, True, RED, PP_ALIGN.CENTER)

    # Paper2 method
    slide = new_slide(prs, "Paper 2：动作抽取",
                      "输入和输出固定：Document + Existing Ontology → Grounded IR Patch + Evidence", "PAPER 2")
    stages2 = [
        ("1", "结构解析", "标题、表格、步骤号、版面", TEAL),
        ("2", "程序单元", "动作、条件、异常、规则", BLUE),
        ("3", "LLM 抽取", "受控 Action IR + evidence", AMBER),
        ("4", "本体对齐", "候选检索 + 类型/角色约束", GREEN),
        ("5", "图与验证", "control flow + schema checks", RED),
    ]
    for i, args in enumerate(stages2):
        x = 0.55 + i * 2.56
        stage(slide, x, 2.05, 2.22, *args)
        if i < 4:
            line(slide, x + 2.24, 2.78, x + 2.5, 2.78, args[-1], 2.2, True)
    add_card(slide, 0.9, 4.45, 5.45, 1.55, "当前已有", [
        "40 篇内部试验；Rule / LLM-Only / LLM-Ontology / Ours",
    ], TEAL, 15)
    add_card(slide, 6.98, 4.45, 5.45, 1.55, "当前缺失", [
        "公开 benchmark、完整金标；evidence 和 control-flow 评测为 0",
    ], RED, 15)

    # 16 Paper2 experiment
    slide = new_slide(prs, "Paper 2：当前结果", "40 篇内部样本表明本体有帮助，但完整方法尚未超过直接基线", "PAPER 2")
    add_card(slide, 0.72, 1.85, 3.65, 4.55, "LLM-Ontology", [
        "Action mention F1：85.1%",
        "Action type：80.3%",
        "Target grounding：98.4%",
        "Validation pass：81.0%",
    ], TEAL, 16)
    add_card(slide, 4.83, 1.85, 3.65, 4.55, "Ours", [
        "Action mention F1：79.2%",
        "Action type：78.3%",
        "Target grounding：98.5%",
        "Parameter grounding F1：91.6%",
        "Validation pass：22.8%",
    ], BLUE, 15)
    add_card(slide, 8.94, 1.85, 3.65, 4.55, "结论与下一步", [
        "当前不能声称 Ours 最优",
        "先定位 validation pass 下降原因",
        "修复 evidence / flow 评测",
        "再做公开数据与 Full IR 金标",
    ], AMBER, 15)

    # Paper2 related work
    slide = new_slide(prs, "Paper 2：直接前驱", "过程抽取、程序图、ontology-guided extraction 和可执行生成均已有研究", "PAPER 2")
    rows = [
        ("Text2Event (ACL 2021)", "schema-constrained sequence-to-structure event extraction"),
        ("CPK Extraction (2019)", "goal/workflow/action/command/usage ontology；47,491 actions"),
        ("PET / PAGED", "activity、actor、gateway、flow 与 procedural graph benchmark"),
        ("Universal Prompting (2024)", "8 个 LLM；三数据集；最高 +8 F1"),
        ("Decomposed Hybrid BPM", "LLM 抽取 + deterministic process-model construction"),
        ("Ontology-informed PDF extraction", "procedure/step/substep + ontology + in-context learning"),
        ("Multi-Agent Procedural Graph (2026)", "builder + structural simulator + semantic refinement"),
        ("NL2ProcessOps / OMPD", "文本到执行代码；工业维护程序本体"),
    ]
    add_table(slide, 0.52, 1.72, 12.3, 5.05,
              ["直接前驱", "已经覆盖的能力"], rows, [4.0, 8.3], 11)

    slide = new_slide(prs, "Paper 2：成立门槛", "只有满足以下三项，才能把输出契约写成方法创新", "PAPER 2")
    add_card(slide, 0.7, 1.85, 3.82, 4.62, "公开数据", [
        "MyFixit / MSPT：动作、对象、参数",
        "PET / PAGED：control-flow",
        "按字段 mask 报告，不伪造完整标签",
    ], TEAL, 15)
    add_card(slide, 4.76, 1.85, 3.82, 4.62, "完整金标", [
        "100–200 个 Full Action IR",
        "双人标注 + 专家裁决 + agreement",
        "测 exact match、evidence、validation",
    ], AMBER, 15)
    add_card(slide, 8.82, 1.85, 3.82, 4.62, "直接对照", [
        "必须超过 LLM-Only 和 LLM-Ontology",
        "或证明可解释的质量/校验权衡",
        "并验证 ActionBank 下游效用",
    ], GREEN, 15)
    add_text(slide, 1.1, 6.58, 11.1, 0.25,
             "PAGED 是 benchmark 强敌；2026 Multi-Agent Procedural Graph 是方法强敌；OMPD 是工业表示强敌。",
             13, True, RED, PP_ALIGN.CENTER)

    # Paper3 method
    slide = new_slide(prs, "Paper 3：运行时语义",
                      "方法不是额外安全规则：同一 Action IR 同时生成状态检查、violation 和 repair 条件", "PAPER 3")
    stages3 = [
        ("1", "IR 编译", "确定性生成 ActionBank", TEAL),
        ("2", "状态更新", "只接受已观察工具结果", BLUE),
        ("3", "动作提案", "LLM 给出 action + args", AMBER),
        ("4", "本体校验", "类型/角色/状态/确认", RED),
        ("5", "执行/修复", "call 或结构化 violation", GREEN),
    ]
    for i, args in enumerate(stages3):
        x = 0.55 + i * 2.56
        stage(slide, x, 1.95, 2.22, *args)
        if i < 4:
            line(slide, x + 2.24, 2.68, x + 2.5, 2.68, args[-1], 2.2, True)
    add_card(slide, 0.95, 4.38, 5.35, 1.65, "Epistemic Action：弱 Grounding", [
        "查询用于获取未知状态；若要求对象已缓存，会形成启动死锁",
    ], BLUE, 15)
    add_card(slide, 7.03, 4.38, 5.35, 1.65, "Mutating Action：强 Grounding", [
        "改变状态前检查对象、参数角色、前置状态、策略和绑定确认",
    ], RED, 15)

    # 17 Paper3 concrete example
    slide = new_slide(prs, "Paper 3：执行示例", "取消订单任务如何经过状态获取、确认绑定和强 grounding", "PAPER 3")
    example_steps = [
        ("1", "认证", "find_user_id_by_email\n→ user_authenticated=true", BLUE),
        ("2", "读取订单", "get_order_details(#123)\n→ status=pending", TEAL),
        ("3", "绑定确认", "ask_for_confirmation\n绑定 action + arguments", AMBER),
        ("4", "强校验", "target / status / reason /\nconfirmation 均满足", RED),
        ("5", "执行效果", "cancel_pending_order\npending → cancelled", GREEN),
    ]
    for i, args in enumerate(example_steps):
        x = 0.55 + i * 2.56
        stage(slide, x, 1.88, 2.22, *args)
        if i < 4:
            line(slide, x + 2.24, 2.61, x + 2.5, 2.61, args[-1], 2.2, True)
    add_card(slide, 0.85, 4.25, 5.6, 1.82, "为什么不能直接取消？", [
        "初始时订单对象未观察、状态未知、用户未确认",
        "Mutating action 必须满足 strong grounding",
    ], RED, 14)
    add_card(slide, 6.88, 4.25, 5.6, 1.82, "状态反事实", [
        "若 status=delivered，则返回 PreconditionViolation",
        "Repair 应选择退货、询问或转人工，而不是重试取消",
    ], BLUE, 14)

    # 18 Current implementation assets
    slide = new_slide(prs, "Paper 3：实现链路", "已有 canonical 文件、编译器、运行时和一致性检查", "PAPER 3")
    assets = [
        ("Canonical IR", "data/action_ir/\nretail_action_ir.json", TEAL),
        ("Compiler", "compile_action_ir_to_\naction_bank.py", BLUE),
        ("Runtime View", "data/action_bank/\nretail_action_bank.json", AMBER),
        ("Agent Modules", "runtime_ontology\nadmissibility / repair", GREEN),
        ("Checks", "projection smoke test\npreflight / traces", RED),
    ]
    for i, (title, body, color) in enumerate(assets):
        x = 0.58 + i * 2.53
        rect(slide, x, 2.05, 2.18, 2.15, WHITE, color)
        add_badge(slide, x + 0.3, 2.28, 1.58, title, color)
        add_text(slide, x + 0.14, 3.1, 1.9, 0.65, body, 12, False, INK, PP_ALIGN.CENTER)
        if i < 4:
            line(slide, x + 2.2, 3.12, x + 2.46, 3.12, color, 2, True)
    rect(slide, 1.25, 5.05, 10.85, 0.95, PALE_TEAL, TEAL)
    add_text(slide, 1.48, 5.25, 10.38, 0.46,
             "设计约束：ActionBank 必须由 canonical Action IR 确定性生成；禁止手工修改导致 Paper 2 / Paper 3 表示断裂。",
             14, True, TEAL, PP_ALIGN.CENTER)

    # 19 Results
    slide = new_slide(prs, "Paper 3：初步结果",
                      "主分析：341 个严格配对样本，114 个任务，3 个完整 trials", "PAPER 3")
    data = ChartData()
    data.categories = ["Schema-Only", "Typed + Repair"]
    data.add_series("Success rate", (44.9, 55.7))
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.75), Inches(1.88),
        Inches(5.45), Inches(4.3), data
    ).chart
    chart.has_legend = False
    chart.value_axis.minimum_scale = 0
    chart.value_axis.maximum_scale = 70
    chart.value_axis.major_unit = 10
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.tick_labels.font.size = Pt(10)
    chart.category_axis.tick_labels.font.size = Pt(11)
    chart.plots[0].has_data_labels = True
    chart.plots[0].data_labels.number_format = '0.0"%"'
    chart.plots[0].data_labels.font.size = Pt(13)
    chart.plots[0].series[0].format.fill.solid()
    chart.plots[0].series[0].format.fill.fore_color.rgb = TEAL
    add_card(slide, 6.58, 1.88, 5.95, 1.95, "积极证据", [
        "+10.9 pp；paired McNemar p = 0.0029",
        "Transfer calls：323 → 62",
        "说明机制值得完整重跑，而非已经定论",
    ], TEAL, 15)
    add_card(slide, 6.58, 4.08, 5.95, 2.1, "不能回避的限制", [
        "task-level sign test p = 0.109，未显著",
        "8-trial run 被配额中断",
        "confirmation binding 缺陷修复后尚未重跑",
        "平均延迟：190.6s → 260.3s",
    ], RED, 14)

    # 20 Boundaries
    slide = new_slide(prs, "论文边界", "三篇论文形成基础本体、动作获取和运行使用的递进关系", "SYNTHESIS")
    rows = [
        ("Paper 1", "数据本体如何低成本协作生成？", "Live Schema → Versioned Data Ontology", "不直接生成 Action IR"),
        ("Paper 2", "文档如何产生动作候选？", "Document → Action IR Patch", "不负责协作治理和 agent policy"),
        ("Paper 3", "如何理解、验证和修复动作？", "ActionBank → Runtime Execution", "不负责从文档构建动作层"),
    ]
    add_table(slide, 0.62, 1.92, 12.05, 4.35,
              ["论文", "核心问题", "输入/输出", "明确不做什么"],
              rows, [1.35, 3.0, 3.45, 4.25], 12)
    add_text(slide, 1.1, 6.48, 11.1, 0.28,
             "体系性来自层次递进和数据依赖；不能再声称三篇论文都共享同一个 Action IR 输出。",
             14, True, NAVY, PP_ALIGN.CENTER)

    # Thesis innovations
    slide = new_slide(prs, "总体研究假设", "先写成可证伪假设；实验达标后才能在论文中改写为创新贡献", "CONTRIBUTIONS")
    add_card(slide, 0.68, 1.82, 3.85, 4.7, "H1：协作式数据本体生成", [
        "metadata 全量发现 + 选择性采样验证",
        "机器证据与人类共识分轨管理",
        "降低关系验证的 SQL 和专家成本",
        "当前状态：有方法文档，缺可复现实验",
    ], GREEN, 15)
    add_card(slide, 4.74, 1.82, 3.85, 4.7, "H2：动作抽取", [
        "Existing-ontology grounding + evidence",
        "提高完整 Action IR 的可验证性",
        "并产生可用的 ActionBank",
        "当前状态：40 篇结果混合，需修复",
    ], TEAL, 15)
    add_card(slide, 8.8, 1.82, 3.85, 4.7, "H3：运行时语义", [
        "epistemic weak / mutating strong grounding",
        "提高任务成功并减少错误 transfer",
        "收益来自本体机制而非额外重试",
        "当前状态：+10.9 pp，任务级未显著",
    ], AMBER, 15)

    # Evidence matrix
    slide = new_slide(prs, "证据矩阵", "明确当前证据、缺失实验和停止条件", "EVIDENCE")
    rows = [
        ("Paper 1", "方法文档 + 案例描述", "关系金标 + 成本/协作/漂移实验", "无质量—成本优势则收缩为工程方案"),
        ("Paper 2", "40 篇内部结果混合", "公开集 + Full IR 金标", "不能超过直接基线则收缩主张"),
        ("Paper 3", "+10.9 pp；task p=0.109", "修复版全量 trials + 外部域", "无稳定任务级收益则转向诊断论文"),
    ]
    add_table(slide, 0.55, 1.88, 12.2, 4.55,
              ["论文", "当前证据", "必须补齐", "Go / No-Go"],
              rows, [1.4, 3.0, 3.7, 4.1], 12)

    # Roadmap
    slide = new_slide(prs, "推进计划", "每阶段以可交付物和验收条件结束，不按概念模块推进", "ROADMAP")
    phases = [
        ("01", "2026 Q3", "修复 binding\n全量 paired trials\n任务级统计与消融", RED),
        ("02", "2026 Q3", "冻结 IR core\n补 Airline 投影\n记录跨域字段差异", TEAL),
        ("03", "2026 Q3-Q4", "修复 Paper 2 评测\n100–200 Full IR\n公开 benchmark", BLUE),
        ("04", "2026 Q4", "复现 Kyuubi workflow\n关系/成本/漂移实验\n决定是否独立成文", AMBER),
    ]
    for i, (num, title, body, color) in enumerate(phases):
        x = 0.72 + i * 3.15
        rect(slide, x, 2.0, 2.75, 3.72, WHITE, color)
        add_badge(slide, x + 0.2, 2.22, 0.68, num, color)
        add_text(slide, x + 0.2, 2.93, 2.35, 0.4, title, 17, True, NAVY, PP_ALIGN.CENTER)
        add_text(slide, x + 0.2, 3.68, 2.35, 1.15, body, 14, False, MUTED, PP_ALIGN.CENTER)
        if i < 3:
            line(slide, x + 2.78, 3.82, x + 3.08, 3.82, color, 2.4, True)
    add_text(slide, 1.2, 6.18, 10.9, 0.38,
             "停止扩域条件：Paper 3 无任务级稳定收益，或 Paper 2 不能超过直接本体基线",
             16, True, TEAL, PP_ALIGN.CENTER)

    # Advisor questions
    slide = new_slide(prs, "可能追问", "主动暴露边界，并给出可验证的回答", "DEFENSE")
    rows = [
        ("Paper 1 不输出 Action IR，如何统一？", "Paper 1 构建对象/关系基础层；Paper 2 在其上生成 Action IR；Paper 3 使用动作层。"),
        ("Paper 1 有抽取 Agent，为何还要 Paper 2？", "Paper 1 把抽取器视为 proposal producer；Paper 2 必须独立证明复杂文档抽取贡献。"),
        ("多 Agent 是否只是拆 prompt？", "必须通过角色异质、独立证据、critic、consensus 与 ablation 证明机制收益。"),
        ("公开数据不完整，结果可信吗？", "公开集测局部能力；人工 Full Action IR 集测完整语义，两者分开报告。"),
        ("Paper 3 是否只是规则 verifier？", "规则来自统一 Action IR，并同时驱动 state、admissibility、repair 和 explanation。"),
    ]
    add_table(slide, 0.52, 1.75, 12.28, 4.98,
              ["可能追问", "回答口径"], rows, [4.0, 8.28], 12)

    # Requested advisor support
    slide = new_slide(prs, "需要导师决策", "每项选择都会直接改变下一阶段投入，不再泛泛征求意见", "REQUEST")
    requests = [
        ("1", "Paper 1 定位", "现在按独立论文投入，还是先降为大论文系统章节？", TEAL),
        ("2", "金标领域", "建议优先维修/工业 SOP；是否同意锁定该方向？", BLUE),
        ("3", "专家资源", "能否协调 2–3 名专家完成标注、裁决和时间记录？", AMBER),
        ("4", "Paper 3 门槛", "是否以任务级稳定收益作为扩展 Airline 的前提？", GREEN),
        ("5", "Paper 2 主线", "以抽取准确率为主，还是以 executable downstream utility 为主？", RED),
        ("6", "可发布数据", "能否获得可匿名的 SOP、Schema、API 和变更记录？", NAVY),
    ]
    for i, (num, title, body, color) in enumerate(requests):
        row, col = divmod(i, 2)
        x = 0.7 + col * 6.25
        y = 1.72 + row * 1.55
        rect(slide, x, y, 5.78, 1.15, WHITE, color)
        add_badge(slide, x + 0.18, y + 0.18, 0.58, num, color)
        add_text(slide, x + 0.98, y + 0.13, 1.65, 0.32, title, 15, True, NAVY)
        add_text(slide, x + 0.98, y + 0.53, 4.45, 0.38, body, 12, False, MUTED)
    add_text(slide, 4.35, 6.68, 4.65, 0.38, "谢谢，请批评指正", 18, True, TEAL, PP_ALIGN.CENTER)

    # Advisor-facing main deck: retain a concise decision-oriented narrative.
    # Detailed dataset audits and repeated related-work pages remain in source
    # and can be restored as backup slides when needed.
    finalize_main_deck(
        prs,
        [
            0,   # Cover
            5,   # Core problem
            2,   # International status
            3,   # Palantir
            4,   # Thesis outline
            14,  # Research map
            1,   # Current research basis
            29,  # Thesis contributions
            6,   # Action IR
            9,   # Lifecycle
            11,  # Dataset allocation
            13,  # Shared data asset
            15, 16, 19,       # Paper 1
            20, 21, 23,       # Paper 2
            24, 25, 27,       # Paper 3
            28, 30, 31, 33,   # Synthesis, evidence, roadmap, decisions
        ],
    )
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
