package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.SemanticFact;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 推理事实 Mapper
 */
@Mapper
public interface SemanticFactMapper extends BaseMapper<SemanticFact> {

    @Select("SELECT * FROM semantic_fact WHERE domain_name = #{domainName} AND version = #{version} AND object_type = #{objectType} AND object_id = #{objectId}")
    List<SemanticFact> selectByObject(@Param("domainName") String domainName, @Param("version") String version, @Param("objectType") String objectType, @Param("objectId") String objectId);

    @Select("SELECT * FROM semantic_fact WHERE domain_name = #{domainName} AND version = #{version} AND computed_by_logic = #{logicName}")
    List<SemanticFact> selectByLogicName(@Param("domainName") String domainName, @Param("version") String version, @Param("logicName") String logicName);
}
