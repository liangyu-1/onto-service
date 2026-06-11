-- ============================================================
-- Flyway Migration: Add tbox_rebuild_task for OaaS
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS tbox_rebuild_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    task_id VARCHAR(128) NOT NULL UNIQUE COMMENT '任务唯一标识',
    ontology_id VARCHAR(128) NOT NULL COMMENT '本体ID',
    object_type VARCHAR(32) COMMENT '对象类型',
    scope VARCHAR(32) NOT NULL COMMENT '重建范围: SINGLE_OBJECT/BATCH_BY_TYPE/FULL_REBUILD',
    status VARCHAR(32) DEFAULT 'PENDING' COMMENT '状态: PENDING/RUNNING/SUCCESS/FAILED',
    total_count BIGINT DEFAULT 0 COMMENT '总记录数',
    processed_count BIGINT DEFAULT 0 COMMENT '已处理数',
    failed_count BIGINT DEFAULT 0 COMMENT '失败数',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_time DATETIME COMMENT '开始时间',
    completed_time DATETIME COMMENT '完成时间',
    error_message TEXT COMMENT '错误信息',
    INDEX idx_ontology_id (ontology_id),
    INDEX idx_status (status)
) COMMENT='OaaS TBox索引重建任务表';
