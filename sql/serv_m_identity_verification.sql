DROP TABLE ubd_serv_fin.serv_d_identity_verification;
create table if not exists ubd_serv_fin.serv_d_identity_verification (
device_number string comment '手机号明文',
user_infos ARRAY<STRUCT<        
  cust_name_utf8_md5: STRING COMMENT '姓名md5',
  cert_no_md5: STRING COMMENT '证件md5',
  cust_name_utf8_sha256: STRING COMMENT '姓名sha256',
  cert_no_sha256: STRING COMMENT '证件sha256',
  innet_date: STRING COMMENT '入网日期',
  start_date: STRING COMMENT '使用开始时间',
  end_date: STRING COMMENT '使用结束时间',
  user_status: STRING COMMENT '当前状态',
  innet_months: INT COMMENT '在网时长'>>
) partitioned by (date_id string)


create table if not exists ubd_serv_fin.serv_d_identity_verification (
device_number string comment '手机号明文',
user_infos ARRAY<STRUCT<        
  cust_name_utf8_md5: STRING COMMENT '姓名md5',
  cert_no_md5: STRING COMMENT '证件md5',
  cust_name_utf8_sha256: STRING COMMENT '姓名sha256',
  cert_no_sha256: STRING COMMENT '证件sha256',
  innet_date: STRING COMMENT '入网日期',
  start_date: STRING COMMENT '使用开始时间',
  end_date: STRING COMMENT '使用结束时间',
  user_status: STRING COMMENT '当前状态',
  innet_months: INT COMMENT '在网时长'>>
) partitioned by (date_id string)

insert
  overwrite table ubd_serv_fin.serv_d_identity_verification partition (date_id ='20250531')
select
  device_number,
      collect_list(named_struct(
        'cust_name_utf8_md5', cust_name_utf8_md5,
        'cert_no_md5', cert_no_md5,
        'cust_name_utf8_sha256', cust_name_utf8_sha256,
        'cert_no_sha256', cert_no_sha256,
        'innet_date', innet_date,
        'start_date', innet_date,
        'end_date', close_date,
        'user_status', user_status,
        'innet_months', innet_months)) as user_infos
from
  ubd_b_dwa.dwa_d_cus_user_info
where
  date_id = '20250531'
  and innet_date is not null
  and device_number rlike '^[1][3-9][0-9]{9}$'
group by device_number;


-- 每日增量数据
-- 每日新入网/过户/离网用户
INSERT overwrite TABLE ubd_serv_fin.serv_d_identity_operation partition (date_id = '${date_id}')
SELECT device_number,
      collect_list(named_struct(
        'cust_name_utf8_md5', cust_name_utf8_md5,
        'cert_no_md5', cert_no_md5,
        'cust_name_utf8_sha256', cust_name_utf8_sha256,
        'cert_no_sha256', cert_no_sha256,
        'innet_date', innet_date,
        'start_date', innet_date,
        'end_date', close_date,
        'user_status', user_status,
        'innet_months', innet_months)) as user_infos
from
  ubd_b_dwa.dwa_d_cus_user_info
WHERE date_id = '${date_id}'
  AND (((innet_date = '${date_id}'
         OR changeuser_date = '${date_id}')
        AND is_innet = 1
        AND user_status = 11)
       OR (is_this_break = 1
           AND close_date >= '20170101'))
  AND device_number rlike '^[1][3-9][0-9]{9}$'
  AND length(cust_name_utf8_md5) > 0
  AND length(cert_no_md5) > 0
  AND length(cust_name_utf8_sha256) > 0
  AND length(cert_no_sha256) > 0
GROUP BY device_number;



-- 历史存量数据 
-- 历史过户用户及最新账期数据
DROP table ubd_serv_fin.existed_changeuser_user;
create table if not exists ubd_serv_fin.existed_changeuser_user as
select
  device_number,
  substr(month_id,1,6) as month_id
