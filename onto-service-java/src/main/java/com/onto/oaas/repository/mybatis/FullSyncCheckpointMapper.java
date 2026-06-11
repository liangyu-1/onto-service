package com.onto.oaas.repository.mybatis;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.oaas.model.FullSyncCheckpoint;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface FullSyncCheckpointMapper extends BaseMapper<FullSyncCheckpoint> {

    @Select("SELECT * FROM full_sync_checkpoint ORDER BY started_time DESC LIMIT 1")
    FullSyncCheckpoint findLatest();
}
