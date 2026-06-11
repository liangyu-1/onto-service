package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.InMemoryTBoxIndexRepository;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.repository.neo4j.Neo4jTBoxIndexRepository;
import com.onto.oaas.service.embedding.EmbeddingClient;
import com.onto.oaas.service.embedding.EmbeddingServiceException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 多路召回 Agent。
 *
 * <p>职责：执行多路召回（精确匹配 + 关键词召回 + 向量召回 + 混合检索），合并候选结果。</p>
 * <p>当 Neo4jTBoxIndexRepository 可用时，优先使用 HybridSearchAgent 的混合检索（BM25 + ANN）；
 * 否则回退到内存索引的三路召回。</p>
 * <p>输入：{@link AgentMessageType#RECALL_REQUEST}</p>
 * <p>输出：{@link AgentMessageType#RECALL_RESULT}</p>
 */
@Slf4j
@Component
public class RecallAgent extends AbstractAgent {

    private final TBoxIndexRepository indexRepository;
    private final EmbeddingClient embeddingClient;
    private final boolean hybridEnabled;

    public RecallAgent(AgentBus agentBus, TBoxIndexRepository indexRepository,
                       EmbeddingClient embeddingClient) {
        super(agentBus);
        this.indexRepository = indexRepository;
        this.embeddingClient = embeddingClient;
        this.hybridEnabled = indexRepository instanceof Neo4jTBoxIndexRepository;
        subscribeTo(AgentMessageType.RECALL_REQUEST);
    }

    @Override
    public String getName() {
        return "RecallAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        String query = message.getPayload("query", String.class);
        int topK = message.getPayload("topK", Integer.class);
        List<TBoxObjectType> objectTypes = message.getPayload("objectTypes", List.class);
        Boolean enableKeyword = message.getPayload("enableKeywordRecall", Boolean.class);
        Boolean enableVector = message.getPayload("enableVectorRecall", Boolean.class);

        if (query == null) {
            query = "";
        }
        if (enableKeyword == null) {
            enableKeyword = true;
        }
        if (enableVector == null) {
            enableVector = true;
        }

        log.info("[{}] Recalling for query='{}', topK={}, keyword={}, vector={}, correlationId={}",
                getName(), query, topK, enableKeyword, enableVector, message.getCorrelationId());

        Map<String, ScoredCandidate> candidateMap = new HashMap<>();

        // 优先使用混合检索（Neo4j BM25 + ANN）
        if (hybridEnabled && indexRepository instanceof Neo4jTBoxIndexRepository neo4jRepo) {
            hybridRecall(neo4jRepo, query, objectTypes, topK, enableKeyword, enableVector, candidateMap);
        } else {
            // 回退到三路召回（内存模式）
            legacyRecall(query, objectTypes, topK, enableKeyword, enableVector, candidateMap);
        }

        List<ScoredCandidate> candidates = new ArrayList<>(candidateMap.values());
        log.info("[{}] Recalled {} candidates, correlationId={}", getName(), candidates.size(), message.getCorrelationId());

        AgentMessage reply = message.reply(AgentMessageType.RECALL_RESULT)
                .putPayload("candidates", candidates);
        publish(reply);
    }

    private boolean isTypeAllowed(TBoxIndexDocument doc, List<TBoxObjectType> objectTypes) {
        if (objectTypes == null || objectTypes.isEmpty()) {
            return true;
        }
        return objectTypes.contains(doc.getObjectType());
    }

    private double computeKeywordScore(TBoxIndexDocument doc, String query) {
        String lowerQuery = query.toLowerCase();
        String name = doc.getName() != null ? doc.getName().toLowerCase() : "";
        String desc = doc.getDescription() != null ? doc.getDescription().toLowerCase() : "";
        if (name.equals(lowerQuery)) {
            return 1.0;
        }
        if (name.contains(lowerQuery)) {
            return 0.8;
        }
        if (desc.contains(lowerQuery)) {
            return 0.5;
        }
        return 0.3;
    }

    /**
     * 混合检索召回（Neo4j 模式）：BM25 + ANN + 精确匹配。
     */
    private void hybridRecall(Neo4jTBoxIndexRepository neo4jRepo, String query,
                               List<TBoxObjectType> objectTypes, int topK,
                               boolean enableKeyword, boolean enableVector,
                               Map<String, ScoredCandidate> candidateMap) {
        // 1. 精确匹配
        List<TBoxIndexDocument> exactMatches = neo4jRepo.exactMatchByPath(query);
        for (TBoxIndexDocument doc : exactMatches) {
            candidateMap.merge(doc.getObjectPath(),
                    new ScoredCandidate(doc, 1.0, 0.0, 0.0, List.of("exactMatch")),
                    ScoredCandidate::merge);
        }

        // 2. 混合检索（BM25 + ANN RRF）
        if ((enableKeyword || enableVector) && !query.isBlank()) {
            try {
                float[] queryEmbedding = enableVector ? embeddingClient.embed(query) : new float[0];
                List<TBoxIndexDocument> hybridDocs = neo4jRepo.hybridSearch(
                        query, queryEmbedding.length > 0 ? queryEmbedding : null, objectTypes, topK * 3);
                for (TBoxIndexDocument doc : hybridDocs) {
                    candidateMap.merge(doc.getObjectPath(),
                            new ScoredCandidate(doc, 0.0, 0.5, 0.5, List.of("hybridRecall")),
                            ScoredCandidate::merge);
                }
            } catch (Exception e) {
                log.warn("[{}] Hybrid recall failed: {}", getName(), e.getMessage());
            }
        }
    }

    /**
     * 传统三路召回（内存模式回退）。
     */
    private void legacyRecall(String query, List<TBoxObjectType> objectTypes, int topK,
                               boolean enableKeyword, boolean enableVector,
                               Map<String, ScoredCandidate> candidateMap) {
        // 1. 精确匹配
        List<TBoxIndexDocument> exactMatches = indexRepository.exactMatchByPath(query);
        for (TBoxIndexDocument doc : exactMatches) {
            if (isTypeAllowed(doc, objectTypes)) {
                candidateMap.merge(doc.getObjectPath(),
                        new ScoredCandidate(doc, 1.0, 0.0, 0.0, List.of("exactMatch")),
                        ScoredCandidate::merge);
            }
        }

        // 2. 关键词召回
        if (enableKeyword) {
            List<TBoxIndexDocument> keywordDocs = indexRepository.searchByKeyword(query, objectTypes, topK * 3);
            for (TBoxIndexDocument doc : keywordDocs) {
                double kwScore = computeKeywordScore(doc, query);
                candidateMap.merge(doc.getObjectPath(),
                        new ScoredCandidate(doc, 0.0, kwScore, 0.0, List.of("keywordRecall")),
                        ScoredCandidate::merge);
            }
        }

        // 3. 向量召回
        if (enableVector) {
            List<TBoxIndexDocument> vectorDocs = vectorRecall(query, objectTypes, topK * 5);
            for (TBoxIndexDocument doc : vectorDocs) {
                candidateMap.merge(doc.getObjectPath(),
                        new ScoredCandidate(doc, 0.0, 0.0, 1.0, List.of("vectorRecall")),
                        ScoredCandidate::merge);
            }
        }
    }

    /**
     * 向量召回（内存模式）。
     */
    private List<TBoxIndexDocument> vectorRecall(String query, List<TBoxObjectType> objectTypes, int topK) {
        try {
            float[] queryEmbedding = embeddingClient.embed(query);
            if (queryEmbedding.length == 0) {
                log.warn("Embedding service returned empty vector for query: {}", query);
                return List.of();
            }
            if (indexRepository instanceof InMemoryTBoxIndexRepository memRepo) {
                return memRepo.searchByVector(queryEmbedding, objectTypes, topK);
            }
            log.warn("Vector recall not supported for repository type: {}", indexRepository.getClass().getName());
            return List.of();
        } catch (EmbeddingServiceException e) {
            log.error("Vector recall failed due to embedding service error: {}", e.getMessage());
            return List.of();
        }
    }

    /**
     * 召回阶段的候选结果，包含多路分数。
     */
    public static class ScoredCandidate {
        public final TBoxIndexDocument document;
        public double exactScore;
        public double keywordScore;
        public double vectorScore;
        public final List<String> channels;

        public ScoredCandidate(TBoxIndexDocument document, double exactScore, double keywordScore, double vectorScore, List<String> channels) {
            this.document = document;
            this.exactScore = exactScore;
            this.keywordScore = keywordScore;
            this.vectorScore = vectorScore;
            this.channels = new ArrayList<>(channels);
        }

        public ScoredCandidate merge(ScoredCandidate other) {
            this.exactScore = Math.max(this.exactScore, other.exactScore);
            this.keywordScore = Math.max(this.keywordScore, other.keywordScore);
            this.vectorScore = Math.max(this.vectorScore, other.vectorScore);
            for (String ch : other.channels) {
                if (!this.channels.contains(ch)) {
                    this.channels.add(ch);
                }
            }
            return this;
        }
    }
}
