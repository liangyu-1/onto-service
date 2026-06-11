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
import java.util.List;
import java.util.Optional;

public interface TBoxGraphRepository {

    void saveDomain(DomainDef domain, String domainKey);

    void saveType(TypeDef type, String domainKey, String typeKey);

    void saveProperty(PropertyDef property, String domainKey, String typeKey, String propertyKey);

    void saveRelationship(RelationshipDef relationship, String domainKey, String typeKey, String relationshipKey);

    void saveFunction(FunctionDef function, String domainKey, String typeKey, String functionKey);

    void saveRule(RuleDef rule, String domainKey, String typeKey, String functionKey, String ruleKey);

    void saveSnapshot(TBoxSnapshot snapshot);

    void saveSnapshot(TBoxSnapshot snapshot, String buffer);

    void clearBuffer(String buffer);

    long countObjects(String buffer);

    void promoteBuffer(String fromBuffer, String toBuffer);

    Optional<DomainDef> findDomainByKey(String domainKey);

    Optional<DomainDef> findDomainByKey(String domainKey, String buffer);

    Optional<TypeDef> findTypeByPath(String typePath);

    Optional<PropertyDef> findPropertyByPath(String propertyPath);

    List<DomainDef> findAllDomains();

    List<DomainDef> findAllDomains(String buffer);

    List<TypeDef> findTypesByDomain(String domainKey);

    List<TypeDef> findTypesByDomain(String domainKey, String buffer);

    List<PropertyDef> findPropertiesByType(String domainKey, String typeKey);

    List<PropertyDef> findPropertiesByType(String domainKey, String typeKey, String buffer);

    List<RelationshipDef> findRelationshipsByType(String domainKey, String typeKey);

    List<RelationshipDef> findRelationshipsByType(String domainKey, String typeKey, String buffer);

    List<FunctionDef> findFunctionsByType(String domainKey, String typeKey);

    List<FunctionDef> findFunctionsByType(String domainKey, String typeKey, String buffer);

    List<RuleDef> findRulesByFunction(String domainKey, String typeKey, String functionKey);

    List<RuleDef> findRulesByFunction(String domainKey, String typeKey, String functionKey, String buffer);

    long countObjects();

    default String activeBuffer() {
        return "active";
    }

    default String stagingBuffer() {
        return "staging";
    }

    void clearAll();

    boolean exists(String objectPath);

    /**
     * 根据 object_path 通用查询节点。
     *
     * @param objectPath 对象路径
     * @return 节点对象（DomainDef/TypeDef/PropertyDef 等）
     */
    Optional<Object> findByObjectPath(String objectPath);

    /**
     * 查询指定对象的邻域关系（真实图查询）。
     *
     * @param objectPath  对象路径
     * @param direction   方向：OUTGOING/INCOMING/BOTH
     * @param relationTypes  关系类型过滤（null 或空表示不过滤）
     * @return 邻域边列表
     */
    List<GraphEdge> findNeighbors(String objectPath, Direction direction, List<String> relationTypes);

    List<GraphEdge> findNeighbors(String objectPath, Direction direction, List<String> relationTypes, String buffer);

    // ========== DELETE operations ==========

    void deleteDomain(String domainKey);

    void deleteType(String domainKey, String typeKey);

    void deleteProperty(String objectPath);

    void deleteRelationship(String objectPath);

    void deleteFunction(String domainKey, String typeKey, String functionKey);

    void deleteRule(String objectPath);
}
