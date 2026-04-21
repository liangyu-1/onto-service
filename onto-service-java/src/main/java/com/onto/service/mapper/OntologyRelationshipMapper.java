package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyRelationship;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 关系 Mapper
 */
@Mapper
public interface OntologyRelationshipMapper extends BaseMapper<OntologyRelationship> {

    @Select("SELECT * FROM ontology_relationship WHERE domain_name = #{domainName} AND version = #{version}")
    List<OntologyRelationship> selectByDomainVersion(@Param("domainName") String domainName, @Param("version") String version);

    @Select("SELECT * FROM ontology_relationship WHERE domain_name = #{domainName} AND version = #{version} AND source_label = #{sourceLabel}")
    List<OntologyRelationship> selectOutgoingBySource(@Param("domainName") String domainName, @Param("version") String version, @Param("sourceLabel") String sourceLabel);

    @Select("SELECT * FROM ontology_relationship WHERE domain_name = #{domainName} AND version = #{version} AND target_label = #{targetLabel}")
    List<OntologyRelationship> selectIncomingByTarget(@Param("domainName") String domainName, @Param("version") String version, @Param("targetLabel") String targetLabel);
}
