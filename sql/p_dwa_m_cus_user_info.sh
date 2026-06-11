#!/bin/bash
#
###############################################################################
# *脚本类型     --%@TYPE:           hive
# *名称         --%@NAME:           p_dwa_m_cus_user_info.sh
# *功能描述     --%@COMMENT:        移网用户资料月表
# *执行周期     --%@PERIOD:         M
# *参数         --%@PARAM:          账期 省分
# *创建人       --%@CREATOR:        haosy11
# *创建时间     --%@CREATED_TIME:   2020-11-10
# *层次         --%@LEVEL:          ubd_b_dwa
# *数据域       --%@DOMAIN:         B域
# *备注         --%@REMARK:
# *修改记录     --%@MODIFY:
# *修改记录     --%@MODIFY:
# *来源表       --%@FROM:           ubd_b_dwa.dwa_d_cus_user_info
# *来源表       --%@FROM:           ubd_b_dwa.dwa_m_cus_cust_info
# *来源表       --%@FROM:           ubd_b_ods.ods_m_cus_cb_user_info
# *目标表       --%@TO:             ubd_b_dwa.dwa_m_cus_user_info
###############################################################################
# 调用方法: sh p_dwa_m_cus_user_info.sh 20201110 010
###############################################################################

# 函数引用，使用相对路径
. ../pub_function/p_pub_func_all.sh

###############################################################################
# 声明变量,变量赋值
v_date=$1
v_prov=$2
v_month=`echo $v_date | cut -c 1-6`
v_day=`echo $v_date | cut -c 7-8`
lastday=$(getLastDay $v_month)
v_rowline=0

###############################################################################
# 固定模板，不需修改
# shell名称获取
# 例如：shell名称为：p_dwa_m_cus_user_info.sh
# 截取后为：p_dwa_m_cus_user_info
###############################################################################
v_shellname=`basename $0` >>/dev/null
v_shellname=`echo $v_shellname|awk -F"." '{print $1}'` >>/dev/null

###############################################################################
# 日志文件定义，确定日志文件存放的位置及日志文件名称
# 命名方式为：shell名称_账期_省分_系统时间戳.log
# 例如：p_dwa_d_cus_al_cust_info_20190528_099_20131127172425.log
###############################################################################
v_logfile=$(logFile $v_shellname $v_date $v_prov)
# 判断日志文件是否存在，如果存在就清空
if [ -f $v_logfile ]
 then
   cat /dev/null > $v_logfile
fi
###############################################################################

#私有参数初始化（根据脚本自行进行调整及配置）
v_pkg=UBD_B_DWA      #过程关键字通常截断过程前段
v_procname=P_DWA_M_CUS_USER_INFO   #过程名（最终结果表前加P_与文件名一致）
v_tablename=DWA_M_CUS_USER_INFO      #目标表名（最终结果表）

#获取mysql数据库连【利用p_pub_func_log.sh中的check_mysql方法/函数进行mysql连接判断】
v_config_logmysql=$(check_mysql)
hostname=`echo $v_config_logmysql|awk -F: '{print $1}'`
port=`echo $v_config_logmysql|awk -F: '{print $2}'`
username=`echo $v_config_logmysql|awk -F: '{print $3}'`
password=`echo $v_config_logmysql|awk -F: '{print $4}'`
dbname=`echo $v_config_logmysql|awk -F: '{print $5}'`

#插入日志
$(insertLog_user $hostname $port $username $password $dbname $v_date $v_pkg $v_procname $v_prov $v_tablename)


