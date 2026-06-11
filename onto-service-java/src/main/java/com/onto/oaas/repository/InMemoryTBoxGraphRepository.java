package com.onto.oaas.repository;

import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.GraphEdge;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.Direction;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Repository;

/**
 * 内存模式图仓库。
 *
 * <p>当 Neo4j 不可用时，使用内存存储替代，支持 Kafka 消费链路测试。</p>
 * <p>注意：内存模式重启后数据丢失，仅用于开发和测试环境。</p>
 */
@Slf4j
@Repository
public class InMemoryTBoxGraphRepository implements TBoxGraphRepository {

    // ---------- buffer-scoped storage ----------
    private final Map<String, Map<String, DomainDef>> domainsByBuffer = new ConcurrentHashMap<>();
    private final Map<String, Map<String, TypeDef>> typesByBuffer = new ConcurrentHashMap<>();
    private final Map<String, Map<String, PropertyDef>> propertiesByBuffer = new ConcurrentHashMap<>();
    private final Map<String, Map<String, RelationshipDef>> relationshipsByBuffer = new ConcurrentHashMap<>();
    private final Map<String, Map<String, FunctionDef>> functionsByBuffer = new ConcurrentHashMap<>();
    private final Map<String, Map<String, RuleDef>> rulesByBuffer = new ConcurrentHashMap<>();
    private final Map<String, List<GraphEdge>> edgesByBuffer = new ConcurrentHashMap<>();

    public InMemoryTBoxGraphRepository() {
        log.info("InMemoryTBoxGraphRepository initialized (no Neo4j required)");
    }

    // ---------- helpers ----------

