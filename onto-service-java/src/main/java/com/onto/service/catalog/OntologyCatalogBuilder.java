package com.onto.service.catalog;

import com.onto.service.entity.*;

import java.util.List;

/**
 * Ontology Catalog 构建器接口
 * 基于 TBOX 元数据动态构建 GoogleSQL Catalog 和 PropertyGraph
 */
public interface OntologyCatalogBuilder {

    /**
     * 为指定域版本构建 Catalog
     * 返回 Catalog 元数据摘要
     */
    CatalogMetadata buildCatalog(String domainName, String version);

    /**
     * 构建 PropertyGraph
     */
    PropertyGraphMetadata buildPropertyGraph(String domainName, String version, CatalogMetadata catalog);

    /**
     * 注册节点表 (Node Table)
     */
    void registerNodeTable(PropertyGraphMetadata graph, OntologyObjectType objectType,
                           OntologyObjectAboxMapping mapping, List<OntologyProperty> properties);

    /**
     * 注册边表 (Edge Table)
     */
    void registerEdgeTable(PropertyGraphMetadata graph, OntologyRelationship relationship,
                           CatalogMetadata catalog);

    /**
     * 刷新 Catalog (当 TBOX 变更时)
     */
    void refreshCatalog(String domainName, String version);

    /**
     * Catalog 元数据
     */
    class CatalogMetadata {
        private String domainName;
        private String version;
        private int objectTypeCount;
        private int relationshipCount;
        private int mappingCount;
        private boolean built;
        private String nativeCatalogHandle;  // JNI handle

        public String getDomainName() { return domainName; }
        public void setDomainName(String domainName) { this.domainName = domainName; }
        public String getVersion() { return version; }
        public void setVersion(String version) { this.version = version; }
        public int getObjectTypeCount() { return objectTypeCount; }
        public void setObjectTypeCount(int objectTypeCount) { this.objectTypeCount = objectTypeCount; }
        public int getRelationshipCount() { return relationshipCount; }
        public void setRelationshipCount(int relationshipCount) { this.relationshipCount = relationshipCount; }
        public int getMappingCount() { return mappingCount; }
        public void setMappingCount(int mappingCount) { this.mappingCount = mappingCount; }
        public boolean isBuilt() { return built; }
        public void setBuilt(boolean built) { this.built = built; }
        public String getNativeCatalogHandle() { return nativeCatalogHandle; }
        public void setNativeCatalogHandle(String nativeCatalogHandle) { this.nativeCatalogHandle = nativeCatalogHandle; }
    }

    /**
     * PropertyGraph 元数据
     */
    class PropertyGraphMetadata {
        private String domainName;
        private String version;
        private int nodeTableCount;
        private int edgeTableCount;
        private int labelCount;
        private String nativeGraphHandle;  // JNI handle

        public String getDomainName() { return domainName; }
        public void setDomainName(String domainName) { this.domainName = domainName; }
        public String getVersion() { return version; }
        public void setVersion(String version) { this.version = version; }
        public int getNodeTableCount() { return nodeTableCount; }
        public void setNodeTableCount(int nodeTableCount) { this.nodeTableCount = nodeTableCount; }
        public int getEdgeTableCount() { return edgeTableCount; }
        public void setEdgeTableCount(int edgeTableCount) { this.edgeTableCount = edgeTableCount; }
        public int getLabelCount() { return labelCount; }
        public void setLabelCount(int labelCount) { this.labelCount = labelCount; }
        public String getNativeGraphHandle() { return nativeGraphHandle; }
        public void setNativeGraphHandle(String nativeGraphHandle) { this.nativeGraphHandle = nativeGraphHandle; }
    }
}
