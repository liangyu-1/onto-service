-- ============================================================
-- TPCH dataset (SF 0.01) tables in Doris (ontology database)
-- Data source: https://github.com/little-big-h/TPCH-SF-001 (public)
-- ============================================================

CREATE DATABASE IF NOT EXISTS ontology;
USE ontology;

DROP TABLE IF EXISTS tpch_customer;
DROP TABLE IF EXISTS tpch_orders;
DROP TABLE IF EXISTS tpch_lineitem;
DROP TABLE IF EXISTS tpch_part;
DROP TABLE IF EXISTS tpch_supplier;
DROP TABLE IF EXISTS tpch_partsupp;
DROP TABLE IF EXISTS tpch_nation;
DROP TABLE IF EXISTS tpch_region;

CREATE TABLE tpch_customer (
  c_custkey INT,
  c_name VARCHAR(128),
  c_address VARCHAR(256),
  c_nationkey INT,
  c_phone VARCHAR(32),
  c_acctbal DOUBLE,
  c_mktsegment VARCHAR(16),
  c_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(c_custkey)
DISTRIBUTED BY HASH(c_custkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_orders (
  o_orderkey INT,
  o_custkey INT,
  o_orderstatus VARCHAR(1),
  o_totalprice DOUBLE,
  o_orderdate DATE,
  o_orderpriority VARCHAR(16),
  o_clerk VARCHAR(16),
  o_shippriority INT,
  o_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(o_orderkey)
DISTRIBUTED BY HASH(o_orderkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_lineitem (
  l_orderkey INT,
  l_linenumber INT,
  l_partkey INT,
  l_suppkey INT,
  l_quantity DOUBLE,
  l_extendedprice DOUBLE,
  l_discount DOUBLE,
  l_tax DOUBLE,
  l_returnflag VARCHAR(1),
  l_linestatus VARCHAR(1),
  l_shipdate DATE,
  l_commitdate DATE,
  l_receiptdate DATE,
  l_shipinstruct VARCHAR(32),
  l_shipmode VARCHAR(16),
  l_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(l_orderkey, l_linenumber)
DISTRIBUTED BY HASH(l_orderkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_part (
  p_partkey INT,
  p_name VARCHAR(128),
  p_mfgr VARCHAR(32),
  p_brand VARCHAR(16),
  p_type VARCHAR(64),
  p_size INT,
  p_container VARCHAR(16),
  p_retailprice DOUBLE,
  p_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(p_partkey)
DISTRIBUTED BY HASH(p_partkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_supplier (
  s_suppkey INT,
  s_name VARCHAR(128),
  s_address VARCHAR(256),
  s_nationkey INT,
  s_phone VARCHAR(32),
  s_acctbal DOUBLE,
  s_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(s_suppkey)
DISTRIBUTED BY HASH(s_suppkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_partsupp (
  ps_partkey INT,
  ps_suppkey INT,
  ps_availqty INT,
  ps_supplycost DOUBLE,
  ps_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(ps_partkey, ps_suppkey)
DISTRIBUTED BY HASH(ps_partkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_nation (
  n_nationkey INT,
  n_name VARCHAR(32),
  n_regionkey INT,
  n_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(n_nationkey)
DISTRIBUTED BY HASH(n_nationkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

CREATE TABLE tpch_region (
  r_regionkey INT,
  r_name VARCHAR(32),
  r_comment VARCHAR(512)
) ENGINE=OLAP
DUPLICATE KEY(r_regionkey)
DISTRIBUTED BY HASH(r_regionkey) BUCKETS 1
PROPERTIES ("replication_num"="1");

