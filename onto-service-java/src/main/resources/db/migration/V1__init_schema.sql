-- ============================================================
-- Flyway Migration: Initial Schema for Ontology Service
-- 兼容 Doris/MySQL 语法
-- ============================================================

-- 1. 本体域/图定义表
CREATE TABLE IF NOT EXISTS ontology_domain (
    domain_name VARCHAR(128) NOT NULL COMMENT '本体图名称',
    version VARCHAR(32) NOT NULL COMMENT 'TBOX 版本号',
    ddl_sql TEXT COMMENT '原始 Property Graph / Semantic SQL DDL',
    status VARCHAR(32) COMMENT '版本状态：draft / validated / published / deprecated / archived',
    created_at DATETIME COMMENT '创建时间',
    created_by VARCHAR(128) COMMENT '创建人或发布服务账号',
    ddl_hash VARCHAR(64) COMMENT 'DDL 内容 hash',
    PRIMARY KEY (domain_name, version)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version)
COMMENT '本体域定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 2. 节点类型/对象类型表
CREATE TABLE IF NOT EXISTS ontology_object_type (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    label_name VARCHAR(128) NOT NULL COMMENT '节点类型名称',
    parent_label VARCHAR(128) COMMENT '父类 label',
    display_name VARCHAR(256) COMMENT '面向用户显示的类型名称',
    description TEXT COMMENT '面向人类的简短说明',
    ai_context TEXT COMMENT '面向 LLM 的类型语义',
    PRIMARY KEY (domain_name, version, label_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, label_name)
COMMENT '节点类型定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 3. Object 到 ABOX 映射表
CREATE TABLE IF NOT EXISTS ontology_object_abox_mapping (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    class_name VARCHAR(128) NOT NULL COMMENT 'TBOX class 名称',
    parent_class VARCHAR(128) COMMENT '父类名称',
    mapping_strategy VARCHAR(64) COMMENT '承载策略',
    object_source_name VARCHAR(256) COMMENT 'ABOX 对象源名称',
    source_kind VARCHAR(64) COMMENT '对象源类型',
    primary_key VARCHAR(128) COMMENT '主键列',
    discriminator_column VARCHAR(128) COMMENT '类型判别列',
    type_filter_sql TEXT COMMENT '子类实例过滤条件',
    property_projection_json TEXT COMMENT '属性投影 JSON',
    view_sql TEXT COMMENT '视图定义 SQL',
    materialization_strategy VARCHAR(64) COMMENT '物化策略',
    ai_context TEXT COMMENT '面向 LLM 的说明',
    PRIMARY KEY (domain_name, version, class_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, class_name)
COMMENT 'Object 到 ABOX 映射表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 4. 属性定义表
CREATE TABLE IF NOT EXISTS ontology_property (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    owner_label VARCHAR(128) NOT NULL COMMENT '属性所属类型',
    property_name VARCHAR(128) NOT NULL COMMENT '语义属性名',
    value_type VARCHAR(64) COMMENT '属性值类型',
    column_name VARCHAR(128) COMMENT '直接映射的物理列',
    expression_sql TEXT COMMENT '派生属性表达式',
    is_measure BOOLEAN COMMENT '是否为聚合指标',
    semantic_role VARCHAR(64) COMMENT '语义角色',
    hidden BOOLEAN DEFAULT FALSE COMMENT '是否默认隐藏',
    description TEXT COMMENT '面向人类的简短说明',
    ai_context TEXT COMMENT '面向 LLM 的业务含义',
    PRIMARY KEY (domain_name, version, owner_label, property_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, owner_label, property_name)
COMMENT '属性定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 5. 关系定义表
CREATE TABLE IF NOT EXISTS ontology_relationship (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    label_name VARCHAR(128) NOT NULL COMMENT '关系名称',
    edge_table VARCHAR(256) COMMENT '承载关系的边表',
    source_label VARCHAR(128) NOT NULL COMMENT '关系源类型',
    target_label VARCHAR(128) NOT NULL COMMENT '关系目标类型',
    source_key VARCHAR(128) COMMENT 'source 实例 ID 列',
    target_key VARCHAR(128) COMMENT 'target 实例 ID 列',
    outgoing_name VARCHAR(128) COMMENT 'source 侧导航伪列名',
    incoming_name VARCHAR(128) COMMENT 'target 侧反向导航伪列名',
    outgoing_is_multi BOOLEAN COMMENT 'source 侧是否为 MULTIROW',
    incoming_is_multi BOOLEAN COMMENT 'target 侧是否为 MULTIROW',
    cardinality VARCHAR(64) COMMENT '关系基数',
    ai_context TEXT COMMENT '面向 LLM 的业务语义',
    PRIMARY KEY (domain_name, version, label_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, label_name)
COMMENT '关系定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 6. Logic 规则定义表
CREATE TABLE IF NOT EXISTS ontology_logic (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    target_type VARCHAR(128) COMMENT '作用目标类型',
    target_property VARCHAR(128) COMMENT '输出属性',
    logic_kind VARCHAR(64) COMMENT '类型',
    implementation_type VARCHAR(64) COMMENT '实现方式',
    expression_sql TEXT COMMENT 'SQL 表达式',
    udf_name VARCHAR(256) COMMENT 'UDF 名称',
    python_entrypoint VARCHAR(512) COMMENT 'Python 入口引用',
    service_endpoint VARCHAR(512) COMMENT '服务 endpoint',
    deterministic BOOLEAN COMMENT '是否确定性',
    execution_mode_hint VARCHAR(64) COMMENT '执行模式提示',
    external_binding_name VARCHAR(256) COMMENT '外部执行绑定名称',
    output_type VARCHAR(64) COMMENT '输出类型',
    ai_context TEXT COMMENT '面向 LLM 的规则含义',
    PRIMARY KEY (domain_name, version, logic_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name)
COMMENT 'Logic 规则定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 7. Logic 依赖表
CREATE TABLE IF NOT EXISTS ontology_logic_dependency (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    dependency_kind VARCHAR(64) COMMENT '依赖类型',
    dependency_name VARCHAR(256) COMMENT '依赖名称',
    dependency_path VARCHAR(512) COMMENT '跨关系路径',
    required BOOLEAN COMMENT '是否必需',
    description TEXT COMMENT '依赖说明',
    PRIMARY KEY (domain_name, version, logic_name, dependency_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name, dependency_name)
COMMENT 'Logic 依赖表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 8. Logic 外部执行绑定表
CREATE TABLE IF NOT EXISTS ontology_logic_execution_binding (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    platform_name VARCHAR(128) COMMENT '外部平台名称',
    platform_job_ref VARCHAR(512) COMMENT '外部平台任务 ID',
    platform_output_ref VARCHAR(512) COMMENT '外部平台输出引用',
    result_table VARCHAR(256) COMMENT '写回结果表',
    execution_mode_hint VARCHAR(64) COMMENT '执行模式提示',
    trigger_rule_ref VARCHAR(512) COMMENT '触发规则引用',
    enabled BOOLEAN COMMENT '该绑定是否可用',
    owner VARCHAR(128) COMMENT '负责人',
    observability_ref VARCHAR(512) COMMENT '监控地址引用',
    PRIMARY KEY (domain_name, version, logic_name, platform_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name, platform_name)
COMMENT 'Logic 外部执行绑定表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 9. Logic 解释模板表
CREATE TABLE IF NOT EXISTS ontology_logic_explanation (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    language VARCHAR(32) NOT NULL COMMENT '解释语言',
    template_text TEXT COMMENT '解释模板',
    evidence_schema_json TEXT COMMENT 'evidence 结构说明',
    ai_context TEXT COMMENT '面向 LLM 的解释边界',
    PRIMARY KEY (domain_name, version, logic_name, language)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name, language)
COMMENT 'Logic 解释模板表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 10. Action 定义表
CREATE TABLE IF NOT EXISTS ontology_action (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    action_name VARCHAR(128) NOT NULL COMMENT 'Action 名称',
    tool_name VARCHAR(128) COMMENT '暴露给 LLM 的工具名',
    target_type VARCHAR(128) COMMENT '目标对象类型',
    input_schema_json TEXT COMMENT '输入 schema',
    output_schema_json TEXT COMMENT '输出 schema',
    precondition_sql TEXT COMMENT '前置条件 SQL',
    precondition_logic VARCHAR(256) COMMENT '前置条件引用的 logic',
    external_platform VARCHAR(128) COMMENT '外部平台名称',
    external_action_ref VARCHAR(512) COMMENT '外部 action 引用',
    invocation_mode VARCHAR(64) COMMENT '调用模式',
    dry_run_required BOOLEAN COMMENT '是否必须先 dry-run',
    ai_context TEXT COMMENT '面向 LLM 的调用时机',
    PRIMARY KEY (domain_name, version, action_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, action_name)
COMMENT 'Action 定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- 11. Action 外部绑定表
CREATE TABLE IF NOT EXISTS ontology_action_binding (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    action_name VARCHAR(128) NOT NULL COMMENT 'Action 名称',
    platform_name VARCHAR(128) NOT NULL COMMENT '外部平台名称',
    platform_action_ref VARCHAR(512) COMMENT '外部 action ID',
    dry_run_ref VARCHAR(512) COMMENT 'dry-run endpoint 引用',
    result_ref VARCHAR(512) COMMENT '执行结果查询引用',
    observability_ref VARCHAR(512) COMMENT '监控地址引用',
    enabled BOOLEAN COMMENT '该绑定是否可用',
    PRIMARY KEY (domain_name, version, action_name, platform_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, action_name, platform_name)
COMMENT 'Action 外部绑定表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

-- ABOX 表

-- 推理事实表
CREATE TABLE IF NOT EXISTS semantic_fact (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '使用的 TBOX 版本',
    object_type VARCHAR(128) NOT NULL COMMENT '对象类型',
    object_id VARCHAR(256) NOT NULL COMMENT '对象 ID',
    property_name VARCHAR(128) NOT NULL COMMENT '推理属性',
    value_type VARCHAR(64) COMMENT '值类型',
    value_string VARCHAR(4096) COMMENT '字符串值',
    value_number DOUBLE COMMENT '数值',
    value_bool BOOLEAN COMMENT '布尔值',
    value_json JSON COMMENT '复杂值 JSON',
    computed_by_logic VARCHAR(256) COMMENT '生成该事实的 logic_name',
    computed_at DATETIME COMMENT '计算时间',
    valid_from DATETIME COMMENT '事实生效开始时间',
    valid_to DATETIME COMMENT '事实生效结束时间',
    evidence_json JSON COMMENT '证据 JSON',
    provenance_json JSON COMMENT '数据来源 JSON',
    PRIMARY KEY (domain_name, version, object_type, object_id, property_name)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, object_type, object_id, property_name)
COMMENT '推理事实表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES ("enable_unique_key_merge_on_write" = "true");

-- Logic 运行记录表
CREATE TABLE IF NOT EXISTS semantic_logic_run (
    run_id VARCHAR(64) NOT NULL COMMENT '运行 ID',
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '使用的 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    execution_mode_hint VARCHAR(64) COMMENT '执行模式提示',
    external_platform VARCHAR(128) COMMENT '外部平台名称',
    external_job_ref VARCHAR(512) COMMENT '外部平台任务引用',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '结束时间',
    status VARCHAR(32) COMMENT '状态',
    input_count INT COMMENT '输入对象数量',
    output_count INT COMMENT '输出事实数量',
    error_message TEXT COMMENT '失败信息',
    metrics_json JSON COMMENT '运行指标 JSON',
    PRIMARY KEY (run_id)
) ENGINE = OLAP
UNIQUE KEY(run_id)
COMMENT 'Logic 运行记录表'
DISTRIBUTED BY HASH(run_id) BUCKETS 3
PROPERTIES ("enable_unique_key_merge_on_write" = "true");

-- Action 实例表
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
    status VARCHAR(32) COMMENT '状态',
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
COMMENT 'Action 实例表'
DISTRIBUTED BY HASH(action_id) BUCKETS 3
PROPERTIES ("enable_unique_key_merge_on_write" = "true");
