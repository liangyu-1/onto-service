package com.onto.service.semantic.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.onto.service.entity.OntologyRelationship;
import com.onto.service.mapper.OntologyRelationshipMapper;
import com.onto.service.semantic.OntologyRelationshipService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 关系服务实现
 */
@Service
public class OntologyRelationshipServiceImpl extends ServiceImpl<OntologyRelationshipMapper, OntologyRelationship> implements OntologyRelationshipService {

    @Override
    public OntologyRelationship createRelationship(OntologyRelationship relationship) {
        baseMapper.insert(relationship);
        return relationship;
    }

    @Override
    public List<OntologyRelationship> getRelationships(String domainName, String version) {
        return baseMapper.selectByDomainVersion(domainName, version);
    }

    @Override
    public OntologyRelationship getRelationship(String domainName, String version, String labelName) {
        QueryWrapper<OntologyRelationship> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("label_name", labelName);
        return baseMapper.selectOne(wrapper);
    }

    @Override
    public List<OntologyRelationship> getOutgoingRelationships(String domainName, String version, String sourceLabel) {
        return baseMapper.selectOutgoingBySource(domainName, version, sourceLabel);
    }

    @Override
    public List<OntologyRelationship> getIncomingRelationships(String domainName, String version, String targetLabel) {
        return baseMapper.selectIncomingByTarget(domainName, version, targetLabel);
    }
}
