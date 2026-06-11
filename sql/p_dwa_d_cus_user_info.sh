#!/bin/bash
###############################################################################
# *脚本类型     --%@TYPE:               hive
# *名称        --%@NAME:              p_dwa_d_cus_user_info.sh
# *功能描述     --%@COMMENT:            移网用户资料日表
# *执行周期     --%@PERIOD:             d
# *参数        --%@PARAM:              帐期
# *创建者       --%@CREATED_BY:         郝树运
# *创建时间     --%@CREATE_TIME:        2021/03/11
# *修改者       --%@UPDATED_BY:        孙孟曜
# *更新时间     --%@UPDATE_TIME:        2022/07/19
# *层次         --%@LEVEL:             ubd_b_dwa
# *数据域       --%@DOMAIN:            B域
# *来源表       --%@FROM:              ubd_b_dwa.dwa_d_cus_user_info_prov
# *目标表       --%@TO:                ubd_b_dwa.dwa_d_cus_user_info
# *备注         --%@REMARK:            
###############################################################################
# 调用方法: sh p_dwa_d_cus_user_info.sh 20220401
###############################################################################

export HADOOP_HEAPSIZE=8192

#函数引用，使用相对路径
. ../pub_function.sh

#声明变量,变量赋值
v_date=$1

v_month=`echo $1 | cut -c 1-6`
v_day=`echo $1 | cut -c 7-8`
v_part=${v_month}
v_rowline=0
v_prov=099

#私有参数初始化
v_pkg=UBD_B_DWA
v_tablename=DWA_D_CUS_USER_INFO
v_procname=P_${v_tablename}
v_yesterday=`addDays $v_date -1`

#获取脚本文件名
v_shell_name=`basename $0` >>/dev/null
v_shell_name=`echo $v_shell_name|awk -F"." '{print $1}'` >>/dev/null

#生成本地日志文件
v_log_file=$(logFile ${v_shell_name} ${v_date} ${v_prov} /data/log/by/$(date +"%Y%m%d"))

#获取mysql数据库登录信息(check_mysql公共函数进行连接判断)
hostname=${LOG_MYSQL_HOST:-10.191.20.254}
port=${LOG_MYSQL_PORT:-8066}
username=${LOG_MYSQL_USER:-lf_pro_b}
password=${LOG_MYSQL_PASSWORD:?LOG_MYSQL_PASSWORD is required}
dbname=${LOG_MYSQL_DB:-zba_hd}
v_config_logmysql=$(checkMysql "$hostname" "$port" "$username" "$password" "$dbname")

##插入MySql日志
$(insertLog $hostname $port $username $password $dbname $v_date $v_pkg $v_procname $v_prov $v_tablename)

#定义sql
v_sql="alter table dwa_d_cus_user_info drop partition(date_id = '"${v_date}"');
INSERT overwrite TABLE dwa_d_cus_user_info PARTITION (date_id,prov_id)
SELECT device_number
    ,user_id
    ,cust_id
    ,user_id_sys
    ,cust_id_sys
    ,user_id_prov_sys
    ,cust_id_prov_sys
    ,service_type
    ,user_type
    ,brand_id
    ,is_innet
    ,is_card
    ,is_stat
    ,is_acct
    ,is_this_break
    ,pay_mode
    ,product_id
    ,product_class
    ,open_mode
    ,oper_date
    ,create_date
    ,innet_date
    ,close_date
    ,update_time
    ,innet_months
    ,user_status
    ,user_diff_code
    ,net_type_cbss
    ,activity_id
    ,activity_type
    ,active_type
    ,main_discnt_code
    ,is_change
    ,score_value
    ,credit_class
    ,basic_credit_value
    ,credit_value
    ,in_depart_id
    ,remove_flag
    ,remove_area_id
    ,remove_depart_id
    ,remove_reason_code
    ,pre_destroy_time
    ,first_call_time
    ,assure_cust_id
    ,assure_type_code
    ,assure_date
    ,is_add
    ,add_type
    ,is_this_dev
    ,is_lost
    ,lost_type
    ,open_depart_id
    ,developer_id
    ,develop_date
    ,develop_area_id
    ,changeuser_date
    ,innet_method
    ,channel_id
    ,channel_type
    ,stop_type
    ,last_stop_date
    ,area_id
    ,cert_area_id
    ,cert_type
    ,cust_sex
    ,cert_no_head_six
    ,cust_age
    ,cust_constellation
    ,cust_birthday_md5
    ,cust_name_md5
    ,cert_no_md5
    ,cust_name_mosaic
    ,cert_no_length
    ,cert_no_tail_four
    ,cert_no_tail_six_md5
    ,cert_addr_md5
    ,cust_addr_md5
    ,rn
    ,cust_name_utf8_md5
    ,cert_addr_utf8_md5
    ,cust_addr_utf8_md5
    ,cust_birthday_utf8_sha256
    ,cust_name_utf8_sha256
    ,cert_no_sha256
    ,cert_addr_utf8_sha256
    ,cust_addr_utf8_sha256
    ,cert_no_six_sha256
    ,stop_month
    ,cert_usernums
    ,cert_innet_usernums
    ,cert_usernums-cert_innet_usernums  as cert_break_usernums
    ,date_id
    ,prov_id
