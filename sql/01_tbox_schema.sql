-- ============================================================
-- 本体平台 TBOX (Terminology Box) 数据层 Schema
-- 基于 Doris 存储引擎
-- ============================================================

-- 1. 本体域/图定义表
CREATE TABLE IF NOT EXISTS ontology_domain (
    id VARCHAR(192) NOT NULL COMMENT '复合主键 domain_name:version',
    domain_name VARCHAR(128) NOT NULL COMMENT '本体图名称，例如 PlantGraph',
    version VARCHAR(32) NOT NULL COMMENT 'TBOX 版本号，例如 1.0.0',
    ddl_sql TEXT COMMENT '原始 Property Graph / Semantic SQL DDL',
    status VARCHAR(32) COMMENT '版本状态：draft / validated / published / deprecated / archived',
    created_at DATETIME COMMENT '创建时间',
    created_by VARCHAR(128) COMMENT '创建人或发布服务账号',
    ddl_hash VARCHAR(64) COMMENT 'DDL 内容 hash，用于变更检测和幂等发布',
) ENGINE = OLAP
UNIQUE KEY(id)
COMMENT '本体域定义表，保存 TBOX 的源定义和版本管理'
DISTRIBUTED BY HASH(id) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 2. 节点类型/对象类型表
CREATE TABLE IF NOT EXISTS ontology_object_type (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    label_name VARCHAR(128) NOT NULL COMMENT '节点类型 / class / label 名称，例如 Equipment',
    parent_label VARCHAR(128) COMMENT '父类 label，用于 class 继承，例如 PhysicalAsset',
    display_name VARCHAR(256) COMMENT '面向用户显示的类型名称',
    description TEXT COMMENT '面向人类的简短说明',
    ai_context TEXT COMMENT '面向 LLM 的类型语义、别名、使用建议和反例',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, label_name)
COMMENT '节点类型定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 3. Object 到 ABOX 映射表
CREATE TABLE IF NOT EXISTS ontology_object_abox_mapping (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    class_name VARCHAR(128) NOT NULL COMMENT 'TBOX class / label 名称，例如 BoilerProcess',
    parent_class VARCHAR(128) COMMENT '父类名称，例如 ICSProcess / HAIComponent',
    mapping_strategy VARCHAR(64) COMMENT '承载策略：single_wide_table / class_view / class_table / union_view',
    object_source_name VARCHAR(256) COMMENT 'ABOX 对象源名称，可以是 Doris 物理表、逻辑视图或物化视图',
    source_kind VARCHAR(64) COMMENT '对象源类型：physical_table / logical_view / materialized_view / table_function',
    primary_key VARCHAR(128) COMMENT 'ABOX 对象源主键列，例如 process_id / point_tag',
    discriminator_column VARCHAR(128) COMMENT '单宽表继承的类型判别列，例如 process_id / point_prefix',
    type_filter_sql TEXT COMMENT '子类实例过滤条件，例如 process_id = P1',
    property_projection_json TEXT COMMENT 'class 可见属性到 ABOX 列/表达式的投影 JSON',
    view_sql TEXT COMMENT 'class_view / union_view 的定义 SQL',
    materialization_strategy VARCHAR(64) COMMENT '虚拟表是否物化以及刷新策略，例如 virtual / materialized_5m',
    ai_context TEXT COMMENT '面向 LLM 的说明：实例从哪里来、不要误用哪些列',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, class_name)
COMMENT 'Object 到 ABOX 映射表，class 到 ABOX source 的承载策略'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 4. 属性定义表
CREATE TABLE IF NOT EXISTS ontology_property (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    owner_label VARCHAR(128) NOT NULL COMMENT '属性所属类型 / label，例如 SCADAPoint',
    property_name VARCHAR(128) NOT NULL COMMENT '语义属性名，例如 anomaly_state',
    value_type VARCHAR(64) COMMENT '属性值类型，例如 STRING / DOUBLE / TIMESTAMP',
    column_name VARCHAR(128) COMMENT '直接映射的 Doris 物理列；表达式属性可为空',
    expression_sql TEXT COMMENT '派生属性或 measure 的 GoogleSQL 表达式',
    is_measure TINYINT COMMENT '是否为聚合指标 / measure',
    semantic_role VARCHAR(64) COMMENT '语义角色：identifier / dimension / state / metric',
    semantic_aliases TEXT COMMENT '属性别名数组，辅助 LLM grounding',
    hidden TINYINT COMMENT '是否默认隐藏，适用于敏感字段或内部字段',
    description TEXT COMMENT '面向人类的简短说明',
    ai_context TEXT COMMENT '面向 LLM 的业务含义、使用建议和歧义消解',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, owner_label, property_name)
