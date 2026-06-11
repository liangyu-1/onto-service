CREATE TABLE IF NOT EXISTS tbox_v3_event_process_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(128) NOT NULL UNIQUE,
    event_type VARCHAR(64) NOT NULL,
    object_path VARCHAR(512),
    graph_status VARCHAR(32) DEFAULT 'PENDING',
    index_status VARCHAR(32) DEFAULT 'PENDING',
    retry_count INT DEFAULT 0,
    last_error TEXT,
    kafka_topic VARCHAR(128),
    kafka_partition INT,
    kafka_offset BIGINT,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_object_path (object_path),
    INDEX idx_graph_status (graph_status)
);