#定义sql
v_sql="alter table dwa_m_cus_user_info drop partition(month_id = '"${v_month}"',prov_id = '"${v_prov}"');
INSERT overwrite TABLE dwa_m_cus_user_info PARTITION (month_id = '"${v_month}"',prov_id = '"${v_prov}"')
SELECT t1.device_number
    ,t1.user_id
    ,t1.cust_id
    ,t1.user_id_sys
    ,t1.cust_id_sys
    ,t1.user_id_prov_sys
    ,t1.cust_id_prov_sys
    ,t1.service_type
    ,t1.user_type
    ,t1.brand_id
    ,t1.is_innet
    ,t1.is_card
    ,t1.is_stat
    ,t1.is_acct
    ,t1.is_this_break
    ,t1.pay_mode
    ,t1.product_id
    ,t1.product_class
    ,t1.open_mode
    ,t1.oper_date
    ,t1.create_date
    ,t1.innet_date
    ,t1.close_date
    ,t1.update_time
    ,t1.innet_months
    ,t1.user_status
    ,t1.user_diff_code
    ,t1.net_type_cbss
    ,t1.activity_id
    ,t1.activity_type
    ,t1.active_type
    ,t1.main_discnt_code
    ,t1.is_change
    ,t1.score_value
    ,t1.credit_class
    ,t1.basic_credit_value
    ,t1.credit_value
    ,t1.in_depart_id
    ,t1.remove_flag
    ,t1.remove_area_id
    ,t1.remove_depart_id
    ,t1.remove_reason_code
    ,t1.pre_destroy_time
    ,t1.first_call_time
    ,t1.assure_cust_id
    ,t1.assure_type_code
    ,t1.assure_date
    ,t1.is_add
    ,t1.add_type
    ,t1.is_this_dev
    ,t1.is_lost
    ,t1.lost_type
    ,t1.open_depart_id
    ,t1.developer_id
    ,t1.develop_date
    ,t1.develop_area_id
    ,t1.changeuser_date
    ,t1.innet_method
    ,t1.channel_id
    ,t1.channel_type
    ,t1.stop_type
    ,t1.last_stop_date
    ,t1.area_id
    ,t1.cert_area_id
    ,t1.cert_type
    ,t1.cust_sex
    ,t1.cert_no_head_six
    ,t1.cust_age
    ,t1.cust_constellation
    ,t1.cust_birthday_md5
    ,t1.cust_name_md5
    ,t1.cert_no_md5
    ,t1.cust_name_mosaic
    ,t1.cert_no_length
    ,t1.cert_no_tail_four
    ,t1.cert_no_tail_six_md5
    ,t1.cert_addr_md5
    ,t1.cust_addr_md5
    ,t2.cust_name_is_valid
    ,t2.cert_type_is_valid
    ,t2.cert_no_is_valid
    ,t2.cert_addr_is_valid
    ,t2.is_18_cert_no_valid
    ,t2.is_15_cert_no_valid
    ,t2.jk_cust_name_is_valid
    ,t2.contact_addr_is_valid_wide
    ,t2.is_18_cert_no_valid_wide
    ,t2.cert_addr_is_valid_wide
    ,t2.name_is_valid_wide
    ,t3.product_pkg_mode
    ,t3.zb_dev_man_id
    ,t3.is_group
    ,t3.innet_flag
    ,t3.user_group_flag
    ,t3.minor_enterprises_flag
    ,t3.cust_size
    ,t3.channel_type_zb
    ,t1.rn
    ,t1.cust_name_utf8_md5
    ,t1.cert_addr_utf8_md5
    ,t1.cust_addr_utf8_md5
    ,t1.cust_birthday_utf8_sha256
    ,t1.cust_name_utf8_sha256
    ,t1.cert_no_sha256
    ,t1.cert_addr_utf8_sha256
    ,t1.cust_addr_utf8_sha256
    ,t1.cert_no_six_sha256
    ,t1.stop_month
    ,t1.cert_usernums
    ,t1.cert_innet_usernums
    ,t1.cert_break_usernums
FROM (
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
        ,cert_break_usernums
    FROM ubd_b_dwa.dwa_d_cus_user_info
    WHERE date_id = '"${lastday}"'
        AND prov_id = '"${v_prov}"'
    ) t1
LEFT JOIN --关联客户资料表月表

(SELECT cust_id_prov_sys
    ,cust_name_is_valid
    ,cert_type_is_valid
    ,cert_no_is_valid
    ,cert_addr_is_valid
    ,is_18_cert_no_valid
    ,is_15_cert_no_valid
    ,jk_cust_name_is_valid
    ,contact_addr_is_valid_wide
    ,is_18_cert_no_valid_wide
    ,cert_addr_is_valid_wide
    ,name_is_valid_wide
FROM ubd_b_dwa.dwa_m_cus_cust_info
WHERE month_id = '"${v_month}"'
    AND prov_id = '"${v_prov}"' ) t2
    ON t1.cust_id_prov_sys = t2.cust_id_prov_sys