from
  (
    select
      device_number,
      date_format(
        add_months(
          from_unixtime(unix_timestamp(changeuser_date, 'yyyyMMdd')),
          -1
        ),
        'yyyyMMdd'
      ) as month_id
    from
      ubd_b_dwa.dwa_m_cus_user_info
    where
      month_id = '202505'
      and changeuser_date >= '20230701'
      and device_number rlike '^[1][3-9][0-9]{9}$'
      and length(cust_name_utf8_md5) > 0
      and length(cert_no_md5) > 0
      and length(cust_name_utf8_sha256) > 0
      and length(cert_no_sha256) > 0
  ) a
group by
  device_number,
  substr(month_id,1,6);

drop table ubd_serv_fin.serv_m_changeuser_info;
create table if not exists ubd_serv_fin.serv_m_changeuser_info (
device_number string comment '手机号明文',      
cust_name_utf8_md5 STRING COMMENT '姓名md5',
cert_no_md5 STRING COMMENT '证件md5',
cust_name_utf8_sha256 STRING COMMENT '姓名sha256',
cert_no_sha256 STRING COMMENT '证件sha256',
is_innet STRING COMMENT '是否在网',
innet_date STRING COMMENT '入网日期',
user_status STRING COMMENT '当前状态',
innet_months INT COMMENT '在网时长',
close_date STRING COMMENT '结束时间',
changeuser_date string COMMENT '过户时间'
) partitioned by (month_id string);

insert
  overwrite table ubd_serv_fin.serv_m_changeuser_info partition (month_id = '${month_id}')
select
  b.*
from
  (
    select
      *
    from
      ubd_serv_fin.existed_changeuser_user
    where
      month_id = '${month_id}'
  ) a
  join (
    select
      device_number,
      cust_name_utf8_md5,
      cert_no_md5,
      cust_name_utf8_sha256,
      cert_no_sha256,
      is_innet,
      innet_date,
      user_status,
      innet_months,
      close_date,
      changeuser_date
    from
      ubd_b_dwa.dwa_m_cus_user_info
    where
      month_id = '${month_id}'
      and length(cust_name_utf8_md5) > 0
      and length(cert_no_md5) > 0
      and length(cust_name_utf8_sha256) > 0
      and length(cert_no_sha256) > 0
) b on a.device_number = b.device_number;

insert
  overwrite table ubd_serv_fin.serv_m_changeuser_info partition (month_id = '202505')
select
  device_number,
  cust_name_utf8_md5,
  cert_no_md5,
  cust_name_utf8_sha256,
  cert_no_sha256,
  is_innet,
  innet_date,
  user_status,
  innet_months,
  close_date,
  changeuser_date
from
  ubd_b_dwa.dwa_m_cus_user_info
where
  month_id = '202505'
  and device_number rlike '^[1][3-9][0-9]{9}$'
  and length(cust_name_utf8_md5) > 0
  and length(cert_no_md5) > 0
  and length(cust_name_utf8_sha256) > 0
  and length(cert_no_sha256) > 0;



-- 最新在网用户
with lastest_innet_user as (
  select
    device_number
  from
    ubd_serv_fin.serv_m_changeuser_info
    where is_innet = 1
    and month_id = '202505'
  group by device_number
),
-- 存量数据在网用户
existed_innet_user AS
  (SELECT device_number,
          cust_name_utf8_md5,
          cert_no_md5,
          cust_name_utf8_sha256,
          cert_no_sha256,
          innet_date,
          CASE
              WHEN nvl(changeuser_date,'') = ''
                   AND nvl(next_changeuser_date,'') = '' THEN innet_date
              WHEN nvl(changeuser_date,'') != '' THEN changeuser_date
          END AS start_date,
          CASE
              WHEN nvl(changeuser_date,'') = ''
                   AND nvl(next_changeuser_date,'') != ''
                   AND nvl(close_date,'') = '' THEN next_changeuser_date
              ELSE close_date
          END AS end_date,
          user_status,
          innet_months
   FROM
     (SELECT b.*,
             LEAD(changeuser_date, 1) OVER (PARTITION BY b.device_number
                                        ORDER BY innet_date, changeuser_date) AS next_changeuser_date,
                                  ROW_NUMBER() OVER( PARTITION BY b.device_number
                                                    ORDER BY innet_date DESC ) AS rn
      FROM lastest_innet_user a
      JOIN ubd_serv_fin.serv_m_changeuser_info b
      WHERE a.device_number = b.device_number) c
   WHERE rn =1),
