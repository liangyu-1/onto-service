package com.onto.oaas.repository.neo4j;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxIndexRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Result;
import org.neo4j.driver.Session;
import org.neo4j.driver.types.Node;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Repository;

/**
 * Neo4j 向量索引实现的本体检索仓库（双缓冲支持）。
 *
 * <p>利用 Neo4j 5.x 原生支持的向量索引（HNSW）实现 ANN 检索，
 * 同时支持全文索引（BM25）关键词检索。</p>
 *
 * <p>通过 buffer 属性区分 active/staging 数据，全量同步时写入 staging，
 * 完成后切换，保证同步期间查询不中断。</p>
 */
@Slf4j
@Repository
@Primary
public class Neo4jTBoxIndexRepository implements TBoxIndexRepository {

    private final Driver driver;
    private final ObjectMapper objectMapper;

    private static final String NODE_LABEL = "TBoxIndex";
    private static final String VECTOR_INDEX_NAME = "tbox_embedding";
    private static final String FULLTEXT_INDEX_NAME = "tbox_fulltext";
    private static final int EMBEDDING_DIMENSION = 1024;
    private static final int SCHEMA_INIT_MAX_RETRIES = 10;
    private static final long SCHEMA_INIT_RETRY_DELAY_MS = 2000;

    private volatile boolean schemaInitialized = false;

    @Autowired
    public Neo4jTBoxIndexRepository(Driver driver, ObjectMapper objectMapper) {
        this.driver = driver;
        this.objectMapper = objectMapper;
    }

