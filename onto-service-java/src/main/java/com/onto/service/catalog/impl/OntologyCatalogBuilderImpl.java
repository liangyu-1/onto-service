package com.onto.service.catalog.impl;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.onto.service.catalog.OntologyCatalogBuilder;
import com.onto.service.entity.*;
import com.onto.service.mapper.*;
import com.onto.service.semantic.OntologyObjectTypeService;
import com.onto.service.semantic.OntologyPropertyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * Ontology Catalog 构建器实现
 *
 * 基于 TBOX 元数据动态构建 Catalog 和 PropertyGraph。
 * 使用 Caffeine 缓存 Catalog 实例，避免重复构建。
 *
 * JNI 桥接说明：
 * - 加载 libonto_jni.so 后，通过 native 方法调用 C++ 实现
 * - C++ 侧负责实际的 GoogleSQL SimpleCatalog 和 PropertyGraph 构建
 * - Java 侧负责元数据加载和生命周期管理
 */
@Slf4j
@Component
public class OntologyCatalogBuilderImpl implements OntologyCatalogBuilder {

    @Autowired
    private OntologyObjectTypeService objectTypeService;

    @Autowired
    private OntologyPropertyService propertyService;

    @Autowired
    private OntologyRelationshipMapper relationshipMapper;

    @Autowired
    private OntologyObjectAboxMappingMapper aboxMappingMapper;

    private Cache<String, CatalogMetadata> catalogCache;
    private Cache<String, PropertyGraphMetadata> graphCache;

    // Native library loaded flag
    private boolean jniAvailable = false;

    @PostConstruct
    public void init() {
        catalogCache = Caffeine.newBuilder()
            .maximumSize(100)
            .expireAfterWrite(10, TimeUnit.MINUTES)
            .build();

        graphCache = Caffeine.newBuilder()
            .maximumSize(100)
            .expireAfterWrite(10, TimeUnit.MINUTES)
            .build();

        // Try to load native library
        try {
            System.loadLibrary("onto_jni");
            jniAvailable = true;
            log.info("JNI library 'onto_jni' loaded successfully");
        } catch (UnsatisfiedLinkError e) {
            log.warn("JNI library 'onto_jni' not available, catalog building will use fallback mode: {}", e.getMessage());
            jniAvailable = false;
        }
    }

    @Override
    public CatalogMetadata buildCatalog(String domainName, String version) {
        String cacheKey = domainName + ":" + version;
        CatalogMetadata cached = catalogCache.getIfPresent(cacheKey);
        if (cached != null && cached.isBuilt()) {
            log.debug("Catalog cache hit for {}", cacheKey);
            return cached;
        }

        log.info("Building catalog for domain={}, version={}", domainName, version);

        // 1. 加载 TBOX 元数据
        List<OntologyObjectType> objectTypes = objectTypeService.getObjectTypes(domainName, version);
        List<OntologyRelationship> relationships = relationshipMapper.selectByDomainVersion(domainName, version);
        List<OntologyObjectAboxMapping> mappings = aboxMappingMapper.selectByDomainVersion(domainName, version);

        CatalogMetadata metadata = new CatalogMetadata();
        metadata.setDomainName(domainName);
        metadata.setVersion(version);
        metadata.setObjectTypeCount(objectTypes.size());
        metadata.setRelationshipCount(relationships.size());
        metadata.setMappingCount(mappings.size());

        // 2. 通过 JNI 构建 native catalog (如果可用)
        if (jniAvailable) {
            try {
                String nativeHandle = nativeBuildCatalog(domainName, version,
                    serializeObjectTypes(objectTypes),
                    serializeRelationships(relationships),
                    serializeMappings(mappings));
                metadata.setNativeCatalogHandle(nativeHandle);
                metadata.setBuilt(true);
                log.info("Native catalog built successfully, handle={}", nativeHandle);
            } catch (Exception e) {
                log.error("Failed to build native catalog, using fallback mode", e);
                metadata.setBuilt(false);
            }
        } else {
            // Fallback: 纯 Java 模式，不构建 native catalog
            metadata.setBuilt(false);
            log.info("Catalog metadata prepared (fallback mode, no native catalog)");
        }

        catalogCache.put(cacheKey, metadata);
        return metadata;
    }

