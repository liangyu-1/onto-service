package com.onto.service.semantic.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.onto.service.entity.OntologyObjectType;
import com.onto.service.mapper.OntologyObjectTypeMapper;
import com.onto.service.semantic.OntologyObjectTypeService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 对象类型服务实现
 */
@Service
public class OntologyObjectTypeServiceImpl extends ServiceImpl<OntologyObjectTypeMapper, OntologyObjectType> implements OntologyObjectTypeService {

    @Override
    public OntologyObjectType createObjectType(OntologyObjectType objectType) {
        baseMapper.insert(objectType);
        return objectType;
    }

    @Override
    public List<OntologyObjectType> getObjectTypes(String domainName, String version) {
        return baseMapper.selectByDomainVersion(domainName, version);
    }

    @Override
    public OntologyObjectType getObjectType(String domainName, String version, String labelName) {
        QueryWrapper<OntologyObjectType> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("label_name", labelName);
        return baseMapper.selectOne(wrapper);
    }

    @Override
    public List<OntologyObjectType> getChildTypes(String domainName, String version, String parentLabel) {
        return baseMapper.selectByParentLabel(domainName, version, parentLabel);
    }
}