LEFT JOIN --关联用户资料月表获取月表特有字段
    (
    SELECT NULL as product_pkg_mode
        ,NULL as zb_dev_man_id
        ,is_group
        ,innet_flag
        ,user_group_flag
        ,minor_enterprises_flag
        ,cust_size
        ,NULL as channel_type_zb
        ,CONCAT_ws('_','CB',prov_id,user_id_old) AS user_id_prov_sys
    FROM ubd_b_ods.ods_m_cus_cb_user_info
    WHERE month_id = '"${v_month}"'
        AND prov_id = '"${v_prov}"'
    ) t3
    ON t1.user_id_prov_sys = t3.user_id_prov_sys;
"

#新集群同步sql
v_sql_sync="ALTER TABLE ubd_b_dwa.dwa_m_cus_user_info ADD IF NOT EXISTS PARTITION (month_id='${v_month}', prov_id='${v_prov}')
LOCATION 'hdfs://xl/user/ubd_master/ubd_b_dwa.db/dwa_m_cus_user_info/month_id=${v_month}/prov_id=${v_prov}';"

#hive执行sql命令，并将执行结果写入日志文件中
hive -e "
use ubd_b_dwa;
set mapred.job.name=${v_procname}_${v_date}_${v_prov};
set mapreduce.job.queuename=ubd_by;
set hive.groupby.skewindata=true;
set hive.auto.convert.join=false;
set hive.map.aggr=true;
set mapreduce.map.memory.mb=2048;
set mapreduce.reduce.memory.mb=4096;
set mapred.max.split.size=268435456;
set mapred.min.split.size.per.node=268435456;
set mapred.min.split.size.per.rack=268435456;
set hive.exec.reducers.max=850;
set hive.merge.mapfiles=true;
set hive.merge.mapredfiles=true;
set hive.merge.size.per.task=134217728;
set hive.merge.smallfiles.avgsize=134217728;
set hive.exec.reducers.bytes.per.reducer=268435456;
set hive.exec.compress.output=true;
set mapred.output.compress=true;
set mapred.output.compression.codec=org.apache.hadoop.io.compress.GzipCodec;
set mapred.output.compression.type=BLOCK;
set hive.stats.autogather=true;
$v_sql
;" 2>&1 |tee $v_logfile >>/dev/null

# 在319老集群建立分区连接并同步分区
#source /opt/beh/conf/beh_env
#hive -e "use ubd_b_dwa;$v_sql_sync;" >>$v_logfile

#获取过程执行情况【通过p_pub_func_analyze.sh中的isExeSuccess方法/函数进行判断】
v_result=$(isExeSuccess $v_logfile) >>/dev/null
if  [ $v_result -eq 1 ]; then
v_retcode=SUCCESS
v_retinfo=结束
v_rowline=0

##切换新319环境
source /opt/ubd/conf/beh_env

vf_sql="select count(*) from ubd_b_dwa.dwa_m_cus_user_info
        where month_id='"${v_date}"' and prov_id='"${v_prov}"';"

hive -S -e "
set mapred.job.name=${v_procname}_sum_${v_date}_${v_prov};
set mapreduce.job.queuename=ubd_by;
$vf_sql;" 2>&1 | tee $v_logfile >>/dev/null

vf_flag=$(isExeSuccess $v_logfile)

if [ ${vf_flag} -eq 1 ]; then

v_rowline=$(getLastline $v_logfile)
v_rowline=`echo ${v_rowline}  | grep "^[0-9][0-9]*$"`

if [ "${v_rowline}" = "" ]; then
v_rowline=0
fi

fi

echo $v_rowline

else
v_retcode=FAIL
#获取执行错误原因【通过p_pub_func_analyze.sh中的getFailedInfo方法/函数进行判断】
v_retinfo=$(getFailedInfo $v_logfile)
v_retinfo=${v_retinfo//\'/\"}
v_retinfo=${v_retinfo// /|}
echo $v_retcode
fi

#更新日志【通过p_pub_func_log.sh中的updateLog方法/函数进行获取】
$(updateLog_user $hostname $port $username $password $dbname $v_date $v_pkg $v_procname $v_prov $v_retinfo $v_retcode $v_rowline)



