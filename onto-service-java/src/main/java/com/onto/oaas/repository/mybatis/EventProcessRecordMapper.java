package com.onto.oaas.repository.mybatis;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.oaas.model.EventProcessRecord;
import com.onto.oaas.model.enums.EventProcessStatus;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface EventProcessRecordMapper extends BaseMapper<EventProcessRecord> {

    @Select("SELECT * FROM event_process_record WHERE event_id = #{eventId}")
    EventProcessRecord findByEventId(@Param("eventId") String eventId);

    @Update("UPDATE event_process_record SET graph_status = #{status}, updated_time = NOW() WHERE event_id = #{eventId}")
    int updateStatus(@Param("eventId") String eventId, @Param("status") EventProcessStatus status);

    @Update("TRUNCATE TABLE event_process_record")
    void truncateAll();
}