from
(
SELECT device_number
    ,user_id
    ,cust_id
    ,user_id_sys
    ,cust_id_sys
    ,user_id_prov_sys
    ,cust_id_prov_sys
    ,service_type
    ,user_type
    ,brand_id
    ,is_innet
    ,is_card
    ,is_stat
    ,is_acct
    ,is_this_break
    ,pay_mode
    ,product_id
    ,product_class
    ,open_mode
    ,oper_date
    ,create_date
    ,innet_date
    ,close_date
    ,update_time
    ,innet_months
    ,user_status
    ,user_diff_code
    ,net_type_cbss
    ,activity_id
    ,activity_type
    ,active_type
    ,main_discnt_code
    ,is_change
    ,score_value
    ,credit_class
    ,basic_credit_value
    ,credit_value
    ,in_depart_id
    ,remove_flag
    ,remove_area_id
    ,remove_depart_id
    ,remove_reason_code
    ,pre_destroy_time
    ,first_call_time
    ,assure_cust_id
    ,assure_type_code
    ,assure_date
    ,is_add
    ,add_type
    ,is_this_dev
    ,is_lost
    ,lost_type
    ,open_depart_id
    ,developer_id
    ,develop_date
    ,develop_area_id
    ,changeuser_date
    ,innet_method
    ,channel_id
    ,channel_type
    ,stop_type
    ,last_stop_date
    ,area_id
    ,cert_area_id
    ,cert_type
    ,cust_sex
    ,cert_no_head_six
    ,cust_age
    ,cust_constellation
    ,cust_birthday_md5
    ,cust_name_md5
    ,cert_no_md5
    ,cust_name_mosaic
    ,cert_no_length
    ,cert_no_tail_four
    ,cert_no_tail_six_md5
    ,cert_addr_md5
    ,cust_addr_md5
    ,row_number() OVER (PARTITION BY device_number ORDER BY rn, date_id DESC,is_innet DESC,innet_date DESC,service_type DESC) AS rn
    -- rownumber这里优先rn排序，是因为date_id都一样了，无法区分哪一条是新数据，这种情况下可能会一些不合理的历史数据影响导致B用户排的更靠前
    ,cust_name_utf8_md5
    ,cert_addr_utf8_md5
    ,cust_addr_utf8_md5
    ,cust_birthday_utf8_sha256
    ,cust_name_utf8_sha256
    ,cert_no_sha256
    ,cert_addr_utf8_sha256
    ,cust_addr_utf8_sha256
    ,cert_no_six_sha256
    ,stop_month
    ,size(collect_set(device_number) over(partition by cert_no_md5)) cert_usernums
    ,size(collect_set(case when is_innet='1' then device_number else null end) over(partition by cert_no_md5)) cert_innet_usernums
    ,date_id
    ,prov_id
from
(SELECT device_number
    ,user_id
    ,cust_id
    ,user_id_sys
    ,cust_id_sys
    ,user_id_prov_sys
    ,cust_id_prov_sys
    ,service_type
    ,user_type
    ,brand_id
    ,is_innet
    ,is_card
    ,is_stat
    ,is_acct
    ,is_this_break
    ,pay_mode
    ,product_id
    ,product_class
    ,open_mode
    ,oper_date
    ,create_date
    ,innet_date
    ,close_date
    ,update_time
    ,innet_months
    ,user_status
    ,user_diff_code
    ,net_type_cbss
    ,activity_id
    ,activity_type
    ,active_type
    ,main_discnt_code
    ,is_change
    ,score_value
    ,credit_class
    ,basic_credit_value
    ,credit_value
    ,in_depart_id
    ,remove_flag
    ,remove_area_id
    ,remove_depart_id
    ,remove_reason_code
    ,pre_destroy_time
    ,first_call_time
    ,assure_cust_id
    ,assure_type_code
    ,assure_date
    ,is_add
    ,add_type
    ,is_this_dev
    ,is_lost
    ,lost_type
    ,open_depart_id
    ,developer_id
    ,develop_date
    ,develop_area_id
    ,changeuser_date
    ,innet_method
    ,channel_id
    ,channel_type
    ,stop_type
    ,last_stop_date
    ,area_id
    ,cert_area_id
    ,cert_type
    ,cust_sex
    ,cert_no_head_six
    ,cust_age
    ,cust_constellation
    ,cust_birthday_md5
    ,cust_name_md5
    ,cert_no_md5
    ,cust_name_mosaic
    ,cert_no_length
    ,cert_no_tail_four
    ,cert_no_tail_six_md5
    ,cert_addr_md5
    ,cust_addr_md5
    ,cust_name_utf8_md5
    ,cert_addr_utf8_md5
    ,cust_addr_utf8_md5
    ,cust_birthday_utf8_sha256
    ,cust_name_utf8_sha256
    ,cert_no_sha256
    ,cert_addr_utf8_sha256
    ,cust_addr_utf8_sha256
    ,cert_no_six_sha256
    ,stop_month
    ,date_id
    ,prov_id
    ,rn --分省的rn中保证了最新账期更新进来的数据序号为1的特征，后续还需要据此排序
    ,rank() OVER (PARTITION BY device_number ORDER BY prov_id) AS ranknumber
    --关于ranknunber字段，理论上一个手机号不可能对应多个归属地，如果真的存在这里会只保留某一个省的数据，
    --而一个省内的数据在分省加工中是一次加工完成的，所以外层rownumber其实只用rn排序就可以的
    from ubd_b_dwa.dwa_d_cus_user_info_prov where date_id = '"${v_date}"'
)t1
where ranknumber=1
)t2
"

