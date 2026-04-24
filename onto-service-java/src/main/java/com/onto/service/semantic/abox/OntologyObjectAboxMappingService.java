package com.onto.service.semantic.abox;

import com.onto.service.entity.OntologyObjectAboxMapping;

import java.util.List;

/**
 * TBOX/ABOX 映射服务接口
 */
public interface OntologyObjectAboxMappingService {

    OntologyObjectAboxMapping createMapping(OntologyObjectAboxMapping mapping);

    List<OntologyObjectAboxMapping> listMappings(String domainName, String version);

    OntologyObjectAboxMapping getMapping(String domainName, String version, String className);

    OntologyObjectAboxMapping updateMapping(OntologyObjectAboxMapping mapping);

    void deleteMapping(String domainName, String version, String className);
}