COMMENT '属性定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 5. 关系定义表
CREATE TABLE IF NOT EXISTS ontology_relationship (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    label_name VARCHAR(128) NOT NULL COMMENT '关系 / 谓语 / edge label 名称，例如 HAS_POINT',
    edge_table VARCHAR(256) COMMENT '承载关系实例的 Doris 边表；FK 型关系可复用 target 表',
    source_label VARCHAR(128) NOT NULL COMMENT '关系源类型，例如 ICSProcess',
    target_label VARCHAR(128) NOT NULL COMMENT '关系目标类型，例如 SCADAPoint',
    source_key VARCHAR(128) COMMENT 'edge_table 中指向 source 实例 ID 的列',
    target_key VARCHAR(128) COMMENT 'edge_table 中指向 target 实例 ID 的列',
    outgoing_name VARCHAR(128) COMMENT 'source 侧导航伪列名，例如 ICSProcess.has_point',
    incoming_name VARCHAR(128) COMMENT 'target 侧反向导航伪列名，例如 SCADAPoint.belongs_to_process',
    outgoing_is_multi TINYINT COMMENT 'TRUE 表示 source.outgoing_name 类型为 MULTIROW<target_label>',
    incoming_is_multi TINYINT COMMENT 'TRUE 表示 target.incoming_name 类型为 MULTIROW<source_label>',
    cardinality VARCHAR(64) COMMENT '关系基数：one_to_one / one_to_many / many_to_one / many_to_many',
    ai_context TEXT COMMENT '该谓语面向 LLM 的业务语义、别名、使用场景和反例',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, label_name)
COMMENT '关系定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 6. Logic 规则定义表
CREATE TABLE IF NOT EXISTS ontology_logic (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称，例如 ICSProcess.security_state',
    target_type VARCHAR(128) COMMENT '作用目标类型，例如 ICSProcess',
    target_property VARCHAR(128) COMMENT '输出属性，例如 security_state',
    logic_kind VARCHAR(64) COMMENT '类型：semantic_property / measure / constraint / state_machine / alert_rule',
    implementation_type VARCHAR(64) COMMENT '实现方式：sql / udf / python / nlp / external_service',
    expression_sql TEXT COMMENT 'SQL 表达式或查询；非 SQL 实现可为空',
    udf_name VARCHAR(256) COMMENT 'UDF 名称；非 UDF 实现可为空',
    python_entrypoint VARCHAR(512) COMMENT '外部平台 Python 入口引用；非 Python 实现可为空',
    service_endpoint VARCHAR(512) COMMENT '外部平台服务 endpoint 引用；非 external_service 可为空',
    deterministic TINYINT COMMENT '是否确定性；影响是否可用于 precondition',
    execution_mode_hint VARCHAR(64) COMMENT '执行模式提示：on_read / materialized / scheduled / event_driven',
    external_binding_name VARCHAR(256) COMMENT '外部执行绑定名称，例如 hai_security_state_job',
    output_type VARCHAR(64) COMMENT '输出类型，例如 STRING / DOUBLE / BOOL / JSON',
    ai_context TEXT COMMENT '面向 LLM 的规则含义、适用场景和反例',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name)
COMMENT 'Logic 规则定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 7. Logic 依赖表
CREATE TABLE IF NOT EXISTS ontology_logic_dependency (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    dependency_name VARCHAR(256) COMMENT '依赖名称，例如 Equipment.active_alarm_count',
    dependency_kind VARCHAR(64) COMMENT '依赖类型：property / relation / measure / table / service',
    dependency_path VARCHAR(512) COMMENT '跨关系路径，例如 Equipment.has_sensor.latest_value',
    required TINYINT COMMENT '是否必需',
    description TEXT COMMENT '依赖说明',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name, dependency_name)
