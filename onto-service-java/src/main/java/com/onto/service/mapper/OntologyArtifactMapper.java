package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyArtifact;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 本体工件 Mapper
 */
@Mapper
public interface OntologyArtifactMapper extends BaseMapper<OntologyArtifact> {

    @Select("SELECT * FROM ontology_artifact WHERE domain_name = #{domainName} AND version = #{version} " +
            "ORDER BY created_at DESC")
    List<OntologyArtifact> selectByDomainVersion(@Param("domainName") String domainName,
                                                 @Param("version") String version);

    @Select("SELECT * FROM ontology_artifact WHERE domain_name = #{domainName} AND version = #{version} " +
            "AND artifact_kind = #{artifactKind} AND format = #{format} AND content_hash = #{contentHash} " +
            "LIMIT 1")
    OntologyArtifact selectOneByKey(@Param("domainName") String domainName,
                                    @Param("version") String version,
                                    @Param("artifactKind") String artifactKind,
                                    @Param("format") String format,
                                    @Param("contentHash") String contentHash);

    @Select("SELECT * FROM ontology_artifact WHERE domain_name = #{domainName} AND version = #{version} " +
            "AND artifact_kind = #{artifactKind} AND format = #{format} " +
            "ORDER BY created_at DESC LIMIT 1")
    OntologyArtifact selectLatestByKindFormat(@Param("domainName") String domainName,
                                              @Param("version") String version,
                                              @Param("artifactKind") String artifactKind,
                                              @Param("format") String format);
}

