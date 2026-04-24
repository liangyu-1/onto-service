#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

TPCH_REPO_RAW="https://raw.githubusercontent.com/little-big-h/TPCH-SF-001/master"
WORK_DIR="${WORK_DIR:-/tmp/tpch-sf001}"
DB="${DORIS_DB:-ontology}"
# Use Doris BE HTTP port for stream load (on host: 8040). FE redirects to BE internal IP on Docker Desktop.
STREAM_HTTP="${DORIS_STREAM_HTTP:-http://127.0.0.1:8040}"
AUTH_USER="${DORIS_USER:-root}"
AUTH_PASS="${DORIS_PASSWORD:-}"

echo "Initializing TPCH tables + loading public TPCH-SF-001 data..."
echo "Source: ${TPCH_REPO_RAW}"
echo "Work dir: ${WORK_DIR}"
mkdir -p "${WORK_DIR}"

download() {
  local name="$1"
  local url="${TPCH_REPO_RAW}/${name}.tbl"
  local out="${WORK_DIR}/${name}.tbl"
  if [[ -s "${out}" ]]; then
    echo "Using cached ${out}"
    return
  fi
  echo "Downloading ${url}"
  curl -fsSL "${url}" -o "${out}"
}

clean_tbl() {
  local name="$1"
  local in="${WORK_DIR}/${name}.tbl"
  local out="${WORK_DIR}/${name}.clean.tbl"
  # Remove trailing delimiter '|' at end of each line, keep '|' as separator.
  sed 's/|$//' "${in}" > "${out}"
  echo "${out}"
}

stream_load() {
  local table="$1"
  local file="$2"
  local columns="$3"
  local label="tpch_${table}_$(date +%s)"

  echo "Stream loading ${table} from ${file}"
  local url="${STREAM_HTTP}/api/${DB}/${table}/_stream_load"

  # Note: Doris stream load uses HTTP, with headers to define format.
  # We use 'column_separator' as '|', and explicit columns.
  local resp
  resp="$(curl -sS --fail -u "${AUTH_USER}:${AUTH_PASS}" \
    -H "label: ${label}" \
    -H "Expect: 100-continue" \
    -H "column_separator: |" \
    -H "format: csv" \
    -H "strict_mode: false" \
    -H "max_filter_ratio: 0.2" \
    -H "columns: ${columns}" \
    -T "${file}" \
    "${url}")"

  echo "${resp}" | head -c 500
  echo
}

# Download public TPCH SF 0.01 files
download customer
download orders
download lineitem
download part
download supplier
download partsupp
download nation
download region

# Clean files (remove trailing '|')
f_customer="$(clean_tbl customer)"
f_orders="$(clean_tbl orders)"
f_lineitem="$(clean_tbl lineitem)"
f_part="$(clean_tbl part)"
f_supplier="$(clean_tbl supplier)"
f_partsupp="$(clean_tbl partsupp)"
f_nation="$(clean_tbl nation)"
f_region="$(clean_tbl region)"

# Stream load into Doris (tables are created by sql/04_tpch_schema.sql)
stream_load tpch_customer "${f_customer}" "c_custkey,c_name,c_address,c_nationkey,c_phone,c_acctbal,c_mktsegment,c_comment"
stream_load tpch_orders "${f_orders}" "o_orderkey,o_custkey,o_orderstatus,o_totalprice,o_orderdate,o_orderpriority,o_clerk,o_shippriority,o_comment"
stream_load tpch_lineitem "${f_lineitem}" "l_orderkey,l_linenumber,l_partkey,l_suppkey,l_quantity,l_extendedprice,l_discount,l_tax,l_returnflag,l_linestatus,l_shipdate,l_commitdate,l_receiptdate,l_shipinstruct,l_shipmode,l_comment"
stream_load tpch_part "${f_part}" "p_partkey,p_name,p_mfgr,p_brand,p_type,p_size,p_container,p_retailprice,p_comment"
stream_load tpch_supplier "${f_supplier}" "s_suppkey,s_name,s_address,s_nationkey,s_phone,s_acctbal,s_comment"
stream_load tpch_partsupp "${f_partsupp}" "ps_partkey,ps_suppkey,ps_availqty,ps_supplycost,ps_comment"
stream_load tpch_nation "${f_nation}" "n_nationkey,n_name,n_regionkey,n_comment"
stream_load tpch_region "${f_region}" "r_regionkey,r_name,r_comment"

echo "TPCH load done."

