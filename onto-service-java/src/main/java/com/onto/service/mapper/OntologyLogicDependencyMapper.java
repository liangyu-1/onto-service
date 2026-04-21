package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyLogicDependency;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * Logic 依赖 Mapper
 */
@Mapper
public interface OntologyLogicDependencyMapper extends BaseMapper<OntologyLogicDependency> {

    @Select("SELECT * FROM ontology_logic_dependency WHERE domain_name = #{domainName} AND version = #{version} AND logic_name = #{logicName}")
    List<OntologyLogicDependency> selectByLogicName(@Param("domainName") String domainName, @Param("version") String version, @Param("logicName") String logicName);

    @Select("SELECT * FROM ontology_logic_dependency WHERE domain_name = #{domainName} AND version = #{version} AND dependency_name = #{dependencyName}")
    List<OntologyLogicDependency> selectByDependencyName(@Param("domainName") String domainName, @Param("version") String version, @Param("dependencyName") String dependencyName);
}
