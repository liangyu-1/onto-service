package com.onto.service.catalog;

import com.google.googlesql.*;
import com.onto.service.entity.*;
import com.onto.service.semantic.*;

import java.util.List;

/**
 * Ontology Catalog 构建器
 * 基于 TBOX 元数据动态构建 GoogleSQL SimpleCatalog 和 PropertyGraph
 */
public interface OntologyCatalogBuilder {

    /**
     * 为指定域版本构建 Catalog
     */
    SimpleCatalog buildCatalog(String domainName, String version);

    /**
     * 构建 PropertyGraph
     */
    SimplePropertyGraph buildPropertyGraph(String domainName, String version, SimpleCatalog catalog);

    /**
     * 注册节点表 (Node Table)
     */
    void registerNodeTable(SimplePropertyGraph graph, OntologyObjectType objectType,
                           OntologyObjectAboxMapping mapping, List<OntologyProperty> properties);

    /**
     * 注册边表 (Edge Table)
     */
    void registerEdgeTable(SimplePropertyGraph graph, OntologyRelationship relationship,
                           SimpleCatalog catalog);

    /**
     * 刷新 Catalog (当 TBOX 变更时)
     */
    void refreshCatalog(String domainName, String version);
}
