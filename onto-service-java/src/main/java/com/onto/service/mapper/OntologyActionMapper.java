package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyAction;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * Action Mapper
 */
@Mapper
public interface OntologyActionMapper extends BaseMapper<OntologyAction> {

    @Select("SELECT * FROM ontology_action WHERE domain_name = #{domainName} AND version = #{version} AND target_type = #{targetType}")
    List<OntologyAction> selectByTargetType(@Param("domainName") String domainName, @Param("version") String version, @Param("targetType") String targetType);
}
