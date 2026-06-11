-- ============================================================
-- Flyway Migration: Add current_projection for read model
-- 兼容 MySQL/H2 语法
-- ============================================================

CREATE TABLE IF NOT EXISTS current_projection (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    entity_id VARCHAR(128) NOT NULL COMMENT '实体ID',
    ontology_id VARCHAR(128) NOT NULL COMMENT '本体ID',
    projection_type VARCHAR(32) NOT NULL COMMENT '投影类型: ENTITY/RELATION/STATE',
    json_data TEXT COMMENT '投影JSON数据',
    version BIGINT DEFAULT 1 COMMENT '乐观锁版本号',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_entity_projection (entity_id, projection_type),
    INDEX idx_ontology_id (ontology_id),
    INDEX idx_updated_time (updated_time)
) COMMENT='当前投影表：CQRS读模型';
