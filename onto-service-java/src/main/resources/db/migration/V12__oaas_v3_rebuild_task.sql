CREATE TABLE IF NOT EXISTS tbox_v3_rebuild_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(128) NOT NULL UNIQUE,
    object_type VARCHAR(32),
    scope VARCHAR(32) NOT NULL,
    status VARCHAR(32) DEFAULT 'PENDING',
    total_count BIGINT DEFAULT 0,
    processed_count BIGINT DEFAULT 0,
    failed_count BIGINT DEFAULT 0,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_time DATETIME,
    completed_time DATETIME,
    error_message TEXT,
    INDEX idx_status (status)
);
