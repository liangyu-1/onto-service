package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyDomain;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 本体域 Mapper
 */
@Mapper
public interface OntologyDomainMapper extends BaseMapper<OntologyDomain> {

    @Select("SELECT * FROM ontology_domain WHERE domain_name = #{domainName} ORDER BY created_at DESC")
    List<OntologyDomain> selectByDomainName(@Param("domainName") String domainName);

    @Select("SELECT * FROM ontology_domain WHERE domain_name = #{domainName} AND status = 'published' ORDER BY created_at DESC LIMIT 1")
    OntologyDomain selectLatestPublished(@Param("domainName") String domainName);
}
