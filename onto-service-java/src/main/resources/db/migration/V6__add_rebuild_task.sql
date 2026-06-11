-- ============================================================
-- Flyway Migration: Add rebuild_task for index rebuild tracking
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS rebuild_task (
    task_id VARCHAR(64) PRIMARY KEY COMMENT '任务ID',
    ontology_id VARCHAR(128) COMMENT '本体ID',
    entity_type VARCHAR(128) COMMENT '实体类型',
    scope VARCHAR(32) COMMENT '重建范围: SINGLE_ENTITY/BATCH_BY_TYPE/FULL_REBUILD',
    status VARCHAR(32) DEFAULT 'PENDING' COMMENT '状态: PENDING/RUNNING/SUCCESS/FAILED',
    total_count BIGINT DEFAULT 0 COMMENT '总记录数',
    processed_count BIGINT DEFAULT 0 COMMENT '已处理数',
    failed_count BIGINT DEFAULT 0 COMMENT '失败数',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_time TIMESTAMP NULL COMMENT '开始时间',
    completed_time TIMESTAMP NULL COMMENT '完成时间',
    error_message TEXT COMMENT '错误信息',
    INDEX idx_ontology_id (ontology_id),
    INDEX idx_status (status),
    INDEX idx_created_time (created_time)
) COMMENT='索引重建任务表';
