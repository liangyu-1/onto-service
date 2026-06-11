-- ============================================================
-- Flyway Migration: Add full_sync_checkpoint for OaaS
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS full_sync_checkpoint (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    checkpoint_id VARCHAR(128) NOT NULL UNIQUE COMMENT '检查点唯一标识',
    ontology_id VARCHAR(128) NOT NULL COMMENT '本体ID',
    ontology_version VARCHAR(64) COMMENT '本体版本',
    snapshot_id VARCHAR(128) COMMENT '快照ID',
    event_sequence BIGINT COMMENT '事件序列号',
    entity_count BIGINT DEFAULT 0 COMMENT '实体数量',
    relation_count BIGINT DEFAULT 0 COMMENT '关系数量',
    constraint_count BIGINT DEFAULT 0 COMMENT '约束数量',
    function_count BIGINT DEFAULT 0 COMMENT '函数数量',
    rule_count BIGINT DEFAULT 0 COMMENT '规则数量',
    status VARCHAR(32) DEFAULT 'RUNNING' COMMENT '状态: RUNNING/SUCCESS/FAILED',
    started_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    completed_time DATETIME COMMENT '完成时间',
    error_message TEXT COMMENT '错误信息',
    INDEX idx_ontology_id (ontology_id),
    INDEX idx_status (status)
) COMMENT='OaaS全量同步检查点表';
