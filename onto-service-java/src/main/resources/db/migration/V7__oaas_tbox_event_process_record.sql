-- ============================================================
-- Flyway Migration: Add tbox_event_process_record for OaaS
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS tbox_event_process_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    event_id VARCHAR(128) NOT NULL UNIQUE COMMENT '事件唯一标识',
    event_sequence BIGINT COMMENT '事件序列号',
    event_type VARCHAR(64) NOT NULL COMMENT '事件类型',
    object_type VARCHAR(32) COMMENT '对象类型',
    object_id VARCHAR(128) COMMENT '对象ID',
    ontology_id VARCHAR(128) NOT NULL COMMENT '本体ID',
    ontology_version VARCHAR(64) COMMENT '本体版本',
    graph_status VARCHAR(32) DEFAULT 'PENDING' COMMENT '图处理状态: PENDING/SUCCESS/FAILED',
    tbox_index_status VARCHAR(32) DEFAULT 'PENDING' COMMENT '索引处理状态: PENDING/SUCCESS/FAILED',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    last_error TEXT COMMENT '最后错误信息',
    kafka_topic VARCHAR(128) COMMENT 'Kafka topic',
    kafka_partition INT COMMENT 'Kafka partition',
    kafka_offset BIGINT COMMENT 'Kafka offset',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_ontology_id (ontology_id),
    INDEX idx_event_type (event_type),
    INDEX idx_object_type (object_type),
    INDEX idx_graph_status (graph_status)
) COMMENT='OaaS TBox事件处理记录表';
