-- ============================================================
-- 本体平台 ABOX (Assertion Box) 数据层 Schema
-- 基于 Doris 存储引擎
-- ============================================================

-- 1. 推理事实表 (ABOX Derived Facts)
CREATE TABLE IF NOT EXISTS semantic_fact (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '使用的 TBOX 版本',
    object_type VARCHAR(128) NOT NULL COMMENT '对象类型，例如 Equipment',
    object_id VARCHAR(256) NOT NULL COMMENT '对象 ID，例如 P1',
    property_name VARCHAR(128) NOT NULL COMMENT '推理属性，例如 security_state',
    value_type VARCHAR(64) COMMENT '值类型，例如 STRING / DOUBLE / BOOL / JSON',
    value_string VARCHAR(4096) COMMENT '字符串值',
    value_number DOUBLE COMMENT '数值',
    value_bool BOOLEAN COMMENT '布尔值',
    value_json JSON COMMENT '复杂值 JSON',
    computed_by_logic VARCHAR(256) COMMENT '生成该事实的 logic_name',
    computed_at DATETIME COMMENT '计算时间',
    valid_from DATETIME COMMENT '事实生效开始时间',
    valid_to DATETIME COMMENT '事实生效结束时间；当前事实可为空',
    evidence_json JSON COMMENT '证据，例如报警数、温度、命中的规则',
    provenance_json JSON COMMENT '数据来源、任务 ID、输入版本等',
    PRIMARY KEY (domain_name, version, object_type, object_id, property_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, object_type, object_id, property_name)
COMMENT '推理事实表，存储规则执行后的派生事实'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "enable_unique_key_merge_on_write" = "true"
);

-- 2. Logic 运行记录表
CREATE TABLE IF NOT EXISTS semantic_logic_run (
    run_id VARCHAR(64) NOT NULL COMMENT '运行 ID',
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '使用的 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    execution_mode_hint VARCHAR(64) COMMENT '执行模式提示',
    external_platform VARCHAR(128) COMMENT '外部大数据平台名称',
    external_job_ref VARCHAR(512) COMMENT '外部平台任务引用',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '结束时间',
    status VARCHAR(32) COMMENT '状态：running / success / failed / skipped',
    input_count INT COMMENT '输入对象数量',
    output_count INT COMMENT '输出事实数量',
    error_message TEXT COMMENT '失败信息',
    metrics_json JSON COMMENT '运行指标，例如耗时、扫描行数',
    PRIMARY KEY (run_id)
) ENGINE = OLAP
UNIQUE KEY(run_id)
COMMENT 'Logic 运行记录表'
DISTRIBUTED BY HASH(run_id) BUCKETS 3
PROPERTIES (
    "enable_unique_key_merge_on_write" = "true"
);

-- 3. Action 实例表
CREATE TABLE IF NOT EXISTS semantic_action_instance (
    action_id VARCHAR(64) NOT NULL COMMENT 'Action 实例 ID',
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '使用的 TBOX 版本',
    action_name VARCHAR(128) NOT NULL COMMENT 'Action 名称',
    tool_name VARCHAR(128) COMMENT 'Tool 名称',
    target_type VARCHAR(128) COMMENT '目标对象类型',
    target_object_id VARCHAR(256) COMMENT '目标对象 ID',
    input_json JSON COMMENT '输入参数',
    dry_run BOOLEAN COMMENT '是否 dry-run',
    status VARCHAR(32) COMMENT '状态：pending / submitted / running / success / failed / cancelled',
    precheck_result_json JSON COMMENT '前置条件检查结果',
    external_request_ref VARCHAR(512) COMMENT '外部平台请求 ID',
    external_result_json JSON COMMENT '外部平台执行结果',
    requested_by VARCHAR(128) COMMENT '请求人',
    requested_by_agent VARCHAR(128) COMMENT '请求 Agent',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间',
    PRIMARY KEY (action_id)
) ENGINE = OLAP
UNIQUE KEY(action_id)
COMMENT 'Action 实例表，记录所有动作执行历史'
DISTRIBUTED BY HASH(action_id) BUCKETS 3
PROPERTIES (
    "enable_unique_key_merge_on_write" = "true"
);

-- 4. AI Context 表 (供 LLM 使用的语义上下文)
CREATE TABLE IF NOT EXISTS ontology_ai_context (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    entity_type VARCHAR(64) NOT NULL COMMENT '实体类型：domain / object_type / property / relationship / logic / action',
    entity_name VARCHAR(256) NOT NULL COMMENT '实体名称',
    context_json JSON COMMENT 'LLM 上下文 JSON，包含语义、别名、使用建议和反例',
    embedding ARRAY<FLOAT> COMMENT '语义嵌入向量',
    updated_at DATETIME COMMENT '更新时间',
    PRIMARY KEY (domain_name, version, entity_type, entity_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, entity_type, entity_name)
COMMENT 'AI Context 表，供 LLM grounding 使用'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "enable_unique_key_merge_on_write" = "true"
);
