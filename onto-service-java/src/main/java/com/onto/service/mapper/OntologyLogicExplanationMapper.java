package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyLogicExplanation;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * Logic 解释模板 Mapper
 */
@Mapper
public interface OntologyLogicExplanationMapper extends BaseMapper<OntologyLogicExplanation> {

    @Select("SELECT * FROM ontology_logic_explanation WHERE domain_name = #{domainName} AND version = #{version} AND logic_name = #{logicName} AND language = #{language}")
    OntologyLogicExplanation selectByLogicAndLanguage(@Param("domainName") String domainName, @Param("version") String version, @Param("logicName") String logicName, @Param("language") String language);
}
