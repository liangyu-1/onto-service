package com.onto.service.semantic.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.onto.service.entity.OntologyProperty;
import com.onto.service.mapper.OntologyPropertyMapper;
import com.onto.service.semantic.OntologyPropertyService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 属性服务实现
 */
@Service
public class OntologyPropertyServiceImpl extends ServiceImpl<OntologyPropertyMapper, OntologyProperty> implements OntologyPropertyService {

    @Override
    public OntologyProperty createProperty(OntologyProperty property) {
        baseMapper.insert(property);
        return property;
    }

    @Override
    public List<OntologyProperty> getPropertiesByOwner(String domainName, String version, String ownerLabel) {
        return baseMapper.selectByOwnerLabel(domainName, version, ownerLabel);
    }

    @Override
    public OntologyProperty getProperty(String domainName, String version, String ownerLabel, String propertyName) {
        QueryWrapper<OntologyProperty> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("owner_label", ownerLabel)
               .eq("property_name", propertyName);
        return baseMapper.selectOne(wrapper);
    }

    @Override
    public List<OntologyProperty> getVisibleProperties(String domainName, String version, String ownerLabel) {
        return baseMapper.selectVisibleByOwnerLabel(domainName, version, ownerLabel);
    }
}
