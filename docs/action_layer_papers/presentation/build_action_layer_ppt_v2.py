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
             "核心目标：构建可协作生成、从文档扩充、可供 Agent 执行的 Action Layer",
             19, True, WHITE)
    add_text(slide, 0.87, 6.55, 7.5, 0.32, "导师汇报 · 2026年6月", 12, False,
             __import__("pptx").dml.color.RGBColor(170, 194, 210))
    add_text(slide, 11.7, 6.48, 0.75, 0.42, "01", 20, True, TEAL, PP_ALIGN.RIGHT)

    # 2 Dissertation outline
    slide = new_slide(prs, "大论文拟定大纲", "三篇小论文分别对应构建框架、文档抽取和运行时执行", "THESIS OUTLINE")
    items = [
        ("01", "绪论", "问题、研究目标与总体框架", TEAL),
        ("02", "理论基础与 Action IR", "动作语义、统一表示与治理模型", BLUE),
        ("03", "协作式动作本体生成", "Paper 1：Multi-Agent + Human-in-the-Loop", GREEN),
        ("04", "程序文档动作抽取", "Paper 2：Document → Grounded Action IR", AMBER),
        ("05", "Agent 动作理解与规划", "Paper 3：ActionBank → Runtime Execution", RED),
        ("06", "统一系统与跨域评估", "Retail、Airline、Maintenance / SOP", TEAL),
    ]
    for i, (num, title, body, color) in enumerate(items):
        row, col = divmod(i, 2)
        x = 0.8 + col * 6.25
        y = 1.78 + row * 1.55
        rect(slide, x, y, 5.75, 1.15, WHITE, color)
        add_badge(slide, x + 0.22, y + 0.18, 0.64, num, color)
        add_text(slide, x + 1.05, y + 0.16, 2.25, 0.35, title, 16, True, NAVY)
        add_text(slide, x + 1.05, y + 0.58, 4.3, 0.32, body, 13, False, MUTED)

    # 3 Overall question
    slide = new_slide(prs, "总体问题：如何让本体支持“行动”？", "研究对象不是泛化知识图谱，而是操作型本体中的 Action Layer", "PROBLEM")
    add_card(slide, 0.72, 1.88, 3.55, 3.8, "传统本体回答", [
        "有哪些对象和类型？",
        "对象之间有什么关系？",
        "属性和约束是什么？",
    ], BLUE, 17)
    add_text(slide, 4.4, 3.22, 0.65, 0.45, "→", 30, True, TEAL, PP_ALIGN.CENTER)
    add_card(slide, 5.1, 1.88, 3.55, 3.8, "Action Layer 还要回答", [
        "当前能做什么？",
        "动作作用于谁？",
        "需要什么状态和参数？",
        "执行后世界如何变化？",
    ], TEAL, 16)
    add_text(slide, 8.78, 3.22, 0.65, 0.45, "→", 30, True, AMBER, PP_ALIGN.CENTER)
    add_card(slide, 9.48, 1.88, 3.15, 3.8, "最终支撑", [
        "动作抽取",
        "协作式构建与演化",
        "Agent 规划",
        "执行验证与解释",
    ], AMBER, 16)
    rect(slide, 1.35, 6.02, 10.6, 0.55, PALE_RED, RED)
    add_text(slide, 1.55, 6.15, 10.2, 0.28,
             "API Schema 只描述调用语法；Action Layer 描述动作在业务世界中的语义。",
             15, True, RED, PP_ALIGN.CENTER)

    # 4 What is Action IR
    slide = new_slide(prs, "Action IR：三种表示之间的规范化中间层",
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
    slide = new_slide(prs, "Action IR 的字段不是平铺列表，而是九个语义层", "Core 字段用于三篇论文；Optional 字段允许不同数据集部分标注", "ACTION IR")
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
    slide = new_slide(prs, "Action IR 例子：退回已送达订单中的商品",
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
    slide = new_slide(prs, "Action IR 的完整生命周期", "从多源证据到协作治理、发布和 Agent 执行", "ACTION IR")
    steps = [
        ("1", "多源证据", "metadata / document / API / logs", TEAL),
        ("2", "Agent 提案", "Action IR Patch + evidence", BLUE),
        ("3", "协作验证", "validate / critique / consensus", AMBER),
        ("4", "版本发布", "canonical Action IR / ActionBank", GREEN),
        ("5", "演化反馈", "execution traces / schema drift", RED),
    ]
    for i, args in enumerate(steps):
        x = 0.55 + i * 2.56
        stage(slide, x, 2.15, 2.22, *args)
        if i < 4:
            line(slide, x + 2.24, 2.88, x + 2.5, 2.88, args[-1], 2.2, True)
    add_card(slide, 1.0, 4.55, 5.35, 1.45, "Paper 1 负责完整治理循环", [
        "把多个 Agent 和人的贡献转化为可审计版本演化",
    ], TEAL, 14)
    add_card(slide, 6.98, 4.55, 5.35, 1.45, "Paper 2 / Paper 3 分别提供输入与反馈", [
        "文档抽取产生提案；运行轨迹暴露缺失、冲突和漂移",
    ], BLUE, 14)

    # 8 Dataset audit
    slide = new_slide(prs, "数据可用性审计：已转换不等于可监督训练",
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
    slide = new_slide(prs, "数据集必须按论文和能力分配", "没有任何一个公开数据集可以同时支撑三篇论文的全部主张", "DATA")
    rows = [
        ("Paper 1 协作构建", "AAS/OPC UA/SysML/BOM、SOP/API、tau2 traces", "候选 patch、冲突、验证、版本演化", "需自建 Collaboration Benchmark"),
        ("Paper 2 文档抽取", "MyFixit + MSPT", "action / target / tool / parameter", "主训练与字段级测试"),
        ("Paper 2 结构能力", "PET + ProPara + BioProcess + OMIn", "flow / state change / argument / grounding", "辅助测试，不合并成完整金标"),
        ("Paper 2 弱监督", "Text-mined Synthesis", "operations / conditions / recipes", "预训练，不能报告 gold score"),
        ("Paper 3 Agent", "tau2 Retail/Airline + ABCD", "policy、tools、dialogue、execution", "tau2 主实验，ABCD 外部验证"),
    ]
    add_table(slide, 0.42, 1.8, 12.48, 4.82,
              ["论文", "数据来源", "提供的证据", "使用边界"],
              rows, [2.0, 3.55, 3.5, 3.43], 11)

    # 10 Missing data
    slide = new_slide(prs, "真正缺失的数据：两套自建 benchmark", "这不是附加工作，而是 Paper 1 和 Paper 2 能否成立的前提", "DATA")
    add_card(slide, 0.72, 1.9, 5.75, 4.45, "Full Action IR Test Set（Paper 2）", [
        "从维修手册 / 工业 SOP / 业务策略抽样",
        "完整标注 actor、target、parameters",
        "preconditions、effects、constraints、flow",
        "ontology IDs、evidence span、unresolved fields",
        "双人标注 + 专家裁决 + agreement",
    ], TEAL, 15)
    add_card(slide, 6.88, 1.9, 5.75, 4.45, "Collaboration Benchmark（Paper 1）", [
        "多源候选：metadata、document、API、execution trace",
        "包含正确、错误、缺失和冲突的 IR Patch",
        "记录 Agent votes、专家 decision 和 audit trail",
        "注入 schema / policy evolution",
        "测质量、覆盖率、专家时间和 time-to-consensus",
    ], GREEN, 15)

    # 11 Shared data roles
    slide = new_slide(prs, "一份 Action IR 数据资产，支撑三种研究任务", "体系性来自同一语义资产在构建、抽取和执行中的闭环", "DATA")
    add_card(slide, 0.72, 1.92, 3.65, 4.25, "Paper 1：协作事件", [
        "candidate patch 与证据",
        "Agent / 用户验证意见",
        "冲突、裁决、版本和演化记录",
        "测试质量—成本—覆盖率权衡",
    ], GREEN, 15)
    add_card(slide, 4.83, 1.92, 3.65, 4.25, "Paper 2：抽取样本", [
        "输入：文档 + ontology",
        "标签：Action IR + procedure graph",
        "测试：字段、grounding、flow、evidence",
    ], TEAL, 16)
    add_card(slide, 8.94, 1.92, 3.65, 4.25, "Paper 3：执行样本", [
        "Action IR → ActionBank",
        "runtime state 由对话和工具结果构建",
        "测试 admissibility、repair、success",
    ], AMBER, 16)
    line(slide, 4.37, 4.0, 4.78, 4.0, GREEN, 2, True)
    line(slide, 8.48, 4.0, 8.89, 4.0, TEAL, 2, True)

    # 11 Research map
    slide = new_slide(prs, "三篇论文的逻辑关系与实际推进顺序", "Paper 1 是闭环框架，Paper 2 和 Paper 3 分别提供知识输入与运行反馈", "RESEARCH MAP")
    add_text(slide, 0.75, 1.88, 1.4, 0.35, "逻辑顺序", 16, True, NAVY)
    stages_logic = [
        ("Paper 1", "Collaborative Ontogenesis Loop", GREEN),
        ("Paper 2", "Document → IR Patch", TEAL),
        ("Paper 3", "ActionBank → Execution / Feedback", AMBER),
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
        ("Paper 3", "已有代码和初步结果\n先验证 Action Layer 有无下游价值", AMBER),
        ("Paper 2", "构建规模化、可追踪的动作来源", TEAL),
        ("Paper 1", "整合多 Agent 提案、验证、共识与演化", GREEN),
    ]
    for i, (title, body, color) in enumerate(stages_actual):
        x = 2.1 + i * 3.45
        rect(slide, x, 3.9, 2.85, 1.65, WHITE, color)
        add_badge(slide, x + 0.72, 4.08, 1.4, title, color)
        add_text(slide, x + 0.18, 4.7, 2.49, 0.58, body, 12, False, MUTED, PP_ALIGN.CENTER)
        if i < 2:
            line(slide, x + 2.88, 4.75, x + 3.35, 4.75, color, 2.4, True)

    # 12 Paper1 concept
    slide = new_slide(prs, "Paper 1：Collaborative Action Ontogenesis",
                      "多 Agent + Human-in-the-Loop 持续构建和演化本体动作层", "PAPER 1")
    add_card(slide, 0.72, 1.9, 3.65, 4.15, "为什么需要协作式框架", [
        "自动方法覆盖高但语义不可靠",
        "纯专家方法准确但成本高",
        "Schema、SOP、API 和策略持续变化",
        "单一 Agent 容易产生系统性偏差",
    ], RED, 16)
    add_card(slide, 4.83, 1.9, 3.65, 4.15, "输入证据", [
        "数据库 Schema 与统计画像",
        "SOP、手册和策略文档",
        "API / tool schemas",
        "Agent 执行日志与失败轨迹",
        "领域专家补充",
    ], TEAL, 15)
    add_card(slide, 8.94, 1.9, 3.65, 4.15, "目标输出", [
        "版本化 canonical Action IR",
        "完整 provenance 与贡献者",
        "可信度和共识级别",
        "争议、软废弃与演化记录",
    ], GREEN, 16)

    # 13 Paper1 loop
    slide = new_slide(prs, "Paper 1 方法：提案—验证—批判—共识—发布循环",
                      "Agent 负责不同认知任务；人只处理高风险、低置信度和争议项", "PAPER 1")
    roles = [
        ("Discover", "Schema / API\n候选发现", BLUE),
        ("Extract", "Document →\nIR Patch", TEAL),
        ("Ground", "类型、对象与\n参数对齐", AMBER),
        ("Validate", "采样、约束与\n执行日志验证", GREEN),
        ("Critique", "冲突、重复与\n证据缺失", RED),
        ("Consensus", "投票、仲裁与\n版本发布", NAVY),
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
             "Action IR Patch + Proposal Envelope", 19, True, WHITE, PP_ALIGN.CENTER)
    add_text(slide, 3.35, 4.58, 6.65, 0.28,
             "semantic delta | evidence | contributors | votes | dispute | audit trail",
             12, False, WHITE, PP_ALIGN.CENTER)
    add_card(slide, 0.85, 5.55, 3.55, 0.95, "人类 Micro-task", [
        "确认 / 反驳 / 补充 / 裁决",
    ], AMBER, 12)
    add_card(slide, 4.88, 5.55, 3.55, 0.95, "可信度升级", [
        "candidate → inferred → confirmed → approved",
    ], GREEN, 12)
    add_card(slide, 8.91, 5.55, 3.55, 0.95, "持续演化", [
        "schema drift → reopen → revalidate",
    ], RED, 12)

    # 14 Paper1 evaluation
    slide = new_slide(prs, "Paper 1 实验：不仅比较本体质量，还要比较协作成本",
                      "验证多 Agent 协作是否真的优于单 Agent、自动流水线和纯专家流程", "PAPER 1")
    add_card(slide, 0.68, 1.82, 3.0, 4.62, "实验任务", [
        "Cold start：从多源证据构建动作层",
        "Noisy proposal：注入错误与缺失字段",
        "Conflict：不同 Agent / 用户意见冲突",
        "Evolution：Schema、SOP 和策略变化",
    ], TEAL, 14)
    add_card(slide, 3.88, 1.82, 2.75, 4.62, "Baselines", [
        "Single-LLM generation",
        "Sequential auto pipeline",
        "Human-only construction",
        "Simple majority vote",
        "Ours：role-specialized loop",
    ], BLUE, 14)
    add_card(slide, 6.83, 1.82, 3.0, 4.62, "质量与效率指标", [
        "Action IR field / exact accuracy",
        "Coverage 与 accepted actions",
        "Expert minutes per accepted action",
        "Time-to-consensus",
        "Conflict detection F1",
    ], AMBER, 14)
    add_card(slide, 10.03, 1.82, 2.62, 4.62, "Ablations", [
        "No Critic",
        "No Validator",
        "No Human",
        "No Provenance",
        "No Revalidation",
    ], RED, 14)

    # Paper1 related work
    slide = new_slide(prs, "Paper 1 有哪些直接前驱？", "不能再声称“首个协作式、多 Agent、动态本体构建框架”", "PAPER 1")
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

    slide = new_slide(prs, "Paper 1 真正可保留的创新边界", "必须是组合机制创新，并通过直接对照实验验证", "PAPER 1")
    add_card(slide, 0.7, 1.85, 3.82, 4.62, "Action-Specific Patch", [
        "修改 actor、target、roles",
        "preconditions、effects、constraints",
        "不是普通 class/property/triple proposal",
    ], TEAL, 15)
    add_card(slide, 4.76, 1.85, 3.82, 4.62, "Multi-Source Executable Validation", [
        "metadata + document + API + traces",
        "类型、状态、反事实和工具执行验证",
        "运行失败可反向挑战已发布定义",
    ], GREEN, 14)
    add_card(slide, 8.82, 1.85, 3.82, 4.62, "Governed Evolution", [
        "Action IR 与 Proposal Envelope 分离",
        "dispute、owner、version、soft deprecation",
        "runtime-triggered revalidation",
    ], AMBER, 14)
    add_text(slide, 1.1, 6.58, 11.1, 0.25,
             "若缺少执行验证和运行反馈闭环，Paper 1 很容易被视为 AutoPKG + HyWay 的领域变体。",
             13, True, RED, PP_ALIGN.CENTER)

    # Paper2 method
    slide = new_slide(prs, "Paper 2：从程序文档抽取 Ontology-Grounded Action IR",
                      "作为协作框架中的 Document Extraction Agent，也可独立形成抽取论文", "PAPER 2")
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
    add_card(slide, 0.9, 4.45, 5.45, 1.55, "核心创新", [
        "从 action mention 提升为可投影的 ontology action record",
    ], TEAL, 15)
    add_card(slide, 6.98, 4.45, 5.45, 1.55, "关键约束", [
        "无法对齐的字段标记 unresolved，不允许无证据补全",
    ], RED, 15)

    # 16 Paper2 experiment
    slide = new_slide(prs, "Paper 2：实验必须分层，否则无法证明 Action IR 有效", "公开数据评估局部能力，人工完整集评估整体表示", "PAPER 2")
    add_card(slide, 0.72, 1.85, 3.65, 4.55, "字段级", [
        "Action / Actor / Target F1",
        "Parameter 与 Role F1",
        "Evidence Span F1",
    ], TEAL, 16)
    add_card(slide, 4.83, 1.85, 3.65, 4.55, "结构级", [
        "Ontology Grounding Accuracy",
        "Control-flow Edge F1",
        "Validation Pass Rate",
        "Full Action IR Exact Match",
    ], BLUE, 15)
    add_card(slide, 8.94, 1.85, 3.65, 4.55, "下游级", [
        "协作提案 acceptance / conflict",
        "ActionBank projection 成功率",
        "Agent admissibility / success 变化",
    ], AMBER, 15)

    # Paper2 related work
    slide = new_slide(prs, "Paper 2 也有非常接近的前人工作", "过程抽取、程序图、ontology-guided extraction 和可执行生成均已有研究", "PAPER 2")
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

    slide = new_slide(prs, "Paper 2 必须把“输出契约”作为核心创新", "不能再声称首个 SOP/程序动作抽取或首个 ontology-guided pipeline", "PAPER 2")
    add_card(slide, 0.7, 1.85, 3.82, 4.62, "Existing-Ontology Grounding", [
        "不是生成任意 event/BPMN label",
        "动作、对象、参数映射到已有 ontology IDs",
        "无法映射时显式 unresolved",
    ], TEAL, 15)
    add_card(slide, 4.76, 1.85, 3.82, 4.62, "Executable Action Semantics", [
        "target-object type 与 parameter roles",
        "preconditions、effects、policy constraints",
        "evidence 和 state transition",
    ], AMBER, 15)
    add_card(slide, 8.82, 1.85, 3.82, 4.62, "Cross-Paper Contract", [
        "可形成 Action IR Patch",
        "可确定性投影到 ActionBank",
        "下游 admissibility utility 参与评估",
    ], GREEN, 15)
    add_text(slide, 1.1, 6.58, 11.1, 0.25,
             "PAGED 是 benchmark 强敌；2026 Multi-Agent Procedural Graph 是方法强敌；OMPD 是工业表示强敌。",
             13, True, RED, PP_ALIGN.CENTER)

    # Paper3 method
    slide = new_slide(prs, "Paper 3：面向 Agent 的动作理解、约束与修复",
                      "假设 Action IR 已存在；研究它怎样成为运行时动作语义", "PAPER 3")
    stages3 = [
        ("1", "IR 编译", "Action IR → ActionBank", TEAL),
        ("2", "运行状态", "仅使用对话与已观察工具结果", BLUE),
        ("3", "LLM 提案", "candidate action + arguments", AMBER),
        ("4", "可执行性", "type-aware admissibility", RED),
        ("5", "执行/修复", "tool call 或 ontology violation", GREEN),
    ]
    for i, args in enumerate(stages3):
        x = 0.55 + i * 2.56
        stage(slide, x, 1.95, 2.22, *args)
        if i < 4:
            line(slide, x + 2.24, 2.68, x + 2.5, 2.68, args[-1], 2.2, True)
    add_card(slide, 0.95, 4.38, 5.35, 1.65, "Epistemic Action：弱 Grounding", [
        "查询和检查用于获取状态，不能要求对象已被缓存",
    ], BLUE, 15)
    add_card(slide, 7.03, 4.38, 5.35, 1.65, "Mutating Action：强 Grounding", [
        "修改状态前检查对象、角色、状态、策略和用户确认",
    ], RED, 15)

    # 17 Paper3 concrete example
    slide = new_slide(prs, "Paper 3 具体例子：取消订单 #123", "同一个用户目标如何经过状态获取、确认绑定和强 grounding", "PAPER 3")
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
    slide = new_slide(prs, "Paper 3 当前已落地的 Action IR 使用链路", "不是概念性接口：已有 canonical 文件、编译器、运行时和一致性检查", "PAPER 3")
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
    slide = new_slide(prs, "Paper 3 初步结果：有效信号与不确定性同时存在",
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
    ], TEAL, 15)
    add_card(slide, 6.58, 4.08, 5.95, 2.1, "不能回避的限制", [
        "task-level sign test p = 0.109，未显著",
        "8-trial run 被配额中断",
        "confirmation binding 缺陷修复后尚未重跑",
    ], RED, 14)

    # 20 Boundaries
    slide = new_slide(prs, "三篇论文的关系与边界", "共享 Action IR，但不能重复声称同一个贡献", "SYNTHESIS")
    rows = [
        ("Paper 1", "如何持续构建和演化？", "Evidence → Versioned Action IR", "不替代各专职抽取算法"),
        ("Paper 2", "文档如何产生动作候选？", "Document → Action IR Patch", "不负责协作治理和 agent policy"),
        ("Paper 3", "如何理解、验证和修复动作？", "ActionBank → Runtime Execution", "不负责从文档构建动作层"),
    ]
    add_table(slide, 0.62, 1.92, 12.05, 4.35,
              ["论文", "核心问题", "输入/输出", "明确不做什么"],
              rows, [1.35, 3.0, 3.45, 4.25], 12)
    add_text(slide, 1.1, 6.48, 11.1, 0.28,
             "体系性来自共享表示和数据闭环；创新性仍需由每篇独立的机制实验支撑。",
             14, True, NAVY, PP_ALIGN.CENTER)

    # Thesis innovations
    slide = new_slide(prs, "需要向导师突出的大论文创新点", "创新不是“用了本体和多 Agent”，而是三个可验证的机制贡献", "CONTRIBUTIONS")
    add_card(slide, 0.68, 1.82, 3.85, 4.7, "创新一：可演化的动作本体工程", [
        "Action IR Patch，而不是整库自由生成",
        "多源、多 Agent 的独立证据与角色分工",
        "critique、consensus、provenance 和 revalidation",
        "质量—覆盖率—专家成本联合优化",
    ], GREEN, 15)
    add_card(slide, 4.74, 1.82, 3.85, 4.7, "创新二：本体约束的动作抽取", [
        "从 action mention 提升到完整 Action IR",
        "文档结构、控制流、状态和证据联合建模",
        "现有本体约束 grounding，显式 unresolved",
        "可直接投影到协作提案和运行时 ActionBank",
    ], TEAL, 15)
    add_card(slide, 8.8, 1.82, 3.85, 4.7, "创新三：类型感知的动作语义", [
        "区分获取状态的 epistemic action",
        "与改变状态的 mutating action",
        "weak / strong grounding 避免统一 verifier 的矛盾",
        "ontology violation 驱动 repair 与失败分析",
    ], AMBER, 15)

    # Evidence matrix
    slide = new_slide(prs, "每篇论文必须用什么证据支撑主张？", "只比较最终准确率，无法证明本体动作层是有效机制", "EVIDENCE")
    rows = [
        ("Paper 1", "Multi-agent consensus loop", "IR quality / coverage / expert time / dispute", "Single LLM / automation / expert-only"),
        ("Paper 2", "Ontology constraint", "Grounding / flow / evidence / validation", "LLM-only extraction"),
        ("Paper 3", "Type-aware admissibility", "Task success + violations + repair + latency", "Schema-only + component ablations"),
    ]
    add_table(slide, 0.55, 1.88, 12.2, 4.55,
              ["论文", "核心机制", "必须报告的机制指标", "关键对照"],
              rows, [1.4, 3.0, 4.25, 3.55], 12)

    # Roadmap
    slide = new_slide(prs, "建议推进路线：先补强证据，再扩展场景", "实际顺序以降低研究风险为目标", "ROADMAP")
    phases = [
        ("01", "Paper 3 重跑", "确认修复版有效\n完整 paired trials\ncomponent ablation", RED),
        ("02", "固定共享模型", "Action IR core schema\nProposal Envelope\nfull-label test set", TEAL),
        ("03", "完成 Paper 2", "字段与结构评估\n误差分析\n生成规模化 ActionBank", BLUE),
        ("04", "实现 Paper 1", "multi-agent loop\nconsensus / conflict\nschema evolution", AMBER),
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
             "跨域顺序：Retail → Airline → Maintenance / Industrial SOP",
             16, True, TEAL, PP_ALIGN.CENTER)

    # Advisor questions
    slide = new_slide(prs, "导师最可能追问什么？", "汇报时主动暴露边界，并给出可验证的回答", "DEFENSE")
    rows = [
        ("三篇是否只是共享 Action IR？", "不是：分别研究治理循环、抽取算法和运行时语义，baseline 与指标独立。"),
        ("Paper 1 有抽取 Agent，为何还要 Paper 2？", "Paper 1 把抽取器视为 proposal producer；Paper 2 必须独立证明复杂文档抽取贡献。"),
        ("多 Agent 是否只是拆 prompt？", "必须通过角色异质、独立证据、critic、consensus 与 ablation 证明机制收益。"),
        ("公开数据不完整，结果可信吗？", "公开集测局部能力；人工 Full Action IR 集测完整语义，两者分开报告。"),
        ("Paper 3 是否只是规则 verifier？", "规则来自统一 Action IR，并同时驱动 state、admissibility、repair 和 explanation。"),
    ]
    add_table(slide, 0.52, 1.75, 12.28, 4.98,
              ["可能追问", "回答口径"], rows, [4.0, 8.28], 12)

    # Requested advisor support
    slide = new_slide(prs, "这次汇报需要导师提供什么帮助？", "不是泛泛征求意见，而是请求对关键研究资源和边界作出决策", "REQUEST")
    requests = [
        ("1", "论文强度判断", "Paper 1 是独立论文，还是大论文统一系统章节？", TEAL),
        ("2", "场景聚焦", "Full Action IR Test Set 选维修手册、工业 SOP，还是业务策略？", BLUE),
        ("3", "专家资源", "协调 2–3 名领域专家参与标注、争议裁决和协作成本实验。", AMBER),
        ("4", "数据资源", "争取可公开或匿名发布的 SOP、Schema、API 和变更记录。", GREEN),
        ("5", "实验规范", "确认用户实验规模、agreement 统计和伦理审批要求。", RED),
        ("6", "投稿定位", "分别面向 ontology engineering、NLP extraction 和 agent systems。", NAVY),
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

    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
