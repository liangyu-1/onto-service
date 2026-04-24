-- ============================================================
-- Flyway Migration: Add ontology_artifact for RDF/OWL artifacts
-- 兼容 Doris/MySQL 语法（按现有表风格：ENGINE=OLAP + UNIQUE KEY）
-- ============================================================

CREATE TABLE IF NOT EXISTS ontology_artifact (
    domain_name VARCHAR(128) NOT NULL COMMENT '所属本体图名称',
    version VARCHAR(32) NOT NULL COMMENT '所属 TBOX 版本',
    artifact_kind VARCHAR(64) NOT NULL COMMENT '工件类型：rdf_owl 等',
    format VARCHAR(32) NOT NULL COMMENT '内容格式：ttl / rdfxml / jsonld / owl',
    base_iri VARCHAR(512) COMMENT '命名空间/基准 IRI',
    content TEXT COMMENT '原始内容',
    content_hash VARCHAR(64) NOT NULL COMMENT '内容 hash (sha-256 hex)',
    source VARCHAR(32) COMMENT '来源：generated / uploaded',
    created_at DATETIME COMMENT '创建时间',
    created_by VARCHAR(128) COMMENT '创建人',
    PRIMARY KEY (domain_name, version, artifact_kind, format, content_hash)
) ENGINE = OLAP
UNIQUE KEY(domain_name, version, artifact_kind, format, content_hash)
COMMENT '本体工件表：按 domain/version 存 RDF/OWL 等定义工件'
DISTRIBUTED BY HASH(domain_name) BUCKETS 3;

