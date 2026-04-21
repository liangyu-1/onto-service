package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyObjectType;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 对象类型 Mapper
 */
@Mapper
public interface OntologyObjectTypeMapper extends BaseMapper<OntologyObjectType> {

    @Select("SELECT * FROM ontology_object_type WHERE domain_name = #{domainName} AND version = #{version}")
    List<OntologyObjectType> selectByDomainVersion(@Param("domainName") String domainName, @Param("version") String version);

    @Select("SELECT * FROM ontology_object_type WHERE domain_name = #{domainName} AND version = #{version} AND parent_label = #{parentLabel}")
    List<OntologyObjectType> selectByParentLabel(@Param("domainName") String domainName, @Param("version") String version, @Param("parentLabel") String parentLabel);
}
