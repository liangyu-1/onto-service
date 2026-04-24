package com.onto.service.tbox.neo4j;

import com.onto.service.entity.*;
import org.neo4j.driver.Record;
import org.neo4j.driver.Values;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

/**
 * Neo4j 作为 TBOX 唯一主存的最小实现。
 *
 * 说明：这里优先保证闭环可用（CRUD + list），复杂依赖/影响分析后续再增强。
 */
@Service
public class TboxNeo4jServiceImpl implements TboxNeo4jService {

    @Autowired
    private Neo4jClient neo4j;

    @Override
    public OntologyDomain createDomain(String domainName, String ddlSql, String createdBy) {
        String version = "1.0.0";
        return upsertDomainVersion(domainName, version, ddlSql, "draft", createdBy);
    }

    @Override
    public OntologyDomain publishVersion(String domainName, String ddlSql, String createdBy) {
        List<OntologyDomain> versions = listDomainVersions(domainName);
        String next = generateNextVersion(versions);
        return upsertDomainVersion(domainName, next, ddlSql, "published", createdBy);
    }

    @Override
    public Optional<OntologyDomain> getDomainVersion(String domainName, String version) {
        String cypher = "MATCH (d:DomainVersion {domainName:$domainName, version:$version}) RETURN d LIMIT 1";
        List<OntologyDomain> list = neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version), r -> toDomain(r.get("d").asMap()));
        return list.stream().findFirst();
    }

    @Override
    public List<OntologyDomain> listDomainVersions(String domainName) {
        String cypher = "MATCH (d:DomainVersion {domainName:$domainName}) RETURN d ORDER BY d.createdAt DESC";
        return neo4j.queryList(cypher, Map.of("domainName", domainName), r -> toDomain(r.get("d").asMap()));
    }

    @Override
    public Optional<OntologyDomain> latestPublished(String domainName) {
        String cypher = "MATCH (d:DomainVersion {domainName:$domainName, status:'published'}) RETURN d ORDER BY d.createdAt DESC LIMIT 1";
        List<OntologyDomain> list = neo4j.queryList(cypher, Map.of("domainName", domainName), r -> toDomain(r.get("d").asMap()));
        return list.stream().findFirst();
    }

    @Override
    public OntologyObjectType createObjectType(OntologyObjectType objectType) {
        objectType.setAiContext(objectType.getAiContext());
        String cypher = """
                MERGE (t:ObjectType {domainName:$domainName, version:$version, labelName:$labelName})
                SET t.parentLabel=$parentLabel,
                    t.displayName=$displayName,
                    t.description=$description,
                    t.aiContext=$aiContext
                WITH t
                FOREACH (_ IN CASE WHEN $parentLabel IS NULL OR $parentLabel = '' THEN [] ELSE [1] END |
                  MERGE (p:ObjectType {domainName:$domainName, version:$version, labelName:$parentLabel})
                  MERGE (t)-[:SUBCLASS_OF]->(p)
                )
                RETURN t
                """;
        Map<String, Object> p = new HashMap<>();
        p.put("domainName", objectType.getDomainName());
        p.put("version", objectType.getVersion());
        p.put("labelName", objectType.getLabelName());
        p.put("parentLabel", objectType.getParentLabel());
        p.put("displayName", objectType.getDisplayName());
        p.put("description", objectType.getDescription());
        p.put("aiContext", objectType.getAiContext());
        return neo4j.writeTx(tx -> {
            Record r = tx.run(cypher, Values.value(p)).single();
            return toObjectType(r.get("t").asMap());
        });
    }

    @Override
    public List<OntologyObjectType> listObjectTypes(String domainName, String version) {
        String cypher = "MATCH (t:ObjectType {domainName:$domainName, version:$version}) RETURN t ORDER BY t.labelName";
        return neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version), r -> toObjectType(r.get("t").asMap()));
    }

    @Override
    public OntologyProperty createProperty(OntologyProperty property) {
        String cypher = """
                MERGE (p:Property {domainName:$domainName, version:$version, ownerLabel:$ownerLabel, propertyName:$propertyName})
                SET p.valueType=$valueType,
                    p.columnName=$columnName,
                    p.expressionSql=$expressionSql,
                    p.isMeasure=$isMeasure,
                    p.semanticRole=$semanticRole,
                    p.hidden=$hidden,
                    p.description=$description,
                    p.aiContext=$aiContext
                WITH p
                MERGE (t:ObjectType {domainName:$domainName, version:$version, labelName:$ownerLabel})
                MERGE (t)-[:HAS_PROPERTY]->(p)
                RETURN p
                """;
        Map<String, Object> params = new HashMap<>();
        params.put("domainName", property.getDomainName());
        params.put("version", property.getVersion());
        params.put("ownerLabel", property.getOwnerLabel());
        params.put("propertyName", property.getPropertyName());
        params.put("valueType", property.getValueType());
        params.put("columnName", property.getColumnName());
        params.put("expressionSql", property.getExpressionSql());
        params.put("isMeasure", property.getIsMeasure());
        params.put("semanticRole", property.getSemanticRole());
        params.put("hidden", property.getHidden());
        params.put("description", property.getDescription());
        params.put("aiContext", property.getAiContext());
        return neo4j.writeTx(tx -> {
            Record r = tx.run(cypher, Values.value(params)).single();
            return toProperty(r.get("p").asMap());
        });
    }

    @Override
    public List<OntologyProperty> listProperties(String domainName, String version, String ownerLabel) {
        String cypher = "MATCH (p:Property {domainName:$domainName, version:$version, ownerLabel:$ownerLabel}) RETURN p ORDER BY p.propertyName";
        return neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version, "ownerLabel", ownerLabel), r -> toProperty(r.get("p").asMap()));
    }

    @Override
    public OntologyRelationship createRelationship(OntologyRelationship relationship) {
        String cypher = """
                MERGE (r:RelationType {domainName:$domainName, version:$version, labelName:$labelName})
                SET r.edgeTable=$edgeTable,
                    r.sourceLabel=$sourceLabel,
                    r.targetLabel=$targetLabel,
                    r.sourceKey=$sourceKey,
                    r.targetKey=$targetKey,
                    r.outgoingName=$outgoingName,
                    r.incomingName=$incomingName,
                    r.outgoingIsMulti=$outgoingIsMulti,
                    r.incomingIsMulti=$incomingIsMulti,
                    r.cardinality=$cardinality,
                    r.aiContext=$aiContext
                WITH r
                MERGE (s:ObjectType {domainName:$domainName, version:$version, labelName:$sourceLabel})
                MERGE (t:ObjectType {domainName:$domainName, version:$version, labelName:$targetLabel})
                MERGE (r)-[:SOURCE_TYPE]->(s)
                MERGE (r)-[:TARGET_TYPE]->(t)
                RETURN r
                """;
        Map<String, Object> params = new HashMap<>();
        params.put("domainName", relationship.getDomainName());
        params.put("version", relationship.getVersion());
        params.put("labelName", relationship.getLabelName());
        params.put("edgeTable", relationship.getEdgeTable());
        params.put("sourceLabel", relationship.getSourceLabel());
        params.put("targetLabel", relationship.getTargetLabel());
        params.put("sourceKey", relationship.getSourceKey());
        params.put("targetKey", relationship.getTargetKey());
        params.put("outgoingName", relationship.getOutgoingName());
        params.put("incomingName", relationship.getIncomingName());
        params.put("outgoingIsMulti", relationship.getOutgoingIsMulti());
        params.put("incomingIsMulti", relationship.getIncomingIsMulti());
        params.put("cardinality", relationship.getCardinality());
        params.put("aiContext", relationship.getAiContext());
        return neo4j.writeTx(tx -> toRelationship(tx.run(cypher, Values.value(params)).single().get("r").asMap()));
    }

    @Override
    public List<OntologyRelationship> listRelationships(String domainName, String version) {
        String cypher = "MATCH (r:RelationType {domainName:$domainName, version:$version}) RETURN r ORDER BY r.labelName";
        return neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version), rec -> toRelationship(rec.get("r").asMap()));
    }

    @Override
    public OntologyObjectAboxMapping createAboxMapping(OntologyObjectAboxMapping mapping) {
        String cypher = """
                MERGE (m:AboxMapping {domainName:$domainName, version:$version, className:$className})
                SET m.parentClass=$parentClass,
                    m.mappingStrategy=$mappingStrategy,
                    m.objectSourceName=$objectSourceName,
                    m.sourceKind=$sourceKind,
                    m.primaryKey=$primaryKey,
                    m.discriminatorColumn=$discriminatorColumn,
                    m.typeFilterSql=$typeFilterSql,
                    m.propertyProjectionJson=$propertyProjectionJson,
                    m.viewSql=$viewSql,
                    m.materializationStrategy=$materializationStrategy,
                    m.aiContext=$aiContext
                WITH m
                MERGE (t:ObjectType {domainName:$domainName, version:$version, labelName:$className})
                MERGE (t)-[:HAS_ABOX_MAPPING]->(m)
                RETURN m
                """;
        Map<String, Object> params = new HashMap<>();
        params.put("domainName", mapping.getDomainName());
        params.put("version", mapping.getVersion());
        params.put("className", mapping.getClassName());
        params.put("parentClass", mapping.getParentClass());
        params.put("mappingStrategy", mapping.getMappingStrategy());
        params.put("objectSourceName", mapping.getObjectSourceName());
        params.put("sourceKind", mapping.getSourceKind());
        params.put("primaryKey", mapping.getPrimaryKey());
        params.put("discriminatorColumn", mapping.getDiscriminatorColumn());
        params.put("typeFilterSql", mapping.getTypeFilterSql());
        params.put("propertyProjectionJson", mapping.getPropertyProjectionJson());
        params.put("viewSql", mapping.getViewSql());
        params.put("materializationStrategy", mapping.getMaterializationStrategy());
        params.put("aiContext", mapping.getAiContext());
        return neo4j.writeTx(tx -> toAboxMapping(tx.run(cypher, Values.value(params)).single().get("m").asMap()));
    }

    @Override
    public List<OntologyObjectAboxMapping> listAboxMappings(String domainName, String version) {
        String cypher = "MATCH (m:AboxMapping {domainName:$domainName, version:$version}) RETURN m ORDER BY m.className";
        return neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version), r -> toAboxMapping(r.get("m").asMap()));
    }

    @Override
    public OntologyLogic createLogic(OntologyLogic logic) {
        String cypher = """
                MERGE (l:Logic {domainName:$domainName, version:$version, logicName:$logicName})
                SET l.targetType=$targetType,
                    l.targetProperty=$targetProperty,
                    l.logicKind=$logicKind,
                    l.implementationType=$implementationType,
                    l.expressionSql=$expressionSql,
                    l.deterministic=$deterministic,
                    l.executionModeHint=$executionModeHint,
                    l.outputType=$outputType,
                    l.aiContext=$aiContext
                WITH l
                FOREACH (_ IN CASE WHEN $targetType IS NULL OR $targetType='' THEN [] ELSE [1] END |
                  MERGE (t:ObjectType {domainName:$domainName, version:$version, labelName:$targetType})
                  MERGE (l)-[:TARGETS]->(t)
                )
                RETURN l
                """;
        Map<String, Object> params = new HashMap<>();
        params.put("domainName", logic.getDomainName());
        params.put("version", logic.getVersion());
        params.put("logicName", logic.getLogicName());
        params.put("targetType", logic.getTargetType());
        params.put("targetProperty", logic.getTargetProperty());
        params.put("logicKind", logic.getLogicKind());
        params.put("implementationType", logic.getImplementationType());
        params.put("expressionSql", logic.getExpressionSql());
        params.put("deterministic", logic.getDeterministic());
        params.put("executionModeHint", logic.getExecutionModeHint());
        params.put("outputType", logic.getOutputType());
        params.put("aiContext", logic.getAiContext());
        return neo4j.writeTx(tx -> toLogic(tx.run(cypher, Values.value(params)).single().get("l").asMap()));
    }

    @Override
    public List<OntologyLogic> listLogic(String domainName, String version) {
        String cypher = "MATCH (l:Logic {domainName:$domainName, version:$version}) RETURN l ORDER BY l.logicName";
        return neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version), r -> toLogic(r.get("l").asMap()));
    }

    @Override
    public OntologyAction createAction(OntologyAction action) {
        String cypher = """
                MERGE (a:Action {domainName:$domainName, version:$version, actionName:$actionName})
                SET a.toolName=$toolName,
                    a.targetType=$targetType,
                    a.inputSchemaJson=$inputSchemaJson,
                    a.outputSchemaJson=$outputSchemaJson,
                    a.preconditionSql=$preconditionSql,
                    a.preconditionLogic=$preconditionLogic,
                    a.externalPlatform=$externalPlatform,
                    a.externalActionRef=$externalActionRef,
                    a.invocationMode=$invocationMode,
                    a.dryRunRequired=$dryRunRequired,
                    a.aiContext=$aiContext
                WITH a
                FOREACH (_ IN CASE WHEN $targetType IS NULL OR $targetType='' THEN [] ELSE [1] END |
                  MERGE (t:ObjectType {domainName:$domainName, version:$version, labelName:$targetType})
                  MERGE (a)-[:TARGETS]->(t)
                )
                RETURN a
                """;
        Map<String, Object> params = new HashMap<>();
        params.put("domainName", action.getDomainName());
        params.put("version", action.getVersion());
        params.put("actionName", action.getActionName());
        params.put("toolName", action.getToolName());
        params.put("targetType", action.getTargetType());
        params.put("inputSchemaJson", action.getInputSchemaJson());
        params.put("outputSchemaJson", action.getOutputSchemaJson());
        params.put("preconditionSql", action.getPreconditionSql());
        params.put("preconditionLogic", action.getPreconditionLogic());
        params.put("externalPlatform", action.getExternalPlatform());
        params.put("externalActionRef", action.getExternalActionRef());
        params.put("invocationMode", action.getInvocationMode());
        params.put("dryRunRequired", action.getDryRunRequired());
        params.put("aiContext", action.getAiContext());
        return neo4j.writeTx(tx -> toAction(tx.run(cypher, Values.value(params)).single().get("a").asMap()));
    }

    @Override
    public List<OntologyAction> listActions(String domainName, String version) {
        String cypher = "MATCH (a:Action {domainName:$domainName, version:$version}) RETURN a ORDER BY a.actionName";
        return neo4j.queryList(cypher, Map.of("domainName", domainName, "version", version), r -> toAction(r.get("a").asMap()));
    }

    private OntologyDomain upsertDomainVersion(String domainName, String version, String ddlSql, String status, String createdBy) {
        String cypher = """
                MERGE (d:DomainVersion {domainName:$domainName, version:$version})
                SET d.ddlSql=$ddlSql,
                    d.status=$status,
                    d.createdBy=$createdBy,
                    d.createdAt=$createdAt
                RETURN d
                """;
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("domainName", domainName);
        params.put("version", version);
        params.put("ddlSql", ddlSql);
        params.put("status", status);
        params.put("createdBy", createdBy);
        params.put("createdAt", now.toString());
        return neo4j.writeTx(tx -> toDomain(tx.run(cypher, Values.value(params)).single().get("d").asMap()));
    }

    private static String generateNextVersion(List<OntologyDomain> versions) {
        if (versions == null || versions.isEmpty()) return "1.0.0";
        String v = versions.get(0).getVersion();
        try {
            String[] parts = v.split("\\.");
            int major = Integer.parseInt(parts[0]);
            int minor = parts.length > 1 ? Integer.parseInt(parts[1]) : 0;
            int patch = parts.length > 2 ? Integer.parseInt(parts[2]) : 0;
            patch += 1;
            return major + "." + minor + "." + patch;
        } catch (Exception e) {
            return "1.0.1";
        }
    }

    private static OntologyDomain toDomain(Map<String, Object> m) {
        OntologyDomain d = new OntologyDomain();
        d.setDomainName((String) m.get("domainName"));
        d.setVersion((String) m.get("version"));
        d.setDdlSql((String) m.get("ddlSql"));
        d.setStatus((String) m.get("status"));
        d.setCreatedBy((String) m.get("createdBy"));
        // DomainController/UI 不强依赖 createdAt 精确类型，这里留空或字符串解析后续再补
        return d;
    }

    private static OntologyObjectType toObjectType(Map<String, Object> m) {
        OntologyObjectType t = new OntologyObjectType();
        t.setDomainName((String) m.get("domainName"));
        t.setVersion((String) m.get("version"));
        t.setLabelName((String) m.get("labelName"));
        t.setParentLabel((String) m.get("parentLabel"));
        t.setDisplayName((String) m.get("displayName"));
        t.setDescription((String) m.get("description"));
        t.setAiContext((String) m.get("aiContext"));
        return t;
    }

    private static OntologyProperty toProperty(Map<String, Object> m) {
        OntologyProperty p = new OntologyProperty();
        p.setDomainName((String) m.get("domainName"));
        p.setVersion((String) m.get("version"));
        p.setOwnerLabel((String) m.get("ownerLabel"));
        p.setPropertyName((String) m.get("propertyName"));
        p.setValueType((String) m.get("valueType"));
        p.setColumnName((String) m.get("columnName"));
        p.setExpressionSql((String) m.get("expressionSql"));
        p.setIsMeasure((Boolean) m.get("isMeasure"));
        p.setSemanticRole((String) m.get("semanticRole"));
        p.setHidden((Boolean) m.get("hidden"));
        p.setDescription((String) m.get("description"));
        p.setAiContext((String) m.get("aiContext"));
        return p;
    }

    private static OntologyRelationship toRelationship(Map<String, Object> m) {
        OntologyRelationship r = new OntologyRelationship();
        r.setDomainName((String) m.get("domainName"));
        r.setVersion((String) m.get("version"));
        r.setLabelName((String) m.get("labelName"));
        r.setEdgeTable((String) m.get("edgeTable"));
        r.setSourceLabel((String) m.get("sourceLabel"));
        r.setTargetLabel((String) m.get("targetLabel"));
        r.setSourceKey((String) m.get("sourceKey"));
        r.setTargetKey((String) m.get("targetKey"));
        r.setOutgoingName((String) m.get("outgoingName"));
        r.setIncomingName((String) m.get("incomingName"));
        r.setOutgoingIsMulti((Boolean) m.get("outgoingIsMulti"));
        r.setIncomingIsMulti((Boolean) m.get("incomingIsMulti"));
        r.setCardinality((String) m.get("cardinality"));
        r.setAiContext((String) m.get("aiContext"));
        return r;
    }

    private static OntologyObjectAboxMapping toAboxMapping(Map<String, Object> m) {
        OntologyObjectAboxMapping x = new OntologyObjectAboxMapping();
        x.setDomainName((String) m.get("domainName"));
        x.setVersion((String) m.get("version"));
        x.setClassName((String) m.get("className"));
        x.setParentClass((String) m.get("parentClass"));
        x.setMappingStrategy((String) m.get("mappingStrategy"));
        x.setObjectSourceName((String) m.get("objectSourceName"));
        x.setSourceKind((String) m.get("sourceKind"));
        x.setPrimaryKey((String) m.get("primaryKey"));
        x.setDiscriminatorColumn((String) m.get("discriminatorColumn"));
        x.setTypeFilterSql((String) m.get("typeFilterSql"));
        x.setPropertyProjectionJson((String) m.get("propertyProjectionJson"));
        x.setViewSql((String) m.get("viewSql"));
        x.setMaterializationStrategy((String) m.get("materializationStrategy"));
        x.setAiContext((String) m.get("aiContext"));
        return x;
    }

    private static OntologyLogic toLogic(Map<String, Object> m) {
        OntologyLogic l = new OntologyLogic();
        l.setDomainName((String) m.get("domainName"));
        l.setVersion((String) m.get("version"));
        l.setLogicName((String) m.get("logicName"));
        l.setTargetType((String) m.get("targetType"));
        l.setTargetProperty((String) m.get("targetProperty"));
        l.setLogicKind((String) m.get("logicKind"));
        l.setImplementationType((String) m.get("implementationType"));
        l.setExpressionSql((String) m.get("expressionSql"));
        l.setDeterministic((Boolean) m.get("deterministic"));
        l.setExecutionModeHint((String) m.get("executionModeHint"));
        l.setOutputType((String) m.get("outputType"));
        l.setAiContext((String) m.get("aiContext"));
        return l;
    }

    private static OntologyAction toAction(Map<String, Object> m) {
        OntologyAction a = new OntologyAction();
        a.setDomainName((String) m.get("domainName"));
        a.setVersion((String) m.get("version"));
        a.setActionName((String) m.get("actionName"));
        a.setToolName((String) m.get("toolName"));
        a.setTargetType((String) m.get("targetType"));
        a.setInputSchemaJson((String) m.get("inputSchemaJson"));
        a.setOutputSchemaJson((String) m.get("outputSchemaJson"));
        a.setPreconditionSql((String) m.get("preconditionSql"));
        a.setPreconditionLogic((String) m.get("preconditionLogic"));
        a.setExternalPlatform((String) m.get("externalPlatform"));
        a.setExternalActionRef((String) m.get("externalActionRef"));
        a.setInvocationMode((String) m.get("invocationMode"));
        Object dry = m.get("dryRunRequired");
        if (dry instanceof Boolean b) a.setDryRunRequired(b);
        a.setAiContext((String) m.get("aiContext"));
        return a;
    }
}