    /**
     * 在 Spring 上下文启动完成后初始化 Neo4j schema。
     * 带重试机制，防止 Neo4j 启动初期未完全 ready。
     */
    @PostConstruct
    public void initSchema() {
        for (int attempt = 1; attempt <= SCHEMA_INIT_MAX_RETRIES; attempt++) {
            try {
                initializeSchema();
                schemaInitialized = true;
                log.info("Neo4j TBox index schema initialized successfully");
                return;
            } catch (Exception e) {
                log.warn("[SchemaInit] Attempt {}/{} failed: {}", attempt, SCHEMA_INIT_MAX_RETRIES, e.getMessage());
                if (attempt < SCHEMA_INIT_MAX_RETRIES) {
                    try {
                        Thread.sleep(SCHEMA_INIT_RETRY_DELAY_MS);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
        log.error("[SchemaInit] Failed to initialize Neo4j schema after {} retries", SCHEMA_INIT_MAX_RETRIES);
    }

    public boolean isSchemaInitialized() {
        return schemaInitialized;
    }

    /**
     * 初始化 Neo4j schema：创建向量索引和全文索引。
     */
    private void initializeSchema() {
        try (Session session = driver.session()) {
            // 创建唯一约束（object_path + buffer 联合唯一）
            session.run("""
                CREATE CONSTRAINT tbox_index_object_path_buffer IF NOT EXISTS
                FOR (n:TBoxIndex) REQUIRE (n.object_path, n.buffer) IS UNIQUE
                """);

            // 创建向量索引（HNSW）- Neo4j 5.11+ 支持
            String vectorCypher = String.format(
                "CREATE VECTOR INDEX %s IF NOT EXISTS FOR (n:%s) ON (n.embedding) " +
                "OPTIONS {indexConfig: {`vector.dimensions`: %d, `vector.similarity_function`: 'cosine'}}",
                VECTOR_INDEX_NAME, NODE_LABEL, EMBEDDING_DIMENSION);
            session.run(vectorCypher);

            // 创建全文索引（用于 BM25 关键词检索）- Neo4j 5.x 语法
            session.run("""
                CREATE FULLTEXT INDEX tbox_fulltext IF NOT EXISTS
                FOR (n:TBoxIndex) ON EACH [n.name, n.description, n.keywords_text]
                """);

            log.info("Neo4j TBox index schema initialized: vector_index={}, fulltext_index={}",
                    VECTOR_INDEX_NAME, FULLTEXT_INDEX_NAME);
        }
    }

    @Override
    public void save(TBoxIndexDocument document) {
        save(document, activeBuffer());
    }

    public void save(TBoxIndexDocument document, String buffer) {
        if (document == null || document.getObjectPath() == null) {
            return;
        }
        String cypher = """
            MERGE (n:TBoxIndex {object_path: $objectPath, buffer: $buffer})
            SET n.object_type = $objectType,
                n.name = $name,
                n.description = $description,
                n.text_for_embedding = $textForEmbedding,
                n.keywords_text = $keywordsText,
                n.domain_key = $domainKey,
                n.type_key = $typeKey,
                n.function_key = $functionKey,
                n.rule_key = $ruleKey,
                n.rule_type = $ruleType,
                n.definition = $definition,
                n.binding_json = $bindingJson,
                n.updated_time = $updatedTime
            """;
        if (document.getEmbedding() != null && document.getEmbedding().length > 0) {
            cypher += " SET n.embedding = $embedding";
        }

        try (Session session = driver.session()) {
            var params = buildParams(document, buffer);
            session.run(cypher, params);
            log.debug("Saved TBoxIndex document: {} buffer={}", document.getObjectPath(), buffer);
        }
    }

    @Override
    public void saveBatch(List<TBoxIndexDocument> documents) {
        saveBatch(documents, activeBuffer());
    }

    @Override
    public void saveBatch(List<TBoxIndexDocument> documents, String buffer) {
        if (documents == null || documents.isEmpty()) {
            return;
        }
        String cypher = """
            UNWIND $records AS row
            MERGE (n:TBoxIndex {object_path: row.object_path, buffer: row.buffer})
            SET n.object_type = row.object_type,
                n.name = row.name,
                n.description = row.description,
                n.text_for_embedding = row.text_for_embedding,
                n.keywords_text = row.keywords_text,
                n.domain_key = row.domain_key,
                n.type_key = row.type_key,
                n.function_key = row.function_key,
                n.rule_key = row.rule_key,
                n.rule_type = row.rule_type,
                n.definition = row.definition,
                n.binding_json = row.binding_json,
                n.updated_time = row.updated_time,
                n.embedding = row.embedding
            """;

        List<Map<String, Object>> records = new ArrayList<>();
        for (TBoxIndexDocument doc : documents) {
            records.add(toRecordMap(doc, buffer));
        }

        try (Session session = driver.session()) {
            session.run(cypher, Map.of("records", records));
            log.info("Saved batch of {} TBoxIndex documents to Neo4j buffer={}", documents.size(), buffer);
        }
    }

    @Override
    public void deleteByObjectPath(String objectPath) {
        String cypher = "MATCH (n:TBoxIndex {object_path: $objectPath, buffer: $buffer}) DELETE n";
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
        }
    }

    @Override
    public List<TBoxIndexDocument> searchByKeyword(String query, List<TBoxObjectType> objectTypes, int limit) {
        if (query == null || query.isBlank()) {
            return searchAll(objectTypes, limit);
        }

        // 优先使用全文索引（BM25），然后过滤 active buffer
        String cypher = """
            CALL db.index.fulltext.queryNodes($fulltextIndex, $query)
            YIELD node, score
            WHERE node IS NOT NULL AND node.buffer = $buffer
            """;
        if (objectTypes != null && !objectTypes.isEmpty()) {
            cypher += " AND node.object_type IN $objectTypes";
        }
        cypher += " RETURN node AS n, score ORDER BY score DESC LIMIT $limit";

        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("fulltextIndex", FULLTEXT_INDEX_NAME);
            params.put("query", query);
            params.put("buffer", activeBuffer());
            params.put("limit", limit > 0 ? limit : 100);
            if (objectTypes != null && !objectTypes.isEmpty()) {
                params.put("objectTypes", objectTypes.stream().map(TBoxObjectType::name).toList());
            }

            Result result = session.run(cypher, params);
            return mapResults(result);
        } catch (Exception e) {
            log.warn("Fulltext search failed, falling back to CONTAINS: {}", e.getMessage());
            return searchByKeywordFallback(query, objectTypes, limit);
        }
    }

    private List<TBoxIndexDocument> searchByKeywordFallback(String query, List<TBoxObjectType> objectTypes, int limit) {
        String lowerQuery = query.toLowerCase();
        String cypher = """
            MATCH (n:TBoxIndex)
            WHERE n.buffer = $buffer
              AND (toLower(n.name) CONTAINS $query OR toLower(n.description) CONTAINS $query
                   OR toLower(n.keywords_text) CONTAINS $query)
            """;
        if (objectTypes != null && !objectTypes.isEmpty()) {
            cypher += " AND n.object_type IN $objectTypes";
        }
        cypher += " RETURN n LIMIT $limit";

        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("buffer", activeBuffer());
            params.put("query", lowerQuery);
            params.put("limit", limit > 0 ? limit : 100);
            if (objectTypes != null && !objectTypes.isEmpty()) {
                params.put("objectTypes", objectTypes.stream().map(TBoxObjectType::name).toList());
            }
            Result result = session.run(cypher, params);
            return mapResults(result);
        }
    }

    /**
     * 向量相似度搜索（ANN via HNSW），只查 active buffer。
     */
    public List<TBoxIndexDocument> searchByVector(float[] queryEmbedding, List<TBoxObjectType> objectTypes, int topK) {
        if (queryEmbedding == null || queryEmbedding.length == 0) {
            return List.of();
        }

        // 向量索引不支持属性过滤，先查向量再过滤 buffer
        String cypher = """
            CALL db.index.vector.queryNodes($vectorIndex, $k, $embedding)
            YIELD node, score
            WHERE node IS NOT NULL AND node.buffer = $buffer
            """;
        if (objectTypes != null && !objectTypes.isEmpty()) {
            cypher += " AND node.object_type IN $objectTypes";
        }
        cypher += " RETURN node AS n, score ORDER BY score DESC";

        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("vectorIndex", VECTOR_INDEX_NAME);
            params.put("k", topK > 0 ? topK : 10);
            params.put("embedding", toDoubleList(queryEmbedding));
            params.put("buffer", activeBuffer());
            if (objectTypes != null && !objectTypes.isEmpty()) {
                params.put("objectTypes", objectTypes.stream().map(TBoxObjectType::name).toList());
            }

            Result result = session.run(cypher, params);
            return mapResults(result);
        }
    }