    private Map<String, DomainDef> domains(String buffer) {
        return domainsByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    private Map<String, TypeDef> types(String buffer) {
        return typesByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    private Map<String, PropertyDef> properties(String buffer) {
        return propertiesByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    private Map<String, RelationshipDef> relationships(String buffer) {
        return relationshipsByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    private Map<String, FunctionDef> functions(String buffer) {
        return functionsByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    private Map<String, RuleDef> rules(String buffer) {
        return rulesByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    private List<GraphEdge> edges(String buffer) {
        return edgesByBuffer.computeIfAbsent(buffer, k -> Collections.synchronizedList(new ArrayList<>()));
    }

    // ========== SAVE operations ==========

    @Override
    public void saveDomain(DomainDef domain, String domainKey) {
        saveDomain(domain, domainKey, activeBuffer());
    }

    private void saveDomain(DomainDef domain, String domainKey, String buffer) {
        domains(buffer).put(domainKey, domain);
    }

    @Override
    public void saveType(TypeDef type, String domainKey, String typeKey) {
        saveType(type, domainKey, typeKey, activeBuffer());
    }

    private void saveType(TypeDef type, String domainKey, String typeKey, String buffer) {
        String path = domainKey + "." + typeKey;
        types(buffer).put(path, type);
        edges(buffer).add(GraphEdge.builder()
                .sourcePath(domainKey)
                .relationType("HAS_TYPE")
                .targetPath(path)
                .build());
    }

    @Override
    public void saveProperty(PropertyDef property, String domainKey, String typeKey, String propertyKey) {
        saveProperty(property, domainKey, typeKey, propertyKey, activeBuffer());
    }

    private void saveProperty(PropertyDef property, String domainKey, String typeKey, String propertyKey, String buffer) {
        String path = domainKey + "." + typeKey + ".properties." + propertyKey;
        properties(buffer).put(path, property);
        edges(buffer).add(GraphEdge.builder()
                .sourcePath(domainKey + "." + typeKey)
                .relationType("HAS_PROPERTY")
                .targetPath(path)
                .build());
    }

    @Override
    public void saveRelationship(RelationshipDef relationship, String domainKey, String typeKey, String relationshipKey) {
        saveRelationship(relationship, domainKey, typeKey, relationshipKey, activeBuffer());
    }

    private void saveRelationship(RelationshipDef relationship, String domainKey, String typeKey, String relationshipKey, String buffer) {
        String path = domainKey + "." + typeKey + ".relationships." + relationshipKey;
        relationships(buffer).put(path, relationship);
        edges(buffer).add(GraphEdge.builder()
                .sourcePath(domainKey + "." + typeKey)
                .relationType("HAS_RELATIONSHIP")
                .targetPath(path)
                .build());
    }

    @Override
    public void saveFunction(FunctionDef function, String domainKey, String typeKey, String functionKey) {
        saveFunction(function, domainKey, typeKey, functionKey, activeBuffer());
    }

    private void saveFunction(FunctionDef function, String domainKey, String typeKey, String functionKey, String buffer) {
        String path = domainKey + "." + typeKey + ".functions." + functionKey;
        functions(buffer).put(path, function);
        edges(buffer).add(GraphEdge.builder()
                .sourcePath(domainKey + "." + typeKey)
                .relationType("HAS_FUNCTION")
                .targetPath(path)
                .build());
        if (function.getDimensions() != null) {
            for (String dimPath : function.getDimensions()) {
                edges(buffer).add(GraphEdge.builder()
                        .sourcePath(path)
                        .relationType("USES_DIMENSION")
                        .targetPath(dimPath)
                        .build());
            }
        }
    }

    @Override
    public void saveRule(RuleDef rule, String domainKey, String typeKey, String functionKey, String ruleKey) {
        saveRule(rule, domainKey, typeKey, functionKey, ruleKey, activeBuffer());
    }

    private void saveRule(RuleDef rule, String domainKey, String typeKey, String functionKey, String ruleKey, String buffer) {
        String path = domainKey + "." + typeKey + ".functions." + functionKey + ".rules." + ruleKey;
        rules(buffer).put(path, rule);
        String functionPath = domainKey + "." + typeKey + ".functions." + functionKey;
        edges(buffer).add(GraphEdge.builder()
                .sourcePath(functionPath)
                .relationType("HAS_RULE")
                .targetPath(path)
                .build());
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
        snapshot.getDomains().forEach((domainKey, domain) -> {
            saveDomain(domain, domainKey, buffer);
            if (domain.getTypes() != null) {
                domain.getTypes().forEach((typeKey, type) -> {
                    saveType(type, domainKey, typeKey, buffer);
                    if (type.getProperties() != null) {
                        type.getProperties().forEach((propertyKey, property) ->
                            saveProperty(property, domainKey, typeKey, propertyKey, buffer));
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
    }

    // ========== QUERY operations ==========

    @Override
    public Optional<DomainDef> findDomainByKey(String domainKey) {
        return findDomainByKey(domainKey, activeBuffer());
    }

    @Override
    public Optional<DomainDef> findDomainByKey(String domainKey, String buffer) {
        return Optional.ofNullable(domains(buffer).get(domainKey));
    }

    @Override
    public Optional<TypeDef> findTypeByPath(String typePath) {
        return Optional.ofNullable(types(activeBuffer()).get(typePath));
    }

    @Override
    public Optional<PropertyDef> findPropertyByPath(String propertyPath) {
        return Optional.ofNullable(properties(activeBuffer()).get(propertyPath));
    }

    @Override
    public List<DomainDef> findAllDomains() {
        return findAllDomains(activeBuffer());
    }

    @Override
    public List<DomainDef> findAllDomains(String buffer) {
        return new ArrayList<>(domains(buffer).values());
    }

    @Override
    public List<TypeDef> findTypesByDomain(String domainKey) {
        return findTypesByDomain(domainKey, activeBuffer());
    }

    @Override
    public List<TypeDef> findTypesByDomain(String domainKey, String buffer) {
        return edges(buffer).stream()
                .filter(e -> e.getSourcePath().equals(domainKey) && "HAS_TYPE".equals(e.getRelationType()))
                .map(e -> types(buffer).get(e.getTargetPath()))
                .collect(Collectors.toList());
    }

    @Override
    public List<PropertyDef> findPropertiesByType(String domainKey, String typeKey) {
        return findPropertiesByType(domainKey, typeKey, activeBuffer());
    }

    @Override
    public List<PropertyDef> findPropertiesByType(String domainKey, String typeKey, String buffer) {
        String typePath = domainKey + "." + typeKey;
        return edges(buffer).stream()
                .filter(e -> e.getSourcePath().equals(typePath) && "HAS_PROPERTY".equals(e.getRelationType()))
                .map(e -> properties(buffer).get(e.getTargetPath()))
                .collect(Collectors.toList());
    }

    @Override
    public List<RelationshipDef> findRelationshipsByType(String domainKey, String typeKey) {
        return findRelationshipsByType(domainKey, typeKey, activeBuffer());
    }

    @Override
    public List<RelationshipDef> findRelationshipsByType(String domainKey, String typeKey, String buffer) {
        String typePath = domainKey + "." + typeKey;
        return edges(buffer).stream()
                .filter(e -> e.getSourcePath().equals(typePath) && "HAS_RELATIONSHIP".equals(e.getRelationType()))
                .map(e -> relationships(buffer).get(e.getTargetPath()))
                .collect(Collectors.toList());
    }

    @Override
    public List<FunctionDef> findFunctionsByType(String domainKey, String typeKey) {
        return findFunctionsByType(domainKey, typeKey, activeBuffer());
    }

    @Override
    public List<FunctionDef> findFunctionsByType(String domainKey, String typeKey, String buffer) {
        String typePath = domainKey + "." + typeKey;
        return edges(buffer).stream()
                .filter(e -> e.getSourcePath().equals(typePath) && "HAS_FUNCTION".equals(e.getRelationType()))
                .map(e -> functions(buffer).get(e.getTargetPath()))
                .collect(Collectors.toList());
    }

    @Override
    public List<RuleDef> findRulesByFunction(String domainKey, String typeKey, String functionKey) {
        return findRulesByFunction(domainKey, typeKey, functionKey, activeBuffer());
    }

    @Override
    public List<RuleDef> findRulesByFunction(String domainKey, String typeKey, String functionKey, String buffer) {
        String functionPath = domainKey + "." + typeKey + ".functions." + functionKey;
        return edges(buffer).stream()
                .filter(e -> e.getSourcePath().equals(functionPath) && "HAS_RULE".equals(e.getRelationType()))
                .map(e -> rules(buffer).get(e.getTargetPath()))
                .collect(Collectors.toList());
    }

    @Override
    public long countObjects() {
        return countObjects(activeBuffer());
    }

    @Override
    public long countObjects(String buffer) {
        return domains(buffer).size()
                + types(buffer).size()
                + properties(buffer).size()
                + relationships(buffer).size()
                + functions(buffer).size()
                + rules(buffer).size();
    }

    @Override
    public void clearAll() {
        domainsByBuffer.clear();
        typesByBuffer.clear();
        propertiesByBuffer.clear();
        relationshipsByBuffer.clear();
        functionsByBuffer.clear();
        rulesByBuffer.clear();
        edgesByBuffer.clear();
    }

    @Override
    public void clearBuffer(String buffer) {
        domainsByBuffer.remove(buffer);
        typesByBuffer.remove(buffer);
        propertiesByBuffer.remove(buffer);
        relationshipsByBuffer.remove(buffer);
        functionsByBuffer.remove(buffer);
        rulesByBuffer.remove(buffer);
        edgesByBuffer.remove(buffer);
    }

    @Override
    public void promoteBuffer(String fromBuffer, String toBuffer) {
        clearBuffer(toBuffer);
        Map<String, DomainDef> d = domainsByBuffer.remove(fromBuffer);
        if (d != null) domainsByBuffer.put(toBuffer, d);
        Map<String, TypeDef> t = typesByBuffer.remove(fromBuffer);
        if (t != null) typesByBuffer.put(toBuffer, t);
        Map<String, PropertyDef> p = propertiesByBuffer.remove(fromBuffer);
        if (p != null) propertiesByBuffer.put(toBuffer, p);
        Map<String, RelationshipDef> r = relationshipsByBuffer.remove(fromBuffer);
        if (r != null) relationshipsByBuffer.put(toBuffer, r);
        Map<String, FunctionDef> f = functionsByBuffer.remove(fromBuffer);
        if (f != null) functionsByBuffer.put(toBuffer, f);
        Map<String, RuleDef> ru = rulesByBuffer.remove(fromBuffer);
        if (ru != null) rulesByBuffer.put(toBuffer, ru);
        List<GraphEdge> e = edgesByBuffer.remove(fromBuffer);
        if (e != null) edgesByBuffer.put(toBuffer, e);
    }

    @Override
    public boolean exists(String objectPath) {
        String b = activeBuffer();
        return domains(b).containsKey(objectPath)
                || types(b).containsKey(objectPath)
                || properties(b).containsKey(objectPath)
                || relationships(b).containsKey(objectPath)
                || functions(b).containsKey(objectPath)
                || rules(b).containsKey(objectPath);
    }

    @Override
    public Optional<Object> findByObjectPath(String objectPath) {
        String b = activeBuffer();
        if (domains(b).containsKey(objectPath)) return Optional.of(domains(b).get(objectPath));
        if (types(b).containsKey(objectPath)) return Optional.of(types(b).get(objectPath));
        if (properties(b).containsKey(objectPath)) return Optional.of(properties(b).get(objectPath));
        return Optional.empty();
    }

    @Override
    public List<GraphEdge> findNeighbors(String objectPath, Direction direction, List<String> relationTypes) {
        return findNeighbors(objectPath, direction, relationTypes, activeBuffer());
    }

    @Override
    public List<GraphEdge> findNeighbors(String objectPath, Direction direction, List<String> relationTypes, String buffer) {
        List<GraphEdge> result = new ArrayList<>();
        for (GraphEdge edge : edges(buffer)) {
            boolean matches = false;
            if (direction == Direction.BOTH) {
                matches = edge.getSourcePath().equals(objectPath) || edge.getTargetPath().equals(objectPath);
            } else if (direction == Direction.OUTGOING) {
                matches = edge.getSourcePath().equals(objectPath);
            } else if (direction == Direction.INCOMING) {
                matches = edge.getTargetPath().equals(objectPath);
            }
            if (matches && (relationTypes == null || relationTypes.isEmpty() || relationTypes.contains(edge.getRelationType()))) {
                result.add(edge);
            }
        }
        return result;
    }

    // ========== DELETE operations ==========

    @Override
    public void deleteDomain(String domainKey) {
        String b = activeBuffer();
        domains(b).remove(domainKey);
        types(b).entrySet().removeIf(e -> e.getKey().startsWith(domainKey + "."));
        properties(b).entrySet().removeIf(e -> e.getKey().startsWith(domainKey + "."));
        relationships(b).entrySet().removeIf(e -> e.getKey().startsWith(domainKey + "."));
        functions(b).entrySet().removeIf(e -> e.getKey().startsWith(domainKey + "."));
        rules(b).entrySet().removeIf(e -> e.getKey().startsWith(domainKey + "."));
        edges(b).removeIf(e -> e.getSourcePath().equals(domainKey)
                || e.getSourcePath().startsWith(domainKey + ".")
                || e.getTargetPath().equals(domainKey)
                || e.getTargetPath().startsWith(domainKey + "."));
    }

    @Override
    public void deleteType(String domainKey, String typeKey) {
        String b = activeBuffer();
        String typePath = domainKey + "." + typeKey;
        types(b).remove(typePath);
        properties(b).entrySet().removeIf(e -> e.getKey().startsWith(typePath + "."));
        relationships(b).entrySet().removeIf(e -> e.getKey().startsWith(typePath + "."));
        functions(b).entrySet().removeIf(e -> e.getKey().startsWith(typePath + "."));
        rules(b).entrySet().removeIf(e -> e.getKey().startsWith(typePath + "."));
        edges(b).removeIf(e -> e.getSourcePath().equals(typePath)
                || e.getSourcePath().startsWith(typePath + ".")
                || e.getTargetPath().equals(typePath)
                || e.getTargetPath().startsWith(typePath + "."));
    }

    @Override
    public void deleteProperty(String objectPath) {
        String b = activeBuffer();
        properties(b).remove(objectPath);
        edges(b).removeIf(e -> e.getSourcePath().equals(objectPath) || e.getTargetPath().equals(objectPath));
    }

    @Override
    public void deleteRelationship(String objectPath) {
        String b = activeBuffer();
        relationships(b).remove(objectPath);
        edges(b).removeIf(e -> e.getSourcePath().equals(objectPath) || e.getTargetPath().equals(objectPath));
    }

    @Override
    public void deleteFunction(String domainKey, String typeKey, String functionKey) {
        String b = activeBuffer();
        String functionPath = domainKey + "." + typeKey + ".functions." + functionKey;
        functions(b).remove(functionPath);
        rules(b).entrySet().removeIf(e -> e.getKey().startsWith(functionPath + "."));
        edges(b).removeIf(e -> e.getSourcePath().equals(functionPath)
                || e.getSourcePath().startsWith(functionPath + ".")
                || e.getTargetPath().equals(functionPath)
                || e.getTargetPath().startsWith(functionPath + "."));
    }

    @Override
    public void deleteRule(String objectPath) {
        String b = activeBuffer();
        rules(b).remove(objectPath);
        edges(b).removeIf(e -> e.getSourcePath().equals(objectPath) || e.getTargetPath().equals(objectPath));
    }
}
