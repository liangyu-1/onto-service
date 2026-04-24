package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyObjectAboxMapping;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * ABOX 映射 Mapper
 */
@Mapper
public interface OntologyObjectAboxMappingMapper extends BaseMapper<OntologyObjectAboxMapping> {

    @Select("SELECT * FROM ontology_object_abox_mapping WHERE domain_name = #{domainName} AND version = #{version} AND class_name = #{className}")
    OntologyObjectAboxMapping selectByClassName(@Param("domainName") String domainName, @Param("version") String version, @Param("className") String className);

    @Select("SELECT * FROM ontology_object_abox_mapping WHERE domain_name = #{domainName} AND version = #{version}")
    List<OntologyObjectAboxMapping> selectByDomainVersion(@Param("domainName") String domainName, @Param("version") String version);
}