-- 最新离网用户
lastest_offnet_user as (
  select
    device_number
  from
    ubd_serv_fin.serv_m_changeuser_info
    where is_innet = 0
    and month_id = '202505'
  group by device_number
),
-- 存量数据离网用户
existed_offnet_user AS (
  SELECT
    device_number,
    cust_name_utf8_md5,
    cert_no_md5,
    cust_name_utf8_sha256,
    cert_no_sha256,
    innet_date,
    CASE
      WHEN nvl(changeuser_date,'') = ''
      AND nvl(next_changeuser_date,'') = '' THEN innet_date
      WHEN nvl(changeuser_date,'') != '' THEN changeuser_date
    END AS start_date,
    CASE
      WHEN nvl(close_date,'') != '' THEN close_date
      ELSE date_format(
        add_months(
          from_unixtime(unix_timestamp(innet_date, 'yyyyMMdd')),
          innet_months
        ),
        'yyyyMMdd'
      )
    END AS end_date,
    user_status,
    innet_months
  FROM
    (
      SELECT
        b.*,
        LEAD(changeuser_date, 1) OVER (
          PARTITION BY b.device_number
          ORDER BY
            innet_date,changeuser_date
        ) AS next_changeuser_date
      FROM
        lastest_offnet_user a
        JOIN ubd_serv_fin.serv_m_changeuser_info b ON a.device_number = b.device_number
      WHERE
        close_date >= '20170101'
        OR changeuser_date >= '20170101'
        OR date_format(
          add_months(
            from_unixtime(unix_timestamp(innet_date, 'yyyyMMdd')),
            innet_months
          ),
          'yyyyMMdd'
        ) >= '20170101'
    ) c
)
-- 历史存量
insert overwrite table ubd_serv_fin.serv_d_identity_verification partition (date_id='20250531')
select
  device_number,
  collect_list(
    named_struct(
      'cust_name_utf8_md5',cust_name_utf8_md5,
      'cert_no_md5',cert_no_md5,
      'cust_name_utf8_sha256',cust_name_utf8_sha256,
      'cert_no_sha256',cert_no_sha256,
      'innet_date',innet_date,
      'start_date',start_date,
      'end_date',end_date,
      'user_status',user_status,
      'innet_months',innet_months
    )
  ) as user_infos
from
  (
    select
      device_number,
      cust_name_utf8_md5,
      cert_no_md5,
      cust_name_utf8_sha256,
      cert_no_sha256,
      innet_date,
      start_date,
      end_date,
      user_status,
      innet_months
    from
      existed_innet_user
    union all
    select
      device_number,
      cust_name_utf8_md5,
      cert_no_md5,
      cust_name_utf8_sha256,
      cert_no_sha256,
      innet_date,
      start_date,
      end_date,
      user_status,
      innet_months
    from
      existed_offnet_user
  ) a
group by
  device_number;


-- 每日更新
INSERT overwrite TABLE ubd_serv_fin.serv_d_identity_verification partition (date_id = '20250609')
SELECT device_number,
       collect_set(infos) as user_infos
FROM
  (SELECT device_number,
          infos
   FROM ubd_serv_fin.serv_d_identity_operation
   LATERAL VIEW explode(user_infos) T as infos
   UNION ALL SELECT device_number,
                    infos
   FROM ubd_serv_fin.serv_d_identity_verification
   LATERAL VIEW explode(user_infos) T as infos
   WHERE date_id = '20250531') a
GROUP BY device_number;
