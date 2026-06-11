package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.QueryIntentV2;
import com.onto.oaas.model.QueryIntentV2.StructureConstraint;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.ArrayList;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Result;
import org.neo4j.driver.Session;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 结构感知召回 Agent。
 *
 * <p>职责：基于 Neo4j 图结构执行语义召回，利用本体层级关系进行路径约束检索、
 * 关系推理检索和子图相似度匹配。这是本体系统独有的核心差异化能力。</p>
 *
 * <p>输入：{@link AgentMessageType#STRUCTURE_RECALL_REQUEST}</p>
 * <p>输出：{@link AgentMessageType#STRUCTURE_RECALL_RESULT}</p>
 */
@Slf4j
@Component
public class StructureAwareRecallAgent extends AbstractAgent {

    private final Driver driver;

    @Autowired
    public StructureAwareRecallAgent(AgentBus agentBus, Driver driver) {
        super(agentBus);
        this.driver = driver;
        subscribeTo(AgentMessageType.STRUCTURE_RECALL_REQUEST);
    }

    @Override
    public String getName() {
        return "StructureAwareRecallAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        QueryIntentV2 intent = message.getPayload("intent", QueryIntentV2.class);
        int topK = message.getPayload("topK", Integer.class);

        if (intent == null) {
            publish(message.reply(AgentMessageType.STRUCTURE_RECALL_RESULT)
                    .putPayload("documents", List.of()));
            return;
        }

        log.info("[{}] Structure-aware recall: intent={}, topK={}, correlationId={}",
                getName(), intent.getIntent(), topK, message.getCorrelationId());

        List<TBoxIndexDocument> results = structureRecall(intent, topK);

        log.info("[{}] Structure recall returned {} results, correlationId={}",
                getName(), results.size(), message.getCorrelationId());

        publish(message.reply(AgentMessageType.STRUCTURE_RECALL_RESULT)
                .putPayload("documents", results));
    }

    /**
     * 根据查询意图和结构约束执行图结构召回。
     */
    private List<TBoxIndexDocument> structureRecall(QueryIntentV2 intent, int topK) {
        List<TBoxIndexDocument> allResults = new ArrayList<>();

        switch (intent.getIntent()) {
            case "RULE_LOOKUP" -> {
                // "设备有哪些规则" → 从 Domain 出发找所有 Rule
                allResults.addAll(recallRulesByConstraints(intent.getConstraints(), topK));
            }
            case "PROPERTY_SEARCH" -> {
                // "设备有哪些属性" → 从 Type 出发找所有 Property
                allResults.addAll(recallPropertiesByConstraints(intent.getConstraints(), topK));
            }
            case "RELATIONSHIP_QUERY" -> {
                // "和故障相关的属性" → 通过 Relationship 找关联
                allResults.addAll(recallByRelationship(intent.getConstraints(), topK));
            }
            case "FUNCTION_QUERY" -> {
                allResults.addAll(recallFunctionsByConstraints(intent.getConstraints(), topK));
            }
            case "PATH_NAVIGATION" -> {
                // 路径导航：BFS 扩展
                allResults.addAll(recallByPathNavigation(intent.getConstraints(), topK));
            }
            default -> {
                // 通用：基于结构约束过滤
                allResults.addAll(recallByGenericConstraints(intent.getConstraints(), topK));
            }
        }

        // 去重
        return allResults.stream()
                .distinct()
                .limit(topK)
                .toList();
    }

    /**
     * 规则查找：根据约束从 Domain/Type 出发找 Rule。
     */
    private List<TBoxIndexDocument> recallRulesByConstraints(List<StructureConstraint> constraints, int topK) {
        StringBuilder cypher = new StringBuilder();
        cypher.append("MATCH (d:Domain)-[:HAS_TYPE]->(t:Type)-[:HAS_FUNCTION]->(f:Function)-[:HAS_RULE]->(r:Rule)");

        // 添加路径前缀约束
        List<String> domainPrefixes = extractPathPrefixValues(constraints);
        if (!domainPrefixes.isEmpty()) {
            cypher.append(" WHERE d.object_path IN $domainPrefixes");
        }
        cypher.append(" RETURN r.object_path as objectPath, r.name as name, r.description as description, 'RULE' as objectType");
        cypher.append(" LIMIT $topK");

        return executeStructureQuery(cypher.toString(), domainPrefixes, topK, TBoxObjectType.RULE);
    }

    /**
     * 属性查找：根据约束从 Type 出发找 Property。
     */
    private List<TBoxIndexDocument> recallPropertiesByConstraints(List<StructureConstraint> constraints, int topK) {
        StringBuilder cypher = new StringBuilder();
        cypher.append("MATCH (t:Type)-[:HAS_PROPERTY]->(p:Property)");

        List<String> typePrefixes = extractPathPrefixValues(constraints);
        if (!typePrefixes.isEmpty()) {
            cypher.append(" WHERE t.object_path IN $typePrefixes OR t.domain_key IN $typePrefixes");
        }
        cypher.append(" RETURN p.object_path as objectPath, p.name as name, p.description as description, 'PROPERTY' as objectType");
        cypher.append(" LIMIT $topK");

        return executeStructureQuery(cypher.toString(), typePrefixes, topK, TBoxObjectType.PROPERTY);
    }

    /**
     * 关系推理：通过 Relationship 找关联实体。
     */
    private List<TBoxIndexDocument> recallByRelationship(List<StructureConstraint> constraints, int topK) {
        // 找与指定关系关联的实体
        StringBuilder cypher = new StringBuilder();
        cypher.append("MATCH (t:Type)-[:HAS_RELATIONSHIP]->(r:Relationship)");

        List<String> prefixes = extractPathPrefixValues(constraints);
        if (!prefixes.isEmpty()) {
            cypher.append(" WHERE t.object_path IN $prefixes OR t.domain_key IN $prefixes");
        }
        cypher.append(" RETURN r.object_path as objectPath, r.name as name, r.description as description, 'RELATIONSHIP' as objectType");
        cypher.append(" LIMIT $topK");

        List<TBoxIndexDocument> rels = executeStructureQuery(cypher.toString(), prefixes, topK, TBoxObjectType.RELATIONSHIP);

        // 同时找关系指向的目标属性
        StringBuilder linkCypher = new StringBuilder();
        linkCypher.append("MATCH (r:Relationship)-[:LINK_TO]->(p:Property)");
        if (!prefixes.isEmpty()) {
            linkCypher.append(" WHERE r.object_path STARTS WITH $prefixPattern");
        }
        linkCypher.append(" RETURN p.object_path as objectPath, p.name as name, p.description as description, 'PROPERTY' as objectType");
        linkCypher.append(" LIMIT $topK");

        String prefixPattern = prefixes.isEmpty() ? "" : prefixes.get(0);
        List<TBoxIndexDocument> props = executeStructureQueryWithPattern(linkCypher.toString(), prefixPattern, topK, TBoxObjectType.PROPERTY);

        List<TBoxIndexDocument> combined = new ArrayList<>(rels);
        combined.addAll(props);
        return combined;
    }

    /**
     * 函数查找。
     */
    private List<TBoxIndexDocument> recallFunctionsByConstraints(List<StructureConstraint> constraints, int topK) {
        StringBuilder cypher = new StringBuilder();
        cypher.append("MATCH (t:Type)-[:HAS_FUNCTION]->(f:Function)");

        List<String> prefixes = extractPathPrefixValues(constraints);
        if (!prefixes.isEmpty()) {
            cypher.append(" WHERE t.object_path IN $prefixes");
        }
        cypher.append(" RETURN f.object_path as objectPath, f.name as name, f.description as description, 'FUNCTION' as objectType");
        cypher.append(" LIMIT $topK");

        return executeStructureQuery(cypher.toString(), prefixes, topK, TBoxObjectType.FUNCTION);
    }

    /**
     * 路径导航：BFS 扩展找邻居。
     */
    private List<TBoxIndexDocument> recallByPathNavigation(List<StructureConstraint> constraints, int topK) {
        List<String> startPaths = extractPathPrefixValues(constraints);
        if (startPaths.isEmpty()) {
            return List.of();
        }

        String cypher = """
            MATCH (start)
            WHERE start.object_path IN $startPaths
            MATCH (start)-[r]-(neighbor)
            WHERE neighbor:Domain OR neighbor:Type OR neighbor:Property OR neighbor:Relationship OR neighbor:Function OR neighbor:Rule
            RETURN neighbor.object_path as objectPath, neighbor.name as name, neighbor.description as description,
                   CASE
                     WHEN neighbor:Domain THEN 'DOMAIN'
                     WHEN neighbor:Type THEN 'TYPE'
                     WHEN neighbor:Property THEN 'PROPERTY'
                     WHEN neighbor:Relationship THEN 'RELATIONSHIP'
                     WHEN neighbor:Function THEN 'FUNCTION'
                     WHEN neighbor:Rule THEN 'RULE'
                     ELSE 'UNKNOWN'
                   END as objectType
            LIMIT $topK
            """;

        return executeStructureQuery(cypher, startPaths, topK, null);
    }

    /**
     * 通用结构约束召回。
     */
    private List<TBoxIndexDocument> recallByGenericConstraints(List<StructureConstraint> constraints, int topK) {
        if (constraints == null || constraints.isEmpty()) {
            return List.of();
        }

        // 按 TYPE_FILTER 约束过滤
        List<String> typeFilters = constraints.stream()
                .filter(c -> "TYPE_FILTER".equals(c.getType()))
                .map(StructureConstraint::getValue)
                .toList();

        if (typeFilters.isEmpty()) {
            return List.of();
        }

        // 动态构建 Cypher：根据类型过滤找对应节点
        List<TBoxIndexDocument> results = new ArrayList<>();
        for (String type : typeFilters) {
            String label = type; // DOMAIN, TYPE, PROPERTY, etc.
            String cypher = "MATCH (n:" + label + ") RETURN n.object_path as objectPath, n.name as name, n.description as description, $type as objectType LIMIT $topK";
            results.addAll(executeStructureQuery(cypher, List.of(), topK, TBoxObjectType.valueOf(type)));
        }
        return results;
    }

    // ========== 辅助方法 ==========

    private List<String> extractPathPrefixValues(List<StructureConstraint> constraints) {
        if (constraints == null) {
            return List.of();
        }
        return constraints.stream()
                .filter(c -> "PATH_PREFIX".equals(c.getType()))
                .map(StructureConstraint::getValue)
                .distinct()
                .toList();
    }

    private List<TBoxIndexDocument> executeStructureQuery(String cypher, List<String> pathValues, int topK, TBoxObjectType defaultType) {
        List<TBoxIndexDocument> docs = new ArrayList<>();
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            if (!pathValues.isEmpty()) {
                params.put("domainPrefixes", pathValues);
                params.put("typePrefixes", pathValues);
                params.put("prefixes", pathValues);
                params.put("startPaths", pathValues);
            }
            params.put("topK", topK);
            if (defaultType != null) {
                params.put("type", defaultType.name());
            }

            Result result = session.run(cypher, params);
            while (result.hasNext()) {
                Record record = result.next();
                String objectPath = record.get("objectPath").asString(null);
                String name = record.get("name").asString(null);
                String description = record.get("description").asString(null);
                String typeStr = record.get("objectType").asString(null);

                if (objectPath != null) {
                    TBoxObjectType objectType = defaultType;
                    if (typeStr != null) {
                        try {
                            objectType = TBoxObjectType.valueOf(typeStr);
                        } catch (IllegalArgumentException ignored) {}
                    }
                    docs.add(TBoxIndexDocument.builder()
                            .objectPath(objectPath)
                            .objectType(objectType)
                            .name(name)
                            .description(description)
                            .build());
                }
            }
        } catch (Exception e) {
            log.warn("[{}] Structure query failed: {}", getName(), e.getMessage());
        }
        return docs;
    }

    private List<TBoxIndexDocument> executeStructureQueryWithPattern(String cypher, String prefixPattern, int topK, TBoxObjectType defaultType) {
        List<TBoxIndexDocument> docs = new ArrayList<>();
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("prefixPattern", prefixPattern);
            params.put("topK", topK);
            params.put("type", defaultType.name());

            Result result = session.run(cypher, params);
            while (result.hasNext()) {
                Record record = result.next();
                String objectPath = record.get("objectPath").asString(null);
                String name = record.get("name").asString(null);
                String description = record.get("description").asString(null);
                String typeStr = record.get("objectType").asString(null);

                if (objectPath != null) {
                    TBoxObjectType objectType = defaultType;
                    if (typeStr != null) {
                        try {
                            objectType = TBoxObjectType.valueOf(typeStr);
                        } catch (IllegalArgumentException ignored) {}
                    }
                    docs.add(TBoxIndexDocument.builder()
                            .objectPath(objectPath)
                            .objectType(objectType)
                            .name(name)
                            .description(description)
                            .build());
                }
            }
        } catch (Exception e) {
            log.warn("[{}] Structure query with pattern failed: {}", getName(), e.getMessage());
        }
        return docs;
    }
}
