package com.onto.service.semantic.abox;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.onto.service.entity.OntologyObjectAboxMapping;
import com.onto.service.mapper.OntologyObjectAboxMappingMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * TBOX/ABOX 映射服务实现
 */
@Service
public class OntologyObjectAboxMappingServiceImpl implements OntologyObjectAboxMappingService {

    @Autowired
    private OntologyObjectAboxMappingMapper aboxMappingMapper;

    @Override
    public OntologyObjectAboxMapping createMapping(OntologyObjectAboxMapping mapping) {
        aboxMappingMapper.insert(mapping);
        return mapping;
    }

    @Override
    public List<OntologyObjectAboxMapping> listMappings(String domainName, String version) {
        return aboxMappingMapper.selectByDomainVersion(domainName, version);
    }

    @Override
    public OntologyObjectAboxMapping getMapping(String domainName, String version, String className) {
        return aboxMappingMapper.selectByClassName(domainName, version, className);
    }

    @Override
    public OntologyObjectAboxMapping updateMapping(OntologyObjectAboxMapping mapping) {
        UpdateWrapper<OntologyObjectAboxMapping> wrapper = new UpdateWrapper<>();
        wrapper.eq("domain_name", mapping.getDomainName())
               .eq("version", mapping.getVersion())
               .eq("class_name", mapping.getClassName());
        aboxMappingMapper.update(mapping, wrapper);
        return mapping;
    }

    @Override
    public void deleteMapping(String domainName, String version, String className) {
        QueryWrapper<OntologyObjectAboxMapping> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("class_name", className);
        aboxMappingMapper.delete(wrapper);
    }
}
