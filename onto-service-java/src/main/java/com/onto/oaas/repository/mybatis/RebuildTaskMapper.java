package com.onto.oaas.repository.mybatis;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.oaas.model.RebuildTask;
import com.onto.oaas.model.enums.RebuildStatus;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface RebuildTaskMapper extends BaseMapper<RebuildTask> {

    @Select("SELECT * FROM rebuild_task WHERE status = #{status}")
    List<RebuildTask> findByStatus(@Param("status") RebuildStatus status);
}
