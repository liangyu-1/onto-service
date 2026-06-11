CREATE TABLE IF NOT EXISTS tbox_v3_full_sync_checkpoint (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    checkpoint_id VARCHAR(128) NOT NULL UNIQUE,
    timestamp VARCHAR(64),
    domain_count BIGINT DEFAULT 0,
    type_count BIGINT DEFAULT 0,
    property_count BIGINT DEFAULT 0,
    relationship_count BIGINT DEFAULT 0,
    function_count BIGINT DEFAULT 0,
    measure_count BIGINT DEFAULT 0,
    status VARCHAR(32) DEFAULT 'RUNNING',
    started_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_time DATETIME,
    error_message TEXT,
    INDEX idx_status (status)
);
