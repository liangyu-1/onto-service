package com.onto.oaas.repository.neo4j;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.GraphEdge;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.Direction;
import com.onto.oaas.repository.TBoxGraphRepository;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Result;
import org.neo4j.driver.Session;
import org.neo4j.driver.Values;
import org.neo4j.driver.types.Node;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Repository;

@Slf4j
@Primary
@Repository
public class Neo4jTBoxGraphRepository implements TBoxGraphRepository {

    private final Driver driver;
    private final ObjectMapper objectMapper;

    // 在 saveSnapshot 期间保存 ID path -> object_path 的映射，用于解析 relationship.linkProperties
    private final ThreadLocal<Map<String, String>> idToObjectPathMap = ThreadLocal.withInitial(HashMap::new);

    @Autowired
    public Neo4jTBoxGraphRepository(Driver driver, ObjectMapper objectMapper) {
        this.driver = driver;
        this.objectMapper = objectMapper;
    }

    // ========== SAVE with buffer ==========

    @Override
    public void saveDomain(DomainDef domain, String domainKey) {
        saveDomain(domain, domainKey, activeBuffer());
    }

    public void saveDomain(DomainDef domain, String domainKey, String buffer) {
        String cypher = """
            MERGE (d:Domain {object_path: $objectPath, buffer: $buffer})
            SET d.name = $name,
                d.display_name = $displayName,
                d.description = $description,
                d.domain_key = $domainKey
            """;
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("objectPath", domainKey);
            params.put("buffer", buffer);
            params.put("name", domain.getName());
            params.put("displayName", domain.getDisplayName());
            params.put("description", domain.getDescription());
            params.put("domainKey", domainKey);
            session.run(cypher, params);
        }
    }

    @Override
    public void saveType(TypeDef type, String domainKey, String typeKey) {
        saveType(type, domainKey, typeKey, activeBuffer());
    }

    public void saveType(TypeDef type, String domainKey, String typeKey, String buffer) {
        String objectPath = domainKey + "." + typeKey;
        String cypher = """
            MATCH (d:Domain {object_path: $domainKey, buffer: $buffer})
            MERGE (t:Type {object_path: $objectPath, buffer: $buffer})
            SET t.name = $name,
                t.display_name = $displayName,
                t.description = $description,
                t.display_property = $displayProperty,
                t.domain_key = $domainKey,
                t.type_key = $typeKey
            MERGE (d)-[:HAS_TYPE]->(t)
            """;
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("domainKey", domainKey);
            params.put("buffer", buffer);
            params.put("objectPath", objectPath);
            params.put("name", type.getName());
            params.put("displayName", type.getDisplayName());
            params.put("description", type.getDescription());
            params.put("displayProperty", type.getDisplayProperty());
            params.put("typeKey", typeKey);
            session.run(cypher, params);
        }
    }

    @Override
    public void saveProperty(PropertyDef property, String domainKey, String typeKey, String propertyKey) {
        saveProperty(property, domainKey, typeKey, propertyKey, activeBuffer());
    }

    public void saveProperty(PropertyDef property, String domainKey, String typeKey, String propertyKey, String buffer) {
        String objectPath = domainKey + "." + typeKey + ".properties." + propertyKey;
        String bindingJson = toJson(property.getBinding());
        String cypher = """
            MATCH (t:Type {object_path: $typePath, buffer: $buffer})
            MERGE (p:Property {object_path: $objectPath, buffer: $buffer})
            SET p.name = $name,
                p.display_name = $displayName,
                p.type = $type,
                p.description = $description,
                p.pk_column = $pkColumn,
                p.binding = $binding,
                p.domain_key = $domainKey,
                p.type_key = $typeKey,
                p.property_key = $propertyKey
            MERGE (t)-[:HAS_PROPERTY]->(p)
            """;
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("typePath", domainKey + "." + typeKey);
            params.put("buffer", buffer);
            params.put("objectPath", objectPath);
            params.put("name", property.getName());
            params.put("displayName", property.getDisplayName());
            params.put("type", property.getType());
            params.put("description", property.getDescription());
            params.put("pkColumn", property.isPkColumn());
            params.put("binding", bindingJson);
            params.put("domainKey", domainKey);
            params.put("typeKey", typeKey);
            params.put("propertyKey", propertyKey);
            session.run(cypher, params);
        }
    }

    @Override
    public void saveRelationship(RelationshipDef relationship, String domainKey, String typeKey, String relationshipKey) {
        saveRelationship(relationship, domainKey, typeKey, relationshipKey, activeBuffer());
    }

    public void saveRelationship(RelationshipDef relationship, String domainKey, String typeKey, String relationshipKey, String buffer) {
        String objectPath = domainKey + "." + typeKey + ".relationships." + relationshipKey;
        String linkPropertiesJson = toJson(relationship.getLinkProperties());
        String cypher = """
            MATCH (t:Type {object_path: $typePath, buffer: $buffer})
            MERGE (r:Relationship {object_path: $objectPath, buffer: $buffer})
            SET r.name = $name,
                r.display_name = $displayName,
                r.description = $description,
                r.cardinality = $cardinality,
                r.join_type = $joinType,
                r.link_properties = $linkProperties,
                r.domain_key = $domainKey,
                r.type_key = $typeKey,
                r.relationship_key = $relationshipKey
            MERGE (t)-[:HAS_RELATIONSHIP]->(r)
            """;
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("typePath", domainKey + "." + typeKey);
            params.put("buffer", buffer);
            params.put("objectPath", objectPath);
            params.put("name", relationship.getName());
            params.put("displayName", relationship.getDisplayName());
            params.put("description", relationship.getDescription());
            params.put("cardinality", relationship.getCardinality() != null ? relationship.getCardinality().name() : null);
            params.put("joinType", relationship.getType() != null ? relationship.getType().name() : null);
            params.put("linkProperties", linkPropertiesJson);
            params.put("domainKey", domainKey);
            params.put("typeKey", typeKey);
            params.put("relationshipKey", relationshipKey);
            session.run(cypher, params);
        }
        createLinkToRelationships(relationship, objectPath, buffer);
    }

    private void createLinkToRelationships(RelationshipDef relationship, String relationshipPath, String buffer) {
        if (relationship.getLinkProperties() == null || relationship.getLinkProperties().isEmpty()) {
            return;
        }
        for (var linkProp : relationship.getLinkProperties()) {
            if (linkProp == null) {
                continue;
            }
            for (Map.Entry<String, String> entry : linkProp.entrySet()) {
                String sourcePath = entry.getKey();
                String targetPath = entry.getValue();
                String srcPropPath = resolveIdPathToObjectPath(sourcePath);
                String tgtPropPath = resolveIdPathToObjectPath(targetPath);

                String cypher = """
                    MATCH (r:Relationship {object_path: $relPath, buffer: $buffer})
                    MATCH (p:Property {object_path: $propPath, buffer: $buffer})
                    MERGE (r)-[:LINK_TO]->(p)
                    """;
                try (Session session = driver.session()) {
                    if (srcPropPath != null) {
                        session.run(cypher, Map.of("relPath", relationshipPath, "propPath", srcPropPath, "buffer", buffer));
                    }
                    if (tgtPropPath != null) {
                        session.run(cypher, Map.of("relPath", relationshipPath, "propPath", tgtPropPath, "buffer", buffer));
                    }
                } catch (Exception e) {
                    log.debug("Failed to create LINK_TO for relationship {}: {}", relationshipPath, e.getMessage());
                }
            }
        }
    }

    private String resolveIdPathToObjectPath(String idPath) {
        if (idPath == null || idPath.isEmpty()) {
            return null;
        }
        String[] parts = idPath.split("\\.");
        if (parts.length != 3) {
            return idPath;
        }
        // 优先使用 saveSnapshot 期间构建的 ID -> object_path 映射
        Map<String, String> idMap = idToObjectPathMap.get();
        if (idMap != null) {
            String objectPath = idMap.get(idPath);
            if (objectPath != null) {
                return objectPath;
            }
        }
        // 回退：尝试在 Neo4j 中按 property_key 查找
        return findPropertyObjectPathByIdParts(parts[0], parts[1], parts[2]);
    }

    private String findPropertyObjectPathByIdParts(String domainId, String typeId, String propertyId) {
        String cypher = """
            MATCH (p:Property {domain_key: $domainId, type_key: $typeId, property_key: $propertyId})
            RETURN p.object_path AS objectPath LIMIT 1
            """;
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of(
                    "domainId", domainId,
                    "typeId", typeId,
                    "propertyId", propertyId));
            if (result.hasNext()) {
                String path = result.next().get("objectPath").asString(null);
                if (path != null) {
                    return path;
                }
            }
        } catch (Exception e) {
            log.debug("Failed to resolve property object path by id parts {}.{}.{}: {}",
                    domainId, typeId, propertyId, e.getMessage());
        }
        return null;
    }

    @Override
    public void saveFunction(FunctionDef function, String domainKey, String typeKey, String functionKey) {
        saveFunction(function, domainKey, typeKey, functionKey, activeBuffer());
    }

    public void saveFunction(FunctionDef function, String domainKey, String typeKey, String functionKey, String buffer) {
        String objectPath = domainKey + "." + typeKey + ".functions." + functionKey;
        String dimensionsJson = toJson(function.getDimensions());
        String cypher = """
            MATCH (t:Type {object_path: $typePath, buffer: $buffer})
            MERGE (f:Function {object_path: $objectPath, buffer: $buffer})
            SET f.name = $name,
                f.display_name = $displayName,
                f.description = $description,
                f.type = $funcType,
                f.definition = $definition,
                f.dimensions = $dimensions,
                f.domain_key = $domainKey,
                f.type_key = $typeKey,
                f.function_key = $functionKey
            MERGE (t)-[:HAS_FUNCTION]->(f)
            """;
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("typePath", domainKey + "." + typeKey);
            params.put("buffer", buffer);
            params.put("objectPath", objectPath);
            params.put("name", function.getName());
            params.put("displayName", function.getDisplayName());
            params.put("description", function.getDescription());
            params.put("funcType", function.getType());
            params.put("definition", function.getDefinition());
            params.put("dimensions", dimensionsJson);
            params.put("domainKey", domainKey);
            params.put("typeKey", typeKey);
            params.put("functionKey", functionKey);
            session.run(cypher, params);
        }
        createUsesDimensionRelationships(function, objectPath, buffer);
    }

    private void createUsesDimensionRelationships(FunctionDef function, String functionPath, String buffer) {
        if (function.getDimensions() == null || function.getDimensions().isEmpty()) {
            return;
        }
        for (String dimPath : function.getDimensions()) {
            String cypher = """
                MATCH (f:Function {object_path: $funcPath, buffer: $buffer})
                MATCH (p:Property {object_path: $propPath, buffer: $buffer})
                MERGE (f)-[:USES_DIMENSION]->(p)
                """;
            try (Session session = driver.session()) {
                session.run(cypher, Map.of("funcPath", functionPath, "propPath", dimPath, "buffer", buffer));
            } catch (Exception e) {
                log.debug("Failed to create USES_DIMENSION from {} to {}: {}", functionPath, dimPath, e.getMessage());
            }
        }
    }

    @Override
    public void saveRule(RuleDef rule, String domainKey, String typeKey, String functionKey, String ruleKey) {
        saveRule(rule, domainKey, typeKey, functionKey, ruleKey, activeBuffer());
    }

    public void saveRule(RuleDef rule, String domainKey, String typeKey, String functionKey, String ruleKey, String buffer) {
        String objectPath = domainKey + "." + typeKey + ".functions." + functionKey + ".rules." + ruleKey;
        String cypher = """
            MATCH (f:Function {object_path: $functionPath, buffer: $buffer})
            MERGE (r:Rule {object_path: $objectPath, buffer: $buffer})
            SET r.name = $name,
                r.display_name = $displayName,
                r.description = $description,
                r.type = $ruleType,
                r.definition = $definition,
                r.domain_key = $domainKey,
                r.type_key = $typeKey,
                r.function_key = $functionKey,
                r.rule_key = $ruleKey
            MERGE (f)-[:HAS_RULE]->(r)
            """;
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("functionPath", domainKey + "." + typeKey + ".functions." + functionKey);
            params.put("buffer", buffer);
            params.put("objectPath", objectPath);
            params.put("name", rule.getName());
            params.put("displayName", rule.getDisplayName());
            params.put("description", rule.getDescription());
            params.put("ruleType", rule.getType());
            params.put("definition", rule.getDefinition());
            params.put("domainKey", domainKey);
            params.put("typeKey", typeKey);
            params.put("functionKey", functionKey);
            params.put("ruleKey", ruleKey);
            session.run(cypher, params);
        }
    }

    @Override
    public void saveSnapshot(TBoxSnapshot snapshot) {
        saveSnapshot(snapshot, activeBuffer());
    }

    @Override
    public void saveSnapshot(TBoxSnapshot snapshot, String buffer) {
        if (snapshot == null || snapshot.getDomains() == null) {
            return;
        }
        Map<String, String> idMap = new HashMap<>();
        idToObjectPathMap.set(idMap);
        try {
            snapshot.getDomains().forEach((domainKey, domain) -> {
                saveDomain(domain, domainKey, buffer);
                if (domain.getTypes() != null) {
                    domain.getTypes().forEach((typeKey, type) -> {
                        saveType(type, domainKey, typeKey, buffer);
                        if (type.getProperties() != null) {
                            type.getProperties().forEach((propertyKey, property) -> {
                                saveProperty(property, domainKey, typeKey, propertyKey, buffer);
                                // 记录原始 ID path -> object_path 映射，用于解析 relationship.linkProperties
                                String domainId = domain.getId();
                                String typeId = type.getId();
                                String propId = property.getId();
                                if (domainId != null && typeId != null && propId != null) {
                                    String idPath = domainId + "." + typeId + "." + propId;
                                    String objectPath = domainKey + "." + typeKey + ".properties." + propertyKey;
                                    idMap.put(idPath, objectPath);
                                }
                            });
                        }
                        if (type.getRelationships() != null) {
                            type.getRelationships().forEach((relationshipKey, relationship) ->
                                saveRelationship(relationship, domainKey, typeKey, relationshipKey, buffer));
                        }
                        if (type.getFunctions() != null) {
                            type.getFunctions().forEach((functionKey, function) -> {
                                saveFunction(function, domainKey, typeKey, functionKey, buffer);
                                if (function.getRules() != null) {
                                    function.getRules().forEach((ruleKey, rule) ->
                                        saveRule(rule, domainKey, typeKey, functionKey, ruleKey, buffer));
                                }
                            });
                        }
                    });
                }
            });
        } finally {
            idToObjectPathMap.remove();
        }
    }

    // ========== QUERY with buffer ==========

    @Override
    public Optional<DomainDef> findDomainByKey(String domainKey) {
        return findDomainByKey(domainKey, activeBuffer());
    }

    @Override
    public Optional<DomainDef> findDomainByKey(String domainKey, String buffer) {
        String cypher = "MATCH (d:Domain {object_path: $domainKey, buffer: $buffer}) RETURN d";
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("domainKey", domainKey, "buffer", buffer));
            if (result.hasNext()) {
                Node node = result.next().get("d").asNode();
                return Optional.of(mapNodeToDomainDef(node));
            }
        }
        return Optional.empty();
    }

    @Override
    public Optional<TypeDef> findTypeByPath(String typePath) {
        String cypher = "MATCH (t:Type {object_path: $typePath, buffer: $buffer}) RETURN t";
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("typePath", typePath, "buffer", activeBuffer()));
            if (result.hasNext()) {
                Node node = result.next().get("t").asNode();
                return Optional.of(mapNodeToTypeDef(node));
            }
        }
        return Optional.empty();
    }

    @Override
    public Optional<PropertyDef> findPropertyByPath(String propertyPath) {
        String cypher = "MATCH (p:Property {object_path: $propertyPath, buffer: $buffer}) RETURN p";
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("propertyPath", propertyPath, "buffer", activeBuffer()));
            if (result.hasNext()) {
                Node node = result.next().get("p").asNode();
                return Optional.of(mapNodeToPropertyDef(node));
            }
        }
        return Optional.empty();
    }

    @Override
    public List<DomainDef> findAllDomains() {
        return findAllDomains(activeBuffer());
    }

    @Override
    public List<DomainDef> findAllDomains(String buffer) {
        String cypher = "MATCH (d:Domain {buffer: $buffer}) RETURN d";
        List<DomainDef> domains = new ArrayList<>();
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("buffer", buffer));
            while (result.hasNext()) {
                Node node = result.next().get("d").asNode();
                domains.add(mapNodeToDomainDef(node));
            }
        }
        return domains;
    }

    @Override
    public List<TypeDef> findTypesByDomain(String domainKey) {
        return findTypesByDomain(domainKey, activeBuffer());
    }

    @Override
    public List<TypeDef> findTypesByDomain(String domainKey, String buffer) {
        String cypher = """
            MATCH (d:Domain {object_path: $domainKey, buffer: $buffer})-[:HAS_TYPE]->(t:Type)
            RETURN t
            """;
        List<TypeDef> types = new ArrayList<>();
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("domainKey", domainKey, "buffer", buffer));
            while (result.hasNext()) {
                Node node = result.next().get("t").asNode();
                types.add(mapNodeToTypeDef(node));
            }
        }
        return types;
    }

    @Override
    public List<PropertyDef> findPropertiesByType(String domainKey, String typeKey) {
        return findPropertiesByType(domainKey, typeKey, activeBuffer());
    }

    @Override
    public List<PropertyDef> findPropertiesByType(String domainKey, String typeKey, String buffer) {
        String typePath = domainKey + "." + typeKey;
        String cypher = """
            MATCH (t:Type {object_path: $typePath, buffer: $buffer})-[:HAS_PROPERTY]->(p:Property)
            RETURN p
            """;
        List<PropertyDef> properties = new ArrayList<>();
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("typePath", typePath, "buffer", buffer));
            while (result.hasNext()) {
                Node node = result.next().get("p").asNode();
                properties.add(mapNodeToPropertyDef(node));
            }
        }
        return properties;
    }

    @Override
    public List<RelationshipDef> findRelationshipsByType(String domainKey, String typeKey) {
        return findRelationshipsByType(domainKey, typeKey, activeBuffer());
    }

    @Override
    public List<RelationshipDef> findRelationshipsByType(String domainKey, String typeKey, String buffer) {
        String typePath = domainKey + "." + typeKey;
        String cypher = """
            MATCH (t:Type {object_path: $typePath, buffer: $buffer})-[:HAS_RELATIONSHIP]->(r:Relationship)
            RETURN r
            """;
        List<RelationshipDef> relationships = new ArrayList<>();
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("typePath", typePath, "buffer", buffer));
            while (result.hasNext()) {
                Node node = result.next().get("r").asNode();
                relationships.add(mapNodeToRelationshipDef(node));
            }
        }
        return relationships;
    }

    @Override
    public List<FunctionDef> findFunctionsByType(String domainKey, String typeKey) {
        return findFunctionsByType(domainKey, typeKey, activeBuffer());
    }

    @Override
    public List<FunctionDef> findFunctionsByType(String domainKey, String typeKey, String buffer) {
        String typePath = domainKey + "." + typeKey;
        String cypher = """
            MATCH (t:Type {object_path: $typePath, buffer: $buffer})-[:HAS_FUNCTION]->(f:Function)
            RETURN f
            """;
        List<FunctionDef> functions = new ArrayList<>();
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("typePath", typePath, "buffer", buffer));
            while (result.hasNext()) {
                Node node = result.next().get("f").asNode();
                functions.add(mapNodeToFunctionDef(node));
            }
        }
        return functions;
    }

    @Override
    public List<RuleDef> findRulesByFunction(String domainKey, String typeKey, String functionKey) {
        return findRulesByFunction(domainKey, typeKey, functionKey, activeBuffer());
    }

    @Override
    public List<RuleDef> findRulesByFunction(String domainKey, String typeKey, String functionKey, String buffer) {
        String functionPath = domainKey + "." + typeKey + ".functions." + functionKey;
        String cypher = """
            MATCH (f:Function {object_path: $functionPath, buffer: $buffer})-[:HAS_RULE]->(r:Rule)
            RETURN r
            """;
        List<RuleDef> rules = new ArrayList<>();
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("functionPath", functionPath, "buffer", buffer));
            while (result.hasNext()) {
                Node node = result.next().get("r").asNode();
                rules.add(mapNodeToRuleDef(node));
            }
        }
        return rules;
    }

    @Override
    public long countObjects() {
        return countObjects(activeBuffer());
    }

    @Override
    public long countObjects(String buffer) {
        String cypher = """
            MATCH (n)
            WHERE n.buffer = $buffer
              AND (n:Domain OR n:Type OR n:Property OR n:Relationship OR n:Function OR n:Rule)
            RETURN count(n) AS cnt
            """;
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("buffer", buffer));
            if (result.hasNext()) {
                return result.next().get("cnt").asLong();
            }
        }
        return 0;
    }

    @Override
    public void clearAll() {
        clearBuffer(activeBuffer());
    }

    @Override
    public void clearBuffer(String buffer) {
        String cypher = """
            MATCH (n)
            WHERE n.buffer = $buffer
              AND (n:Domain OR n:Type OR n:Property OR n:Relationship OR n:Function OR n:Rule)
            DETACH DELETE n
            """;
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("buffer", buffer));
            log.info("Cleared graph buffer: {}", buffer);
        }
    }

    @Override
    public void promoteBuffer(String fromBuffer, String toBuffer) {
        // 1. 先删除目标 buffer 的旧数据
        clearBuffer(toBuffer);
        // 2. 将源 buffer 的数据改为目标 buffer
        String cypher = """
            MATCH (n)
            WHERE n.buffer = $fromBuffer
              AND (n:Domain OR n:Type OR n:Property OR n:Relationship OR n:Function OR n:Rule)
            SET n.buffer = $toBuffer
            """;
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("fromBuffer", fromBuffer, "toBuffer", toBuffer));
            log.info("Promoted graph buffer: {} -> {}", fromBuffer, toBuffer);
        }
    }

    @Override
    public boolean exists(String objectPath) {
        String cypher = """
            MATCH (n)
            WHERE n.object_path = $objectPath AND n.buffer = $buffer
            RETURN count(n) AS cnt
            """;
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
            if (result.hasNext()) {
                return result.next().get("cnt").asInt() > 0;
            }
        }
        return false;
    }

    @Override
    public Optional<Object> findByObjectPath(String objectPath) {
        Optional<PropertyDef> prop = findPropertyByPath(objectPath);
        if (prop.isPresent()) return Optional.of(prop.get());

        Optional<TypeDef> type = findTypeByPath(objectPath);
        if (type.isPresent()) return Optional.of(type.get());

        Optional<DomainDef> domain = findDomainByKey(objectPath);
        if (domain.isPresent()) return Optional.of(domain.get());

        Optional<RuleDef> rule = findRuleByPath(objectPath);
        if (rule.isPresent()) return Optional.of(rule.get());

        return Optional.empty();
    }

    private Optional<RuleDef> findRuleByPath(String objectPath) {
        String cypher = "MATCH (r:Rule {object_path: $objectPath, buffer: $buffer}) RETURN r";
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
            if (result.hasNext()) {
                Node node = result.next().get("r").asNode();
                return Optional.of(mapNodeToRuleDef(node));
            }
        }
        return Optional.empty();
    }

    @Override
    public List<GraphEdge> findNeighbors(String objectPath, Direction direction, List<String> relationTypes) {
        return findNeighbors(objectPath, direction, relationTypes, activeBuffer());
    }

    @Override
    public List<GraphEdge> findNeighbors(String objectPath, Direction direction, List<String> relationTypes, String buffer) {
        List<GraphEdge> edges = new ArrayList<>();
        StringBuilder cypher = new StringBuilder();
        cypher.append("MATCH (n {object_path: $objectPath, buffer: $buffer})");

        switch (direction) {
            case OUTGOING -> cypher.append("-[r]->(m {buffer: $buffer})");
            case INCOMING -> cypher.append("<-[r]-(m {buffer: $buffer})");
            case BOTH -> cypher.append("-[r]-(m {buffer: $buffer})");
        }

        if (relationTypes != null && !relationTypes.isEmpty()) {
            cypher.append(" WHERE type(r) IN $relationTypes");
        }
        cypher.append(" RETURN n.object_path AS source, type(r) AS relationType, m.object_path AS target");

        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("objectPath", objectPath);
            params.put("buffer", buffer);
            if (relationTypes != null && !relationTypes.isEmpty()) {
                params.put("relationTypes", relationTypes);
            }
            Result result = session.run(cypher.toString(), params);
            while (result.hasNext()) {
                Record record = result.next();
                String source = record.get("source").asString(null);
                String relType = record.get("relationType").asString(null);
                String target = record.get("target").asString(null);
                if (source != null && relType != null && target != null) {
                    edges.add(GraphEdge.builder()
                            .sourcePath(source)
                            .relationType(relType)
                            .targetPath(target)
                            .build());
                }
            }
        }
        return edges;
    }

    // ========== Mapping helpers ==========

    private DomainDef mapNodeToDomainDef(Node node) {
        return DomainDef.builder()
                .name(node.get("name").asString(null))
                .displayName(node.get("display_name").asString(null))
                .description(node.get("description").asString(null))
                .build();
    }

    private TypeDef mapNodeToTypeDef(Node node) {
        return TypeDef.builder()
                .name(node.get("name").asString(null))
                .displayName(node.get("display_name").asString(null))
                .description(node.get("description").asString(null))
                .displayProperty(node.get("display_property").asString(null))
                .build();
    }

    private PropertyDef mapNodeToPropertyDef(Node node) {
        String bindingJson = node.get("binding").asString(null);
        return PropertyDef.builder()
                .name(node.get("name").asString(null))
                .displayName(node.get("display_name").asString(null))
                .type(node.get("type").asString(null))
                .description(node.get("description").asString(null))
                .pkColumn(node.get("pk_column").asBoolean(false))
                .binding(fromJson(bindingJson, com.onto.oaas.model.Binding.class))
                .build();
    }

    private RelationshipDef mapNodeToRelationshipDef(Node node) {
        String linkPropertiesJson = node.get("link_properties").asString(null);
        return RelationshipDef.builder()
                .name(node.get("name").asString(null))
                .displayName(node.get("display_name").asString(null))
                .description(node.get("description").asString(null))
                .cardinality(parseEnum(node.get("cardinality").asString(null), com.onto.oaas.model.enums.Cardinality.class))
                .type(parseEnum(node.get("join_type").asString(null), com.onto.oaas.model.enums.JoinType.class))
                .linkProperties(fromJson(linkPropertiesJson, new com.fasterxml.jackson.core.type.TypeReference<List<Map<String, String>>>() {}))
                .build();
    }

    private FunctionDef mapNodeToFunctionDef(Node node) {
        String dimensionsJson = node.get("dimensions").asString(null);
        return FunctionDef.builder()
                .name(node.get("name").asString(null))
                .displayName(node.get("display_name").asString(null))
                .description(node.get("description").asString(null))
                .type(node.get("type").asString(null))
                .definition(node.get("definition").asString(null))
                .dimensions(fromJsonList(dimensionsJson, String.class))
                .build();
    }

    private RuleDef mapNodeToRuleDef(Node node) {
        return RuleDef.builder()
                .name(node.get("name").asString(null))
                .displayName(node.get("display_name").asString(null))
                .description(node.get("description").asString(null))
                .type(node.get("type").asString(null))
                .definition(node.get("definition").asString(null))
                .build();
    }

    // ========== JSON helpers ==========

    private String toJson(Object obj) {
        if (obj == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    private <T> T fromJson(String json, Class<T> clazz) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, clazz);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    private <T> List<T> fromJsonList(String json, Class<T> clazz) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, objectMapper.getTypeFactory().constructCollectionType(List.class, clazz));
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    private <T> T fromJson(String json, com.fasterxml.jackson.core.type.TypeReference<T> typeRef) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, typeRef);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    private <E extends Enum<E>> E parseEnum(String value, Class<E> enumClass) {
        if (value == null || value.isEmpty()) {
            return null;
        }
        try {
            return Enum.valueOf(enumClass, value);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    // ========== DELETE operations (保持原有实现，操作 active buffer) ==========

    @Override
    public void deleteDomain(String domainKey) {
        String cypher = """
            MATCH (d:Domain {object_path: $domainKey, buffer: $buffer})
            OPTIONAL MATCH (d)-[:HAS_TYPE]->(t:Type)
            OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:Property)
            OPTIONAL MATCH (t)-[:HAS_RELATIONSHIP]->(r:Relationship)
            OPTIONAL MATCH (t)-[:HAS_FUNCTION]->(f:Function)
            OPTIONAL MATCH (f)-[:HAS_RULE]->(ru:Rule)
            DETACH DELETE d, t, p, r, f, ru
            """;
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("domainKey", domainKey, "buffer", activeBuffer()));
        }
    }

    @Override
    public void deleteType(String domainKey, String typeKey) {
        String objectPath = domainKey + "." + typeKey;
        String cypher = """
            MATCH (t:Type {object_path: $objectPath, buffer: $buffer})
            OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:Property)
            OPTIONAL MATCH (t)-[:HAS_RELATIONSHIP]->(r:Relationship)
            OPTIONAL MATCH (t)-[:HAS_FUNCTION]->(f:Function)
            OPTIONAL MATCH (f)-[:HAS_RULE]->(ru:Rule)
            DETACH DELETE t, p, r, f, ru
            """;
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
        }
    }

    @Override
    public void deleteProperty(String objectPath) {
        String cypher = "MATCH (p:Property {object_path: $objectPath, buffer: $buffer}) DETACH DELETE p";
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
        }
    }

    @Override
    public void deleteRelationship(String objectPath) {
        String cypher = "MATCH (r:Relationship {object_path: $objectPath, buffer: $buffer}) DETACH DELETE r";
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
        }
    }

    @Override
    public void deleteFunction(String domainKey, String typeKey, String functionKey) {
        String objectPath = domainKey + "." + typeKey + ".functions." + functionKey;
        String cypher = """
            MATCH (f:Function {object_path: $objectPath, buffer: $buffer})
            OPTIONAL MATCH (f)-[:HAS_RULE]->(r:Rule)
            DETACH DELETE f, r
            """;
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
        }
    }

    @Override
    public void deleteRule(String objectPath) {
        String cypher = "MATCH (r:Rule {object_path: $objectPath, buffer: $buffer}) DETACH DELETE r";
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
        }
    }
}