COMMENT 'Logic 依赖表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 8. Logic 外部执行绑定表
CREATE TABLE IF NOT EXISTS ontology_logic_execution_binding (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    platform_name VARCHAR(128) COMMENT '外部大数据平台名称，例如 FoundryLikePlatform',
    platform_job_ref VARCHAR(512) COMMENT '外部平台任务 ID / pipeline ID / function ID',
    platform_output_ref VARCHAR(512) COMMENT '外部平台输出数据集或模型输出引用',
    result_table VARCHAR(256) COMMENT '写回 Doris 的结果表，例如 semantic_fact',
    execution_mode_hint VARCHAR(64) COMMENT '执行模式提示：on_read / materialized / scheduled / event_driven',
    trigger_rule_ref VARCHAR(512) COMMENT '外部平台触发规则引用；本体层不负责调度',
    enabled TINYINT COMMENT '该绑定是否可被本体层使用',
    owner VARCHAR(128) COMMENT '负责人或服务账号',
    observability_ref VARCHAR(512) COMMENT '外部平台运行记录、日志或监控地址引用',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name, platform_name)
COMMENT 'Logic 外部执行绑定表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 9. Logic 解释模板表
CREATE TABLE IF NOT EXISTS ontology_logic_explanation (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    logic_name VARCHAR(256) NOT NULL COMMENT '规则名称',
    language VARCHAR(32) NOT NULL COMMENT '解释语言，例如 zh-CN / en-US',
    template_text TEXT COMMENT '解释模板',
    evidence_schema_json TEXT COMMENT 'evidence_json 的结构说明',
    ai_context TEXT COMMENT '面向 LLM 的解释边界和禁止编造提示',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, logic_name, language)
COMMENT 'Logic 解释模板表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 10. Action 定义表
CREATE TABLE IF NOT EXISTS ontology_action (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    action_name VARCHAR(128) NOT NULL COMMENT 'Action 名称，例如 CreateIncidentTicket',
    tool_name VARCHAR(128) COMMENT '暴露给 LLM 的工具名，例如 create_incident_ticket',
    target_type VARCHAR(128) COMMENT '目标对象类型，例如 AttackWindow / ICSProcess',
    input_schema_json TEXT COMMENT '输入 schema，例如 severity / description / affected_points',
    output_schema_json TEXT COMMENT '输出 schema，例如 incident_id / status',
    precondition_sql TEXT COMMENT '前置条件 SQL，例如 attack_window.status != Closed',
    precondition_logic VARCHAR(256) COMMENT '前置条件引用的 logic，例如 ICSProcess.security_state',
    external_platform VARCHAR(128) COMMENT '外部大数据平台名称，例如 FoundryLikePlatform',
    external_action_ref VARCHAR(512) COMMENT '外部 action / workflow / function 引用',
    invocation_mode VARCHAR(64) COMMENT '调用模式：dry_run_only / submit_request / execute_external',
    dry_run_required TINYINT COMMENT '是否必须先 dry-run',
    ai_context TEXT COMMENT '面向 LLM 的调用时机、禁止调用场景和业务提示',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, action_name)
COMMENT 'Action 定义表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 11. Action 外部绑定表
CREATE TABLE IF NOT EXISTS ontology_action_binding (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    action_name VARCHAR(128) NOT NULL COMMENT 'Action 名称',
    platform_name VARCHAR(128) NOT NULL COMMENT '外部大数据平台名称',
    platform_action_ref VARCHAR(512) COMMENT '外部 action / workflow / function ID',
    dry_run_ref VARCHAR(512) COMMENT '外部 dry-run / preview endpoint 引用',
    result_ref VARCHAR(512) COMMENT '外部执行结果或状态查询引用',
    observability_ref VARCHAR(512) COMMENT '外部运行记录、日志或监控地址引用',
    enabled TINYINT COMMENT '该绑定是否可用',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, action_name, platform_name)
COMMENT 'Action 外部绑定表'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);

-- 12. 本体工件表（RDF/OWL 等）
CREATE TABLE IF NOT EXISTS ontology_artifact (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    artifact_kind VARCHAR(64) NOT NULL COMMENT '工件类型：rdf_owl 等',
    format VARCHAR(32) NOT NULL COMMENT '内容格式：ttl / rdfxml / jsonld / owl',
    base_iri VARCHAR(512) COMMENT '命名空间/基准 IRI',
    content TEXT COMMENT '原始内容',
    content_hash VARCHAR(64) NOT NULL COMMENT '内容 hash (sha-256 hex)',
    source VARCHAR(32) COMMENT '来源：generated / uploaded',
    created_at DATETIME COMMENT '创建时间',
    created_by VARCHAR(128) COMMENT '创建人',
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, artifact_kind, format, content_hash)
COMMENT '本体工件表：按 domain/version 存 RDF/OWL 等定义工件'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3
PROPERTIES (
    "replication_num" = "1"
);