    /**
     * 混合检索：BM25 + 向量 ANN 融合，只查 active buffer。
     */
    public List<TBoxIndexDocument> hybridSearch(String query, float[] queryEmbedding,
                                                 List<TBoxObjectType> objectTypes, int topK) {
        List<TBoxIndexDocument> keywordDocs = searchByKeyword(query, objectTypes, topK * 3);
        List<TBoxIndexDocument> vectorDocs = List.of();
        try {
            vectorDocs = searchByVector(queryEmbedding, objectTypes, topK * 3);
        } catch (Exception e) {
            log.warn("Vector search failed, using keyword only: {}", e.getMessage());
        }

        // RRF (Reciprocal Rank Fusion)
        Map<String, Double> rrfScores = new java.util.HashMap<>();
        final double k = 60.0;

        for (int i = 0; i < keywordDocs.size(); i++) {
            String path = keywordDocs.get(i).getObjectPath();
            rrfScores.merge(path, 1.0 / (k + i + 1), Double::sum);
        }
        for (int i = 0; i < vectorDocs.size(); i++) {
            String path = vectorDocs.get(i).getObjectPath();
            rrfScores.merge(path, 1.0 / (k + i + 1), Double::sum);
        }

        return rrfScores.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(topK)
                .map(e -> findByObjectPath(e.getKey()).orElse(null))
                .filter(doc -> doc != null)
                .toList();
    }

