package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyProperty;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 属性 Mapper
 */
@Mapper
public interface OntologyPropertyMapper extends BaseMapper<OntologyProperty> {

    @Select("SELECT * FROM ontology_property WHERE domain_name = #{domainName} AND version = #{version} AND owner_label = #{ownerLabel}")
    List<OntologyProperty> selectByOwnerLabel(@Param("domainName") String domainName, @Param("version") String version, @Param("ownerLabel") String ownerLabel);

    @Select("SELECT * FROM ontology_property WHERE domain_name = #{domainName} AND version = #{version} AND owner_label = #{ownerLabel} AND hidden = false")
    List<OntologyProperty> selectVisibleByOwnerLabel(@Param("domainName") String domainName, @Param("version") String version, @Param("ownerLabel") String ownerLabel);
}
