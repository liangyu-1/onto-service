-- ============================================================
-- Flyway Migration: Add dlq_record for dead letter queue
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS dlq_record (
    dlq_record_id VARCHAR(64) PRIMARY KEY COMMENT '死信记录ID',
    original_event_id VARCHAR(128) NOT NULL COMMENT '原始事件ID',
    event_type VARCHAR(64) COMMENT '事件类型',
    ontology_id VARCHAR(128) COMMENT '本体ID',
    raw_payload TEXT COMMENT '原始消息内容',
    error_reason TEXT COMMENT '错误原因',
    error_code VARCHAR(64) COMMENT '错误码',
    status VARCHAR(32) DEFAULT 'PENDING' COMMENT '状态: PENDING/REPLAYED/ARCHIVED',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_original_event_id (original_event_id),
    INDEX idx_status (status),
    INDEX idx_created_time (created_time)
) COMMENT='死信队列记录表';
