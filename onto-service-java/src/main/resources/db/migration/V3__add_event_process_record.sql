-- ============================================================
-- Flyway Migration: Add event_process_record for idempotency tracking
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS event_process_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    event_id VARCHAR(128) NOT NULL COMMENT '事件唯一标识',
    event_type VARCHAR(64) NOT NULL COMMENT '事件类型',
    ontology_id VARCHAR(128) COMMENT '本体ID',
    ontology_version VARCHAR(32) COMMENT '本体版本',
    graph_status VARCHAR(32) DEFAULT 'PENDING' COMMENT '图处理状态: PENDING/SUCCESS/FAILED',
    entity_index_status VARCHAR(32) DEFAULT 'PENDING' COMMENT '索引处理状态: PENDING/SUCCESS/FAILED',
    projection_status VARCHAR(32) DEFAULT 'PENDING' COMMENT '投影处理状态: PENDING/SUCCESS/FAILED',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    last_error TEXT COMMENT '最后错误信息',
    kafka_topic VARCHAR(256) COMMENT 'Kafka topic',
    kafka_partition INT COMMENT 'Kafka partition',
    kafka_offset BIGINT COMMENT 'Kafka offset',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_event_id (event_id),
    INDEX idx_ontology_id (ontology_id),
    INDEX idx_created_time (created_time)
) COMMENT='事件处理记录表：幂等性追踪';
