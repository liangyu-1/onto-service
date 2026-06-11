#!/usr/bin/env python3
"""Build TBox ontology and Kafka incremental events for identity verification lineage.

The generator intentionally stays conservative:
- DWA daily/monthly table columns are extracted from the target INSERT SELECT
  lists in the provided shell scripts, because those files are not standard DDL.
- Service table columns come from sql/serv_m_identity_verification.sql.
- Kafka envelopes follow the current OaaS consumer format:
  {eventId, eventSequence, eventType, payload:{timestamp, domains, code, message}}.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "dataset" / "identity_verification_lineage"

DOMAIN_KEY = "telecom_identity"
DOMAIN = {
    "name": "telecom_identity",
    "displayName": "电信用户身份核验血缘域",
    "description": (
        "由 serv_m_identity_verification.sql 和 DWA 用户资料日/月脚本抽取的六表 TBox，"
        "覆盖身份核验、每日操作增量、历史过户用户和 DWA 用户资料来源血缘。"
    ),
}

SOURCE_FILES = [
    "sql/serv_m_identity_verification.sql",
    "sql/p_dwa_d_cus_user_info.sh",
    "sql/p_dwa_m_cus_user_info.sh",
]


TABLES = OrderedDict(
    [
        (
            "serv_d_identity_verification",
            {
                "schema": "ubd_serv_fin",
                "table": "serv_d_identity_verification",
                "displayName": "身份核验日快照表",
                "description": (
                    "按手机号聚合的身份核验结果日表，user_infos 保存姓名/证件哈希、入网、使用区间、状态和在网时长。"
                ),
                "displayProperty": "device_number",
                "evidence": "sql/serv_m_identity_verification.sql:create table + insert overwrite",
                "columns": [
                    ("device_number", "string", "手机号明文，目标表主聚合键。"),
                    ("user_infos", "array<struct>", "手机号对应的用户身份信息数组，支持过户历史。"),
                    ("user_infos_cust_name_utf8_md5", "string", "user_infos.cust_name_utf8_md5，姓名 MD5。"),
                    ("user_infos_cert_no_md5", "string", "user_infos.cert_no_md5，证件号 MD5。"),
                    ("user_infos_cust_name_utf8_sha256", "string", "user_infos.cust_name_utf8_sha256，姓名 SHA256。"),
                    ("user_infos_cert_no_sha256", "string", "user_infos.cert_no_sha256，证件号 SHA256。"),
                    ("user_infos_innet_date", "string", "user_infos.innet_date，入网日期。"),
                    ("user_infos_start_date", "string", "user_infos.start_date，手机号使用开始日期。"),
                    ("user_infos_end_date", "string", "user_infos.end_date，手机号使用结束日期。"),
                    ("user_infos_user_status", "string", "user_infos.user_status，用户状态。"),
                    ("user_infos_innet_months", "int", "user_infos.innet_months，在网时长（月）。"),
                    ("date_id", "string", "日分区，格式 yyyyMMdd。"),
                ],
                "pk": ["device_number", "date_id"],
            },
        ),
        (
            "serv_d_identity_operation",
            {
                "schema": "ubd_serv_fin",
                "table": "serv_d_identity_operation",
                "displayName": "身份操作日增量表",
                "description": "每日新入网、过户、离网用户的身份操作增量表，由 DWA 日表过滤后按手机号聚合。",
                "displayProperty": "device_number",
                "evidence": "sql/serv_m_identity_verification.sql:每日增量数据 insert overwrite",
                "columns": [
                    ("device_number", "string", "发生身份操作的手机号。"),
                    ("user_infos", "array<struct>", "当日身份操作涉及的用户身份信息数组。"),
                    ("user_infos_cust_name_utf8_md5", "string", "user_infos.cust_name_utf8_md5，姓名 MD5。"),
                    ("user_infos_cert_no_md5", "string", "user_infos.cert_no_md5，证件号 MD5。"),
                    ("user_infos_cust_name_utf8_sha256", "string", "user_infos.cust_name_utf8_sha256，姓名 SHA256。"),
                    ("user_infos_cert_no_sha256", "string", "user_infos.cert_no_sha256，证件号 SHA256。"),
                    ("user_infos_innet_date", "string", "user_infos.innet_date，入网日期。"),
                    ("user_infos_start_date", "string", "user_infos.start_date，当日脚本中取 innet_date。"),
                    ("user_infos_end_date", "string", "user_infos.end_date，当日脚本中取 close_date。"),
                    ("user_infos_user_status", "string", "user_infos.user_status，用户状态。"),
                    ("user_infos_innet_months", "int", "user_infos.innet_months，在网时长（月）。"),
                    ("date_id", "string", "日分区，格式 yyyyMMdd。"),
                ],
                "pk": ["device_number", "date_id"],
            },
        ),
        (
            "dwa_d_cus_user_info",
            {
                "schema": "ubd_b_dwa",
                "table": "dwa_d_cus_user_info",
                "displayName": "移网用户资料日表",
                "description": "DWA 层移网用户资料日表，是身份核验日快照和身份操作增量的主要来源。",
                "displayProperty": "device_number",
                "evidence": "sql/p_dwa_d_cus_user_info.sh:INSERT overwrite TABLE dwa_d_cus_user_info",
                "columnsFrom": "sql/p_dwa_d_cus_user_info.sh",
                "pk": ["device_number", "date_id", "prov_id"],
            },
        ),
        (
            "dwa_m_cus_user_info",
            {
                "schema": "ubd_b_dwa",
                "table": "dwa_m_cus_user_info",
                "displayName": "移网用户资料月表",
                "description": "DWA 层移网用户资料月表，是历史过户用户清单和过户用户月信息的来源。",
                "displayProperty": "device_number",
                "evidence": "sql/p_dwa_m_cus_user_info.sh:INSERT overwrite TABLE dwa_m_cus_user_info",
                "columnsFrom": "sql/p_dwa_m_cus_user_info.sh",
                "extraColumns": [("month_id", "string", "月分区，格式 yyyyMM。"), ("prov_id", "string", "省分分区。")],
                "pk": ["device_number", "month_id", "prov_id"],
            },
        ),
        (
            "existed_changeuser_user",
            {
                "schema": "ubd_serv_fin",
                "table": "existed_changeuser_user",
                "displayName": "历史过户用户月份清单",
                "description": "从 DWA 月表中筛出的历史过户手机号及其过户前月份，用于回补历史过户用户信息。",
                "displayProperty": "device_number",
                "evidence": "sql/serv_m_identity_verification.sql:create table as select from dwa_m_cus_user_info",
                "columns": [
                    ("device_number", "string", "发生历史过户的手机号。"),
                    ("month_id", "string", "过户日期前一个月的月份，格式 yyyyMM。"),
                ],
                "pk": ["device_number", "month_id"],
            },
        ),
        (
            "serv_m_changeuser_info",
            {
                "schema": "ubd_serv_fin",
                "table": "serv_m_changeuser_info",
                "displayName": "过户用户月信息表",
                "description": "历史过户用户及最新账期的月粒度用户资料，用于计算手机号历史使用区间。",
                "displayProperty": "device_number",
                "evidence": "sql/serv_m_identity_verification.sql:create table + insert overwrite",
                "columns": [
                    ("device_number", "string", "手机号明文。"),
                    ("cust_name_utf8_md5", "string", "姓名 MD5。"),
                    ("cert_no_md5", "string", "证件号 MD5。"),
                    ("cust_name_utf8_sha256", "string", "姓名 SHA256。"),
                    ("cert_no_sha256", "string", "证件号 SHA256。"),
                    ("is_innet", "string", "是否在网，脚本按 1/0 判断。"),
                    ("innet_date", "string", "入网日期。"),
                    ("user_status", "string", "用户状态。"),
                    ("innet_months", "int", "在网时长（月）。"),
                    ("close_date", "string", "离网/结束日期。"),
                    ("changeuser_date", "string", "过户日期。"),
                    ("month_id", "string", "月分区，格式 yyyyMM。"),
                ],
                "pk": ["device_number", "month_id"],
            },
        ),
    ]
)


IMPORTANT_COLUMNS = {
    "device_number": ("手机号", "手机号明文，血缘脚本中用于聚合、过滤和表间关联。"),
    "date_id": ("日分区", "日分区，格式 yyyyMMdd。"),
    "month_id": ("月分区", "月分区，格式 yyyyMM。"),
    "prov_id": ("省分", "省分分区。"),
    "cust_name_utf8_md5": ("姓名MD5", "姓名 UTF-8 编码后的 MD5 哈希值。"),
    "cert_no_md5": ("证件号MD5", "证件号码 MD5 哈希值。"),
    "cust_name_utf8_sha256": ("姓名SHA256", "姓名 UTF-8 编码后的 SHA256 哈希值。"),
    "cert_no_sha256": ("证件号SHA256", "证件号码 SHA256 哈希值。"),
    "innet_date": ("入网日期", "用户入网日期，格式通常为 yyyyMMdd。"),
    "close_date": ("离网日期", "用户离网或结束日期。"),
    "changeuser_date": ("过户日期", "手机号过户发生日期。"),
    "is_innet": ("是否在网", "是否在网，血缘脚本按 1/0 判断。"),
    "user_status": ("用户状态", "用户状态编码，血缘脚本中 11 表示在网条件之一。"),
    "innet_months": ("在网时长", "用户在网时长（月）。"),
    "is_this_break": ("当日离网标记", "是否为当日离网，血缘脚本用于筛选离网增量。"),
    "rn": ("排序序号", "DWA 脚本用于选择手机号最新记录的排序序号。"),
    "cert_usernums": ("证件关联号码数", "同一证件号关联的手机号数量。"),
    "cert_innet_usernums": ("证件在网号码数", "同一证件号关联且在网的手机号数量。"),
    "cert_break_usernums": ("证件离网号码数", "cert_usernums - cert_innet_usernums。"),
}

INT_COLUMNS = {
    "innet_months",
    "cust_age",
    "cert_no_length",
    "rn",
    "cert_usernums",
    "cert_innet_usernums",
    "cert_break_usernums",
}


RELATIONSHIPS = [
    {
        "owner": "dwa_d_cus_user_info",
        "key": "feeds_identity_verification_initial",
        "name": "日表生成身份核验初始快照",
        "description": "serv_d_identity_verification 初始日分区从 DWA 日表按 device_number 聚合 user_infos。",
        "target": "serv_d_identity_verification",
        "cardinality": "many2one",
        "links": [("dwa_d_cus_user_info.device_number", "serv_d_identity_verification.device_number")],
    },
    {
        "owner": "dwa_d_cus_user_info",
        "key": "feeds_identity_operation_daily_delta",
        "name": "日表生成身份操作增量",
        "description": "serv_d_identity_operation 每日增量从 DWA 日表过滤新入网、过户、离网用户后聚合。",
        "target": "serv_d_identity_operation",
        "cardinality": "many2one",
        "links": [("dwa_d_cus_user_info.device_number", "serv_d_identity_operation.device_number")],
    },
    {
        "owner": "dwa_m_cus_user_info",
        "key": "feeds_existed_changeuser_user",
        "name": "月表生成历史过户清单",
        "description": "existed_changeuser_user 从 DWA 月表筛选 changeuser_date >= 20230701 的手机号并推导过户前月份。",
        "target": "existed_changeuser_user",
        "cardinality": "many2one",
        "links": [
            ("dwa_m_cus_user_info.device_number", "existed_changeuser_user.device_number"),
            ("dwa_m_cus_user_info.month_id", "existed_changeuser_user.month_id"),
        ],
    },
    {
        "owner": "existed_changeuser_user",
        "key": "joins_serv_m_changeuser_info",
        "name": "过户清单关联生成过户月信息",
        "description": "serv_m_changeuser_info 按 existed_changeuser_user.device_number 关联 DWA 月表回补历史过户用户资料。",
        "target": "serv_m_changeuser_info",
        "cardinality": "one2many",
        "links": [
            ("existed_changeuser_user.device_number", "serv_m_changeuser_info.device_number"),
            ("existed_changeuser_user.month_id", "serv_m_changeuser_info.month_id"),
        ],
    },
    {
        "owner": "dwa_m_cus_user_info",
        "key": "feeds_serv_m_changeuser_info",
        "name": "月表生成过户用户月信息",
        "description": "serv_m_changeuser_info 从 DWA 月表取用户身份哈希、在网状态、入网/离网/过户日期等字段。",
        "target": "serv_m_changeuser_info",
        "cardinality": "many2one",
        "links": [
            ("dwa_m_cus_user_info.device_number", "serv_m_changeuser_info.device_number"),
            ("dwa_m_cus_user_info.month_id", "serv_m_changeuser_info.month_id"),
        ],
    },
    {
        "owner": "serv_m_changeuser_info",
        "key": "feeds_identity_verification_historical_stock",
        "name": "过户月信息生成历史存量核验",
        "description": "历史存量 identity_verification 从 serv_m_changeuser_info 计算 start_date/end_date 后按手机号聚合。",
        "target": "serv_d_identity_verification",
        "cardinality": "many2one",
        "links": [("serv_m_changeuser_info.device_number", "serv_d_identity_verification.device_number")],
    },
    {
        "owner": "serv_d_identity_operation",
        "key": "merges_into_identity_verification_daily_update",
        "name": "每日操作增量并入身份核验快照",
        "description": "每日更新用 serv_d_identity_operation 与上一日 serv_d_identity_verification explode 后 union all，再 collect_set。",
        "target": "serv_d_identity_verification",
        "cardinality": "many2one",
        "links": [("serv_d_identity_operation.device_number", "serv_d_identity_verification.device_number")],
    },
    {
        "owner": "serv_d_identity_verification",
        "key": "previous_snapshot_merges_into_next_snapshot",
        "name": "上一日身份核验快照并入下一日",
        "description": "每日更新读取上一分区 serv_d_identity_verification 作为历史快照来源。",
        "target": "serv_d_identity_verification",
        "cardinality": "one2one",
        "links": [("serv_d_identity_verification.device_number", "serv_d_identity_verification.device_number")],
    },
]


FUNCTIONS = OrderedDict(
    [
        (
            "dwa_d_cus_user_info",
            {
                "dwa_daily_materialization": {
                    "name": "DWA日表加工",
                    "description": "从省分用户资料日表加工 DWA 用户资料日表，并生成证件关联号码统计。",
                    "dimensions": ["dwa_d_cus_user_info.device_number", "dwa_d_cus_user_info.date_id"],
                    "rules": {
                        "materialize_from_prov_daily": {
                            "name": "省分日表加工规则",
                            "description": "p_dwa_d_cus_user_info.sh 的目标表写入逻辑。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_b_dwa.dwa_d_cus_user_info PARTITION (date_id, prov_id) "
                                "SELECT device_number, user_id, cust_id, ..., "
                                "size(collect_set(device_number) over(partition by cert_no_md5)) AS cert_usernums, "
                                "size(collect_set(case when is_innet='1' then device_number else null end) over(partition by cert_no_md5)) AS cert_innet_usernums "
                                "FROM ubd_b_dwa.dwa_d_cus_user_info_prov WHERE date_id = ${v_date};"
                            ),
                            "source": "sql/p_dwa_d_cus_user_info.sh",
                        }
                    },
                }
            },
        ),
        (
            "dwa_m_cus_user_info",
            {
                "dwa_monthly_materialization": {
                    "name": "DWA月表加工",
                    "description": "从 DWA 日表、客户资料月表和 CB 用户资料月表加工 DWA 用户资料月表。",
                    "dimensions": ["dwa_m_cus_user_info.device_number", "dwa_m_cus_user_info.month_id"],
                    "rules": {
                        "materialize_from_daily_and_month_sources": {
                            "name": "日表与月源关联规则",
                            "description": "p_dwa_m_cus_user_info.sh 的目标表写入逻辑。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_b_dwa.dwa_m_cus_user_info PARTITION (month_id=${v_month}, prov_id=${v_prov}) "
                                "SELECT t1.device_number, t1.user_id, ..., t2.cert_no_is_valid, t3.is_group, t3.innet_flag "
                                "FROM ubd_b_dwa.dwa_d_cus_user_info t1 "
                                "LEFT JOIN ubd_b_dwa.dwa_m_cus_cust_info t2 ON t1.cust_id_prov_sys = t2.cust_id_prov_sys "
                                "LEFT JOIN ubd_b_ods.ods_m_cus_cb_user_info t3 ON t1.user_id_prov_sys = t3.user_id_prov_sys;"
                            ),
                            "source": "sql/p_dwa_m_cus_user_info.sh",
                        }
                    },
                }
            },
        ),
        (
            "serv_d_identity_operation",
            {
                "identity_operation_daily_delta": {
                    "name": "身份操作每日增量加工",
                    "description": "筛选每日新入网、过户、离网用户并聚合为 user_infos。",
                    "dimensions": ["serv_d_identity_operation.device_number", "serv_d_identity_operation.date_id"],
                    "rules": {
                        "daily_delta_from_dwa_d": {
                            "name": "每日身份操作增量规则",
                            "description": "从 DWA 日表按业务条件筛选每日身份操作。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_serv_fin.serv_d_identity_operation PARTITION (date_id=${date_id}) "
                                "SELECT device_number, collect_list(named_struct('cust_name_utf8_md5', cust_name_utf8_md5, "
                                "'cert_no_md5', cert_no_md5, 'cust_name_utf8_sha256', cust_name_utf8_sha256, "
                                "'cert_no_sha256', cert_no_sha256, 'innet_date', innet_date, 'start_date', innet_date, "
                                "'end_date', close_date, 'user_status', user_status, 'innet_months', innet_months)) AS user_infos "
                                "FROM ubd_b_dwa.dwa_d_cus_user_info "
                                "WHERE date_id=${date_id} AND (((innet_date=${date_id} OR changeuser_date=${date_id}) "
                                "AND is_innet=1 AND user_status=11) OR (is_this_break=1 AND close_date >= '20170101')) "
                                "AND device_number rlike '^[1][3-9][0-9]{9}$' "
                                "AND length(cust_name_utf8_md5)>0 AND length(cert_no_md5)>0 "
                                "AND length(cust_name_utf8_sha256)>0 AND length(cert_no_sha256)>0 GROUP BY device_number;"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        }
                    },
                }
            },
        ),
        (
            "existed_changeuser_user",
            {
                "changeuser_month_index": {
                    "name": "历史过户月份清单加工",
                    "description": "从 DWA 月表筛选历史过户手机号，并计算过户前一个月。",
                    "dimensions": ["existed_changeuser_user.device_number", "existed_changeuser_user.month_id"],
                    "rules": {
                        "derive_previous_month_for_changeuser": {
                            "name": "过户前月份推导规则",
                            "description": "changeuser_date 减一个月后取 yyyyMM，得到历史回补月份。",
                            "definition": (
                                "CREATE TABLE ubd_serv_fin.existed_changeuser_user AS "
                                "SELECT device_number, substr(date_format(add_months(from_unixtime(unix_timestamp(changeuser_date,'yyyyMMdd')),-1),'yyyyMMdd'),1,6) AS month_id "
                                "FROM ubd_b_dwa.dwa_m_cus_user_info "
                                "WHERE month_id='202505' AND changeuser_date >= '20230701' "
                                "AND device_number rlike '^[1][3-9][0-9]{9}$' "
                                "AND length(cust_name_utf8_md5)>0 AND length(cert_no_md5)>0 "
                                "AND length(cust_name_utf8_sha256)>0 AND length(cert_no_sha256)>0 "
                                "GROUP BY device_number, substr(month_id,1,6);"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        }
                    },
                }
            },
        ),
        (
            "serv_m_changeuser_info",
            {
                "changeuser_monthly_enrichment": {
                    "name": "过户用户月信息加工",
                    "description": "用历史过户月份清单关联 DWA 月表，并补充最新账期过户用户资料。",
                    "dimensions": ["serv_m_changeuser_info.device_number", "serv_m_changeuser_info.month_id"],
                    "rules": {
                        "monthly_join_from_existed_and_dwa_m": {
                            "name": "历史过户月信息关联规则",
                            "description": "按 device_number 将 existed_changeuser_user 与 DWA 月表关联。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_serv_fin.serv_m_changeuser_info PARTITION (month_id=${month_id}) "
                                "SELECT b.* FROM (SELECT * FROM ubd_serv_fin.existed_changeuser_user WHERE month_id=${month_id}) a "
                                "JOIN (SELECT device_number, cust_name_utf8_md5, cert_no_md5, cust_name_utf8_sha256, cert_no_sha256, "
                                "is_innet, innet_date, user_status, innet_months, close_date, changeuser_date "
                                "FROM ubd_b_dwa.dwa_m_cus_user_info WHERE month_id=${month_id} "
                                "AND length(cust_name_utf8_md5)>0 AND length(cert_no_md5)>0 "
                                "AND length(cust_name_utf8_sha256)>0 AND length(cert_no_sha256)>0) b "
                                "ON a.device_number = b.device_number;"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        },
                        "current_month_from_dwa_m": {
                            "name": "最新账期月信息规则",
                            "description": "直接从 DWA 月表写入最新账期的过户用户信息。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_serv_fin.serv_m_changeuser_info PARTITION (month_id='202505') "
                                "SELECT device_number, cust_name_utf8_md5, cert_no_md5, cust_name_utf8_sha256, cert_no_sha256, "
                                "is_innet, innet_date, user_status, innet_months, close_date, changeuser_date "
                                "FROM ubd_b_dwa.dwa_m_cus_user_info WHERE month_id='202505' "
                                "AND device_number rlike '^[1][3-9][0-9]{9}$' "
                                "AND length(cust_name_utf8_md5)>0 AND length(cert_no_md5)>0 "
                                "AND length(cust_name_utf8_sha256)>0 AND length(cert_no_sha256)>0;"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        },
                    },
                }
            },
        ),
        (
            "serv_d_identity_verification",
            {
                "identity_verification_snapshot_build": {
                    "name": "身份核验快照加工",
                    "description": "生成身份核验历史存量快照，并把每日操作增量并入下一日快照。",
                    "dimensions": ["serv_d_identity_verification.device_number", "serv_d_identity_verification.date_id"],
                    "rules": {
                        "init_daily_snapshot_from_dwa_d": {
                            "name": "初始日快照规则",
                            "description": "从 DWA 日表按 device_number 聚合 user_infos。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_serv_fin.serv_d_identity_verification PARTITION (date_id='20250531') "
                                "SELECT device_number, collect_list(named_struct('cust_name_utf8_md5', cust_name_utf8_md5, "
                                "'cert_no_md5', cert_no_md5, 'cust_name_utf8_sha256', cust_name_utf8_sha256, "
                                "'cert_no_sha256', cert_no_sha256, 'innet_date', innet_date, 'start_date', innet_date, "
                                "'end_date', close_date, 'user_status', user_status, 'innet_months', innet_months)) AS user_infos "
                                "FROM ubd_b_dwa.dwa_d_cus_user_info WHERE date_id='20250531' "
                                "AND innet_date IS NOT NULL AND device_number rlike '^[1][3-9][0-9]{9}$' GROUP BY device_number;"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        },
                        "historical_stock_from_changeuser_info": {
                            "name": "历史存量快照规则",
                            "description": "从 serv_m_changeuser_info 计算在网/离网用户的 start_date/end_date 后聚合。",
                            "definition": (
                                "WITH lastest_innet_user AS (... FROM ubd_serv_fin.serv_m_changeuser_info WHERE is_innet=1 AND month_id='202505'), "
                                "existed_innet_user AS (... LEAD(changeuser_date) OVER(PARTITION BY device_number ORDER BY innet_date, changeuser_date) ...), "
                                "lastest_offnet_user AS (... WHERE is_innet=0 AND month_id='202505'), "
                                "existed_offnet_user AS (... close_date/changeuser_date/innet_date+innet_months >= '20170101' ...) "
                                "INSERT overwrite TABLE ubd_serv_fin.serv_d_identity_verification PARTITION (date_id='20250531') "
                                "SELECT device_number, collect_list(named_struct(...)) AS user_infos "
                                "FROM (SELECT ... FROM existed_innet_user UNION ALL SELECT ... FROM existed_offnet_user) a GROUP BY device_number;"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        },
                        "daily_merge_operation_with_previous_snapshot": {
                            "name": "每日快照合并规则",
                            "description": "把当日操作增量与上一日身份核验快照展开后合并去重。",
                            "definition": (
                                "INSERT overwrite TABLE ubd_serv_fin.serv_d_identity_verification PARTITION (date_id='20250609') "
                                "SELECT device_number, collect_set(infos) AS user_infos "
                                "FROM (SELECT device_number, infos FROM ubd_serv_fin.serv_d_identity_operation "
                                "LATERAL VIEW explode(user_infos) T AS infos "
                                "UNION ALL SELECT device_number, infos FROM ubd_serv_fin.serv_d_identity_verification "
                                "LATERAL VIEW explode(user_infos) T AS infos WHERE date_id='20250531') a GROUP BY device_number;"
                            ),
                            "source": "sql/serv_m_identity_verification.sql",
                        },
                    },
                }
            },
        ),
    ]
)


def extract_insert_select_columns(script_path: Path, target_table: str) -> list[str]:
    """Extract target columns from the first INSERT SELECT list in a Hive shell script."""
    text = script_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    insert_seen = False
    select_seen = False
    columns: list[str] = []

    for raw_line in lines:
        line = raw_line.split("--", 1)[0].strip()
        if not line:
            continue
        lower = line.lower()
        if not insert_seen:
            if "insert overwrite table" in lower and target_table.lower() in lower:
                insert_seen = True
            continue
        if not select_seen:
            if lower.startswith("select "):
                select_seen = True
                expr = line[7:].strip()
            else:
                continue
        else:
            if lower.startswith("from ") or lower.startswith("from(") or lower.startswith("from\n"):
                break
            expr = line

        if expr.startswith(","):
            expr = expr[1:].strip()
        if not expr:
            continue
        columns.append(normalize_select_expr_to_column(expr))

    return unique([c for c in columns if c])


def normalize_select_expr_to_column(expr: str) -> str | None:
    expr = expr.rstrip(",").strip()
    expr = re.sub(r"\s+", " ", expr)
    alias_match = re.search(r"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$", expr, flags=re.IGNORECASE)
    if alias_match:
        return alias_match.group(1)
    if "." in expr and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$", expr):
        return expr.split(".", 1)[1]
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", expr):
        return expr
    return None


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def infer_type(column: str, explicit_type: str | None = None) -> str:
    if explicit_type:
        return explicit_type
    if column in INT_COLUMNS or column.endswith("_nums") or column.endswith("_age"):
        return "int"
    return "string"


def display_and_description(table_key: str, column: str, explicit_description: str | None = None) -> tuple[str, str]:
    if column in IMPORTANT_COLUMNS:
        display, description = IMPORTANT_COLUMNS[column]
        return display, explicit_description or description
    display = column
    description = explicit_description or f"{TABLES[table_key]['displayName']}字段 {column}；类型由脚本字段列表保守推断。"
    return display, description


def binding(table_key: str, property_key: str) -> dict:
    table = TABLES[table_key]
    column = property_key.replace("user_infos_", "user_infos.")
    return {
        "datasource": 0,
        "schema": table["schema"],
        "database": table["schema"],
        "table": table["table"],
        "column": column,
    }


def property_def(table_key: str, column: str, column_type: str | None = None, description: str | None = None) -> dict:
    display, desc = display_and_description(table_key, column, description)
    return {
        "name": column,
        "displayName": display,
        "type": infer_type(column, column_type),
        "description": desc,
        "binding": binding(table_key, column),
        "pkColumn": column in TABLES[table_key].get("pk", []),
    }


def build_table_columns(table_key: str) -> OrderedDict[str, dict]:
    table = TABLES[table_key]
    columns = OrderedDict()
    if "columns" in table:
        for column, column_type, description in table["columns"]:
            columns[column] = property_def(table_key, column, column_type, description)
    else:
        source = ROOT / table["columnsFrom"]
        parsed = extract_insert_select_columns(source, table["table"])
        for column in parsed:
            columns[column] = property_def(table_key, column)
        for column, column_type, description in table.get("extraColumns", []):
            columns[column] = property_def(table_key, column, column_type, description)
    return columns


def prop_path(ref: str) -> str:
    table_key, column = ref.split(".", 1)
    return f"{DOMAIN_KEY}.{table_key}.properties.{column}"


def relationship_def(item: dict) -> dict:
    return {
        "name": item["name"],
        "displayName": item["name"],
        "description": item["description"],
        "linkProperties": [{prop_path(src): prop_path(dst)} for src, dst in item["links"]],
        "cardinality": item["cardinality"],
        "type": "left_join",
    }


def function_def(table_key: str, function_key: str, item: dict, include_rules: bool) -> dict:
    rules = OrderedDict()
    if include_rules:
        for rule_key, rule in item["rules"].items():
            rules[rule_key] = {
                "name": rule["name"],
                "displayName": rule["name"],
                "description": f"{rule['description']} 证据文件：{rule['source']}。",
                "type": "SQL",
                "definition": rule["definition"],
            }
    return {
        "name": function_key,
        "displayName": item["name"],
        "description": item["description"],
        "type": "SQL",
        "definition": f"lineage function for {TABLES[table_key]['schema']}.{TABLES[table_key]['table']}",
        "dimensions": [prop_path(ref) for ref in item["dimensions"]],
        "rules": rules,
    }


def empty_type(table_key: str) -> dict:
    table = TABLES[table_key]
    return {
        "name": table_key,
        "displayName": table["displayName"],
        "description": f"{table['description']} schemaEvidence={table['evidence']}",
        "displayProperty": table["displayProperty"],
        "properties": {},
        "relationships": {},
        "functions": {},
    }


def build_full_domain() -> dict:
    domain = {**DOMAIN, "types": OrderedDict()}
    for table_key in TABLES:
        type_obj = empty_type(table_key)
        type_obj["properties"] = build_table_columns(table_key)
        domain["types"][table_key] = type_obj

    for rel in RELATIONSHIPS:
        domain["types"][rel["owner"]]["relationships"][rel["key"]] = relationship_def(rel)

    for table_key, functions in FUNCTIONS.items():
        for function_key, function in functions.items():
            domain["types"][table_key]["functions"][function_key] = function_def(
                table_key, function_key, function, include_rules=True
            )
    return domain


def payload(domains: dict, timestamp: str) -> dict:
    return {
        "timestamp": timestamp,
        "domains": domains,
        "code": 200,
        "message": "success",
    }


def envelope(event_type: str, domains: dict, seq: int, run_id: str, timestamp: str, suffix: str) -> dict:
    return {
        "eventId": f"evt_{run_id}_{seq:03d}_{event_type}_{suffix}",
        "eventSequence": str(seq),
        "eventType": event_type,
        "schemaVersion": "1.0",
        "publishTime": timestamp,
        "payload": payload(domains, timestamp),
    }


def domain_wrapper(domain_fragment: dict) -> dict:
    return {DOMAIN_KEY: domain_fragment}


def build_events(run_id: str, timestamp: str) -> list[dict]:
    events = []
    seq = 1

    domain_only = {**DOMAIN, "types": {}}
    events.append(envelope("DOMAIN_UPSERT", domain_wrapper(domain_only), seq, run_id, timestamp, "domain"))
    seq += 1

    for table_key in TABLES:
        domain = {**DOMAIN, "types": OrderedDict()}
        type_obj = empty_type(table_key)
        type_obj["properties"] = build_table_columns(table_key)
        domain["types"][table_key] = type_obj
        events.append(envelope("TYPE_UPSERT", domain_wrapper(domain), seq, run_id, timestamp, table_key))
        seq += 1

    for rel in RELATIONSHIPS:
        domain = {**DOMAIN, "types": OrderedDict()}
        type_obj = empty_type(rel["owner"])
        type_obj["relationships"][rel["key"]] = relationship_def(rel)
        domain["types"][rel["owner"]] = type_obj
        events.append(envelope("RELATIONSHIP_UPSERT", domain_wrapper(domain), seq, run_id, timestamp, rel["key"]))
        seq += 1

    for table_key, functions in FUNCTIONS.items():
        for function_key, function in functions.items():
            domain = {**DOMAIN, "types": OrderedDict()}
            type_obj = empty_type(table_key)
            type_obj["functions"][function_key] = function_def(table_key, function_key, function, include_rules=False)
            domain["types"][table_key] = type_obj
            events.append(envelope("FUNCTION_UPSERT", domain_wrapper(domain), seq, run_id, timestamp, function_key))
            seq += 1

            domain = {**DOMAIN, "types": OrderedDict()}
            type_obj = empty_type(table_key)
            type_obj["functions"][function_key] = function_def(table_key, function_key, function, include_rules=True)
            domain["types"][table_key] = type_obj
            events.append(envelope("RULE_UPSERT", domain_wrapper(domain), seq, run_id, timestamp, function_key))
            seq += 1

    return events


def build_summary(snapshot: dict, events: list[dict], run_id: str) -> dict:
    domain = snapshot["domains"][DOMAIN_KEY]
    type_count = len(domain["types"])
    property_count = sum(len(t["properties"]) for t in domain["types"].values())
    relationship_count = sum(len(t["relationships"]) for t in domain["types"].values())
    function_count = sum(len(t["functions"]) for t in domain["types"].values())
    rule_count = sum(len(f["rules"]) for t in domain["types"].values() for f in t["functions"].values())
    return {
        "runId": run_id,
        "domain": DOMAIN_KEY,
        "sourceFiles": SOURCE_FILES,
        "counts": {
            "events": len(events),
            "domains": 1,
            "types": type_count,
            "properties": property_count,
            "relationships": relationship_count,
            "functions": function_count,
            "rules": rule_count,
        },
        "eventTypes": {event_type: sum(1 for e in events if e["eventType"] == event_type) for event_type in sorted({e["eventType"] for e in events})},
        "tables": [f"{TABLES[k]['schema']}.{TABLES[k]['table']}" for k in TABLES],
    }


def write_readme(out_dir: Path, summary: dict) -> None:
    event_file = "identity_verification_tbox_events.jsonl"
    snapshot_file = "identity_verification_tbox_snapshot.json"
    pretty_file = "identity_verification_tbox_events_pretty.json"
    summary_file = "summary.json"
    lines = [
        "# Identity Verification Lineage TBox Events",
        "",
        "本目录由 `scripts/build_identity_verification_lineage_events.py` 生成，用于把 6 张表的血缘本体变成 OaaS Kafka 增量事件。",
        "",
        "## Files",
        "",
        f"- `{event_file}`: JSONL，每行一个 Kafka value，可直接写入 `ontology_events`。",
        f"- `{pretty_file}`: pretty JSON 数组，便于人工检查。",
        f"- `{snapshot_file}`: 同一份本体的全量快照形态。",
        f"- `{summary_file}`: 事件和对象数量汇总。",
        "",
        "## Counts",
        "",
        f"- events: {summary['counts']['events']}",
        f"- types: {summary['counts']['types']}",
        f"- properties: {summary['counts']['properties']}",
        f"- relationships: {summary['counts']['relationships']}",
        f"- functions: {summary['counts']['functions']}",
        f"- rules: {summary['counts']['rules']}",
        "",
        "## Send",
        "",
        "本地 Kafka 容器方式：",
        "",
        "```bash",
        "docker exec -i onto-kafka /opt/kafka/bin/kafka-console-producer.sh \\",
        "  --bootstrap-server localhost:9092 \\",
        "  --topic ontology_events \\",
        f"  < dataset/identity_verification_lineage/{event_file}",
        "```",
        "",
        "外部 Kafka 客户端方式：",
        "",
        "```bash",
        f"kafka-console-producer.sh --bootstrap-server 172.16.21.72:9092 --topic ontology_events < dataset/identity_verification_lineage/{event_file}",
        "```",
        "",
        "## Notes",
        "",
        "- `sql/p_dwa_d_cus_user_info.sh` 和 `sql/p_dwa_m_cus_user_info.sh` 不是标准 DDL；DWA 字段来自目标 `INSERT SELECT` 列表，类型为保守推断。",
        "- `eventId` 是确定性的；同一批事件重复发送会被幂等逻辑跳过。需要重新处理时，用新的 `--run-id` 重新生成。",
        "",
        "```bash",
        "python3 scripts/build_identity_verification_lineage_events.py --run-id identity_verification_lineage_$(date +%Y%m%d%H%M%S)",
        "```",
        "",
        "- 当前事件使用常规路径 `telecom_identity.<table>.functions.<function>.rules.<rule>`。",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--run-id", default="identity_verification_lineage_v1")
    parser.add_argument("--timestamp", default="2026-06-04T00:00:00Z")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "timestamp": args.timestamp,
        "domains": {DOMAIN_KEY: build_full_domain()},
        "code": "200",
        "message": "success",
    }
    events = build_events(args.run_id, args.timestamp)
    summary = build_summary(snapshot, events, args.run_id)

    (out_dir / "identity_verification_tbox_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "identity_verification_tbox_events_pretty.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out_dir / "identity_verification_tbox_events.jsonl").open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(out_dir, summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
