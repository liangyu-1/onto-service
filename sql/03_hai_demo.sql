-- ============================================================
-- HAI demo ABOX tables/views for end-to-end walkthrough
-- Minimal sample only (for smoke tests)
-- ============================================================

-- Create database if needed (Doris MySQL protocol)
CREATE DATABASE IF NOT EXISTS ontology;
USE ontology;

-- Process catalog
CREATE TABLE IF NOT EXISTS hai_process_catalog (
  process_id VARCHAR(32),
  process_name VARCHAR(128)
) ENGINE = OLAP
UNIQUE KEY(process_id)
DISTRIBUTED BY HASH(process_id) BUCKETS 1
PROPERTIES ("replication_num"="1");

-- Point catalog
CREATE TABLE IF NOT EXISTS hai_point_catalog (
  point_tag VARCHAR(128),
  process_id VARCHAR(32),
  point_kind VARCHAR(64)
) ENGINE = OLAP
UNIQUE KEY(point_tag)
DISTRIBUTED BY HASH(point_tag) BUCKETS 1
PROPERTIES ("replication_num"="1");

-- Point sample (already unpivoted)
CREATE TABLE IF NOT EXISTS hai_point_sample (
  ts DATETIME,
  point_tag VARCHAR(128),
  value DOUBLE,
  attack TINYINT
) ENGINE = OLAP
DUPLICATE KEY(ts, point_tag)
DISTRIBUTED BY HASH(point_tag) BUCKETS 1
PROPERTIES ("replication_num"="1");

-- Attack windows
CREATE TABLE IF NOT EXISTS hai_attack_window (
  attack_id VARCHAR(64),
  process_id VARCHAR(32),
  start_ts DATETIME,
  end_ts DATETIME
) ENGINE = OLAP
UNIQUE KEY(attack_id)
DISTRIBUTED BY HASH(attack_id) BUCKETS 1
PROPERTIES ("replication_num"="1");

-- Seed minimal sample
INSERT INTO hai_process_catalog (process_id, process_name) VALUES
  ('P1', 'BoilerProcess')
  ,('P2', 'TurbineProcess');

INSERT INTO hai_point_catalog (point_tag, process_id, point_kind) VALUES
  ('P1_B2004', 'P1', 'SCADA_POINT')
  ,('P2_B2016', 'P2', 'SCADA_POINT');

INSERT INTO hai_point_sample (ts, point_tag, value, attack) VALUES
  ('2026-01-01 10:00:00', 'P1_B2004', 10.0, 0)
  ,('2026-01-01 10:05:00', 'P1_B2004', 12.0, 1)
  ,('2026-01-01 10:06:00', 'P1_B2004', 11.5, 1)
  ,('2026-01-01 10:05:00', 'P2_B2016', 5.0, 0);

INSERT INTO hai_attack_window (attack_id, process_id, start_ts, end_ts) VALUES
  ('HAI-P1-AW-001', 'P1', '2026-01-01 10:05:00', '2026-01-01 10:06:00');

