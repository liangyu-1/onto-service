package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyLogic;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * Logic Mapper
 */
@Mapper
public interface OntologyLogicMapper extends BaseMapper<OntologyLogic> {

    @Select("SELECT * FROM ontology_logic WHERE domain_name = #{domainName} AND version = #{version} AND logic_kind = #{logicKind}")
    List<OntologyLogic> selectByLogicKind(@Param("domainName") String domainName, @Param("version") String version, @Param("logicKind") String logicKind);

    @Select("SELECT * FROM ontology_logic WHERE domain_name = #{domainName} AND version = #{version} AND target_type = #{targetType}")
    List<OntologyLogic> selectByTargetType(@Param("domainName") String domainName, @Param("version") String version, @Param("targetType") String targetType);

    @Select("SELECT * FROM ontology_logic WHERE domain_name = #{domainName} AND version = #{version}")
    List<OntologyLogic> selectByDomainVersion(@Param("domainName") String domainName, @Param("version") String version);
}