#执行sql命令
hive -e "
use ubd_b_dwa;
set mapreduce.job.queuename=ubd_by;
set mapreduce.job.name=${v_procname}_${v_date}_${v_prov};
set mapreduce.job.priority=VERY_HIGH;
set mapreduce.map.java.opts=-Xmx4096m;
set mapreduce.reduce.java.opts=-Xmx12288m;
set mapreduce.map.memory.mb=4096;
set mapreduce.reduce.memory.mb=12288;
set mapred.max.split.size=268435456;
set mapred.min.split.size.per.node=268435456;
set mapred.min.split.size.per.rack=268435456;
set mapred.output.compression.codec=org.apache.hadoop.io.compress.GzipCodec;
set mapred.output.compression.type=BLOCK;
set mapred.output.compress=true;
set hive.input.format=org.apache.hadoop.hive.ql.io.CombineHiveInputFormat;
set hive.groupby.skewindata=true;
set hive.auto.convert.join=false;
set hive.map.aggr=true;
set hive.exec.reducers.max=600;
set hive.exec.reducers.bytes.per.reducer=1073741824;
set mapreduce.reduce.cpu.vcores=3;
set hive.merge.mapfiles=true;
set hive.merge.mapredfiles=true;
set hive.merge.size.per.task=134217728;
set hive.merge.smallfiles.avgsize=134217728;
set hive.exec.compress.output=true;
set hive.stats.autogather=true;
set hive.exec.dynamic.partition.mode=nonstrict;
set hive.exec.max.dynamic.partitions.pernode=1000;
set hive.exec.dynamic.partition=true;
set mapreduce.job.running.map.limit=500;
set mapreduce.job.running.reduce.limit=300;
$v_sql;" 2>&1 |tee $v_log_file >>/dev/null

#获取动态分区名列表
v_prov_list=`hadoop fs -ls hdfs://xl/user/ubd_master/ubd_b_dwa.db/dwa_d_cus_user_info/date_id=${v_date}/ | awk -F 'prov_id=' '{print $2}'`

# 在319老集群建立分区连接并同步分区
#source /opt/beh/conf/beh_env
#
##对每个子动态分区分别处理
#if  [[ ${#v_prov_list} -gt 0 ]]; then
#  for v_prov_d in ${v_prov_list}
#  do
#    v_sql_sync="ALTER TABLE ubd_b_dwa.dwa_d_cus_user_info ADD IF NOT EXISTS PARTITION (date_id='${v_date}',prov_id='${v_prov_d}')
#                LOCATION 'hdfs://xl/user/ubd_master/ubd_b_dwa.db/dwa_d_cus_user_info/date_id=${v_date}/prov_id=${v_prov_d}';"
#    hive -e "use ubd_b_dwa;$v_sql_sync;" >>$v_log_file
#  done
#fi

#获取过程执行情况
v_result=$(isExeSuccess $v_log_file) >>/dev/null
if  [ $v_result -eq 1 ]; then
v_retcode=SUCCESS
v_retinfo=结束
else
v_retcode=FAIL
v_retinfo=$(getFailedInfo $v_log_file)
v_retinfo=${v_retinfo// /|}
echo $v_retcode
fi

##切换新319环境
source /opt/ubd/conf/beh_env

v_sql_count="select count(*) from ubd_b_dwa.dwa_d_cus_user_info
             where date_id='"${v_date}"';"
hive -S -e "
set mapred.job.name=${v_procname}_sum_${v_date}_${v_prov};
set mapreduce.job.priority=VERY_HIGH;
set mapreduce.job.queuename=ubd_by;
use ubd_b_dwa;
$v_sql_count;" 2>&1 | tee $v_log_file >>/dev/null

v_result_count=$(isExeSuccess $v_log_file)

if [ ${v_result_count} -eq 1 ]; then

v_rowline=$(getLastline $v_log_file)
v_rowline=`echo ${v_rowline}  | grep "^[0-9][0-9]*$"`

if [ "${v_rowline}" = "" ]; then
v_rowline=0
fi

fi

echo $v_rowline


#更新MySql日志
$(updateLog $hostname $port $username $password $dbname $v_date $v_pkg $v_procname $v_prov $v_retinfo $v_retcode $v_rowline)