    @Override
    public PropertyGraphMetadata buildPropertyGraph(String domainName, String version, CatalogMetadata catalog) {
        String cacheKey = domainName + ":" + version;
        PropertyGraphMetadata cached = graphCache.getIfPresent(cacheKey);
        if (cached != null) {
            return cached;
        }

        log.info("Building property graph for domain={}, version={}", domainName, version);

        PropertyGraphMetadata metadata = new PropertyGraphMetadata();
        metadata.setDomainName(domainName);
        metadata.setVersion(version);

        List<OntologyObjectType> objectTypes = objectTypeService.getObjectTypes(domainName, version);
        List<OntologyRelationship> relationships = relationshipMapper.selectByDomainVersion(domainName, version);

        int nodeCount = 0;
        int edgeCount = 0;

        // Register node tables
        for (OntologyObjectType objType : objectTypes) {
            OntologyObjectAboxMapping mapping = aboxMappingMapper.selectByClassName(domainName, version, objType.getLabelName());
            List<OntologyProperty> properties = propertyService.getPropertiesByOwner(domainName, version, objType.getLabelName());

            if (mapping != null) {
                registerNodeTable(metadata, objType, mapping, properties);
                nodeCount++;
            }
        }

        // Register edge tables
        for (OntologyRelationship rel : relationships) {
            registerEdgeTable(metadata, rel, catalog);
            edgeCount++;
        }

        metadata.setNodeTableCount(nodeCount);
        metadata.setEdgeTableCount(edgeCount);

        // Native graph build via JNI
        if (jniAvailable && catalog.isBuilt() && catalog.getNativeCatalogHandle() != null) {
            try {
                String nativeHandle = nativeBuildPropertyGraph(catalog.getNativeCatalogHandle());
                metadata.setNativeGraphHandle(nativeHandle);
                log.info("Native property graph built successfully, handle={}", nativeHandle);
            } catch (Exception e) {
                log.error("Failed to build native property graph", e);
            }
        }

        graphCache.put(cacheKey, metadata);
        return metadata;
    }

    @Override
    public void registerNodeTable(PropertyGraphMetadata graph, OntologyObjectType objectType,
                                  OntologyObjectAboxMapping mapping, List<OntologyProperty> properties) {
        log.debug("Registering node table: {} -> {}", objectType.getLabelName(), mapping.getObjectSourceName());

        if (jniAvailable && graph.getNativeGraphHandle() != null) {
            try {
                nativeRegisterNodeTable(
                    graph.getNativeGraphHandle(),
                    objectType.getLabelName(),
                    mapping.getObjectSourceName(),
                    mapping.getPrimaryKey(),
                    serializeProperties(properties)
                );
            } catch (Exception e) {
                log.error("Failed to register native node table for {}", objectType.getLabelName(), e);
            }
        }
    }

    @Override
    public void registerEdgeTable(PropertyGraphMetadata graph, OntologyRelationship relationship, CatalogMetadata catalog) {
        log.debug("Registering edge table: {} ({} -> {})",
            relationship.getLabelName(), relationship.getSourceLabel(), relationship.getTargetLabel());

        if (jniAvailable && graph.getNativeGraphHandle() != null) {
            try {
                nativeRegisterEdgeTable(
                    graph.getNativeGraphHandle(),
                    relationship.getLabelName(),
                    relationship.getSourceLabel(),
                    relationship.getTargetLabel(),
                    relationship.getSourceKey(),
                    relationship.getTargetKey(),
                    relationship.getEdgeTable()
                );
            } catch (Exception e) {
                log.error("Failed to register native edge table for {}", relationship.getLabelName(), e);
            }
        }
    }

    @Override
    public void refreshCatalog(String domainName, String version) {
        String cacheKey = domainName + ":" + version;
        catalogCache.invalidate(cacheKey);
        graphCache.invalidate(cacheKey);

        // Invalidate native catalog if exists
        if (jniAvailable) {
            try {
                nativeRefreshCatalog(domainName, version);
            } catch (Exception e) {
                log.error("Failed to refresh native catalog", e);
            }
        }

        log.info("Catalog refreshed for {}", cacheKey);
    }

    // ==================== JNI Native Methods ====================

    /**
     * 构建 native catalog
     */
    private native String nativeBuildCatalog(String domainName, String version,
                                              String objectTypesJson, String relationshipsJson, String mappingsJson);

    /**
     * 构建 native property graph
     */
    private native String nativeBuildPropertyGraph(String catalogHandle);

    /**
     * 注册 native node table
     */
    private native void nativeRegisterNodeTable(String graphHandle, String labelName,
                                                 String sourceName, String primaryKey, String propertiesJson);

    /**
     * 注册 native edge table
     */
    private native void nativeRegisterEdgeTable(String graphHandle, String labelName,
                                                 String sourceLabel, String targetLabel,
                                                 String sourceKey, String targetKey, String edgeTable);

    /**
     * 刷新 native catalog
     */
    private native void nativeRefreshCatalog(String domainName, String version);

    // ==================== Serialization Helpers ====================

    private String serializeObjectTypes(List<OntologyObjectType> objectTypes) {
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(objectTypes);
        } catch (Exception e) {
            log.error("Failed to serialize object types", e);
            return "[]";
        }
    }

    private String serializeRelationships(List<OntologyRelationship> relationships) {
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(relationships);
        } catch (Exception e) {
            log.error("Failed to serialize relationships", e);
            return "[]";
        }
    }

    private String serializeMappings(List<OntologyObjectAboxMapping> mappings) {
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(mappings);
        } catch (Exception e) {
            log.error("Failed to serialize mappings", e);
            return "[]";
        }
    }

    private String serializeProperties(List<OntologyProperty> properties) {
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(properties);
        } catch (Exception e) {
            log.error("Failed to serialize properties", e);
            return "[]";
        }
    }
}
