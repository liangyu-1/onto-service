package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.SemanticActionInstance;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * Action 实例 Mapper
 */
@Mapper
public interface SemanticActionInstanceMapper extends BaseMapper<SemanticActionInstance> {

    @Select("SELECT * FROM semantic_action_instance WHERE domain_name = #{domainName} ORDER BY created_at DESC LIMIT #{limit}")
    List<SemanticActionInstance> selectRecentByDomain(@Param("domainName") String domainName, @Param("limit") int limit);
}