    @Override
    public Optional<TBoxIndexDocument> findByObjectPath(String objectPath) {
        String cypher = "MATCH (n:TBoxIndex {object_path: $objectPath, buffer: $buffer}) RETURN n";
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("objectPath", objectPath, "buffer", activeBuffer()));
            if (result.hasNext()) {
                Node node = result.next().get("n").asNode();
                return Optional.of(mapNodeToDocument(node));
            }
        }
        return Optional.empty();
    }

    @Override
    public List<TBoxIndexDocument> exactMatchByPath(String objectPath) {
        Optional<TBoxIndexDocument> doc = findByObjectPath(objectPath);
        return doc.map(List::of).orElseGet(List::of);
    }

    @Override
    public List<TBoxIndexDocument> searchByDomain(String domainKey) {
        String cypher = """
            MATCH (n:TBoxIndex {domain_key: $domainKey, buffer: $buffer})
            RETURN n
            """;
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("domainKey", domainKey, "buffer", activeBuffer()));
            return mapResults(result);
        }
    }

    @Override
    public void rebuildIndex() {
        clearBuffer(activeBuffer());
    }

    @Override
    public void clearBuffer(String buffer) {
        String cypher = "MATCH (n:TBoxIndex {buffer: $buffer}) DETACH DELETE n";
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("buffer", buffer));
            log.info("Cleared TBox index buffer: {}", buffer);
        }
    }

    @Override
    public void promoteBuffer(String fromBuffer, String toBuffer) {
        // 1. 先删除目标 buffer 的旧数据
        clearBuffer(toBuffer);
        // 2. 将源 buffer 的数据改目标 buffer
        String cypher = """
            MATCH (n:TBoxIndex {buffer: $fromBuffer})
            SET n.buffer = $toBuffer
            """;
        try (Session session = driver.session()) {
            session.run(cypher, Map.of("fromBuffer", fromBuffer, "toBuffer", toBuffer));
            log.info("Promoted TBox index buffer: {} -> {}", fromBuffer, toBuffer);
        }
    }

    @Override
    public long countByBuffer(String buffer) {
        String cypher = "MATCH (n:TBoxIndex {buffer: $buffer}) RETURN count(n) AS cnt";
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Map.of("buffer", buffer));
            if (result.hasNext()) {
                return result.next().get("cnt").asLong();
            }
        }
        return 0L;
    }

    // ========== 内部辅助方法 ==========

    private List<TBoxIndexDocument> searchAll(List<TBoxObjectType> objectTypes, int limit) {
        String cypher = "MATCH (n:TBoxIndex {buffer: $buffer})";
        if (objectTypes != null && !objectTypes.isEmpty()) {
            cypher += " WHERE n.object_type IN $objectTypes";
        }
        cypher += " RETURN n LIMIT $limit";
        try (Session session = driver.session()) {
            var params = new java.util.HashMap<String, Object>();
            params.put("buffer", activeBuffer());
            params.put("limit", limit > 0 ? limit : 100);
            if (objectTypes != null && !objectTypes.isEmpty()) {
                params.put("objectTypes", objectTypes.stream().map(TBoxObjectType::name).toList());
            }
            Result result = session.run(cypher, params);
            return mapResults(result);
        }
    }

    private List<TBoxIndexDocument> mapResults(Result result) {
        List<TBoxIndexDocument> docs = new ArrayList<>();
        while (result.hasNext()) {
            Record record = result.next();
            org.neo4j.driver.Value nodeValue = record.get("n");
            if (nodeValue == null || nodeValue.isNull()) {
                continue;
            }
            Node node = nodeValue.asNode();
            docs.add(mapNodeToDocument(node));
        }
        return docs;
    }

    private TBoxIndexDocument mapNodeToDocument(Node node) {
        String keywordsText = node.get("keywords_text").asString(null);
        List<String> keywords = keywordsText != null ? List.of(keywordsText.split("\\s+")) : List.of();

        float[] embedding = null;
        if (node.containsKey("embedding")) {
            org.neo4j.driver.Value embValue = node.get("embedding");
            if (embValue != null && !embValue.isNull()) {
                List<Double> embList = embValue.asList(org.neo4j.driver.Value::asDouble);
                if (embList != null) {
                    embedding = new float[embList.size()];
                    for (int i = 0; i < embList.size(); i++) {
                        embedding[i] = embList.get(i).floatValue();
                    }
                }
            }
        }

        String bindingJson = node.get("binding_json").asString(null);
        com.onto.oaas.model.Binding binding = fromJson(bindingJson, com.onto.oaas.model.Binding.class);

        String updatedTimeStr = node.get("updated_time").asString(null);
        Instant updatedTime = updatedTimeStr != null ? Instant.parse(updatedTimeStr) : null;

        return TBoxIndexDocument.builder()
                .objectPath(node.get("object_path").asString(null))
                .objectType(parseEnum(node.get("object_type").asString(null), TBoxObjectType.class))
                .name(node.get("name").asString(null))
                .description(node.get("description").asString(null))
                .textForEmbedding(node.get("text_for_embedding").asString(null))
                .keywords(keywords)
                .domainKey(node.get("domain_key").asString(null))
                .typeKey(node.get("type_key").asString(null))
                .functionKey(node.get("function_key").asString(null))
                .ruleKey(node.get("rule_key").asString(null))
                .ruleType(node.get("rule_type").asString(null))
                .definition(node.get("definition").asString(null))
                .binding(binding)
                .updatedTime(updatedTime)
                .embedding(embedding)
                .build();
    }

    private Map<String, Object> buildParams(TBoxIndexDocument doc, String buffer) {
        var params = new java.util.HashMap<String, Object>();
        params.put("objectPath", doc.getObjectPath());
        params.put("buffer", buffer);
        params.put("objectType", doc.getObjectType() != null ? doc.getObjectType().name() : null);
        params.put("name", doc.getName());
        params.put("description", doc.getDescription());
        params.put("textForEmbedding", doc.getTextForEmbedding());
        params.put("keywordsText", doc.getKeywords() != null ? String.join(" ", doc.getKeywords()) : null);
        params.put("domainKey", doc.getDomainKey());
        params.put("typeKey", doc.getTypeKey());
        params.put("functionKey", doc.getFunctionKey());
        params.put("ruleKey", doc.getRuleKey());
        params.put("ruleType", doc.getRuleType());
        params.put("definition", doc.getDefinition());
        params.put("bindingJson", toJson(doc.getBinding()));
        params.put("updatedTime", doc.getUpdatedTime() != null ? doc.getUpdatedTime().toString() : Instant.now().toString());
        if (doc.getEmbedding() != null && doc.getEmbedding().length > 0) {
            params.put("embedding", toDoubleList(doc.getEmbedding()));
        }
        return params;
    }

    private Map<String, Object> toRecordMap(TBoxIndexDocument doc, String buffer) {
        var map = new java.util.HashMap<String, Object>();
        map.put("object_path", doc.getObjectPath());
        map.put("buffer", buffer);
        map.put("object_type", doc.getObjectType() != null ? doc.getObjectType().name() : null);
        map.put("name", doc.getName());
        map.put("description", doc.getDescription());
        map.put("text_for_embedding", doc.getTextForEmbedding());
        map.put("keywords_text", doc.getKeywords() != null ? String.join(" ", doc.getKeywords()) : null);
        map.put("domain_key", doc.getDomainKey());
        map.put("type_key", doc.getTypeKey());
        map.put("function_key", doc.getFunctionKey());
        map.put("rule_key", doc.getRuleKey());
        map.put("rule_type", doc.getRuleType());
        map.put("definition", doc.getDefinition());
        map.put("binding_json", toJson(doc.getBinding()));
        map.put("updated_time", doc.getUpdatedTime() != null ? doc.getUpdatedTime().toString() : Instant.now().toString());
        map.put("embedding", doc.getEmbedding() != null ? toDoubleList(doc.getEmbedding()) : null);
        return map;
    }

    private List<Double> toDoubleList(float[] arr) {
        List<Double> list = new ArrayList<>(arr.length);
        for (float v : arr) {
            list.add((double) v);
        }
        return list;
    }

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
}
