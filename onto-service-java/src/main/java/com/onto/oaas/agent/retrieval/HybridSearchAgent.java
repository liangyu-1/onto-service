package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.neo4j.Neo4jTBoxIndexRepository;
import com.onto.oaas.service.embedding.EmbeddingClient;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 混合检索 Agent。
 *
 * <p>职责：执行 Neo4j 混合检索（向量 ANN + 关键词 BM25 + 图结构过滤），
 * 使用 RRF (Reciprocal Rank Fusion) 融合多路召回结果。</p>
 *
 * <p>输入：{@link AgentMessageType#HYBRID_SEARCH_REQUEST}</p>
 * <p>输出：{@link AgentMessageType#HYBRID_SEARCH_RESULT}</p>
 */
@Slf4j
@Component
public class HybridSearchAgent extends AbstractAgent {

    private final Neo4jTBoxIndexRepository indexRepository;
    private final EmbeddingClient embeddingClient;

    public HybridSearchAgent(AgentBus agentBus, Neo4jTBoxIndexRepository indexRepository,
                             EmbeddingClient embeddingClient) {
        super(agentBus);
        this.indexRepository = indexRepository;
        this.embeddingClient = embeddingClient;
        subscribeTo(AgentMessageType.HYBRID_SEARCH_REQUEST);
    }

    @Override
    public String getName() {
        return "HybridSearchAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        String query = message.getPayload("query", String.class);
        int topK = message.getPayload("topK", Integer.class);
        List<TBoxObjectType> objectTypes = message.getPayload("objectTypes", List.class);
        boolean enableKeyword = message.getPayload("enableKeyword", Boolean.class);
        Boolean enableVector = message.getPayload("enableVector", Boolean.class);

        if (query == null) {
            query = "";
        }
        if (enableKeyword == false && Boolean.FALSE.equals(enableVector)) {
            log.warn("[{}] Both keyword and vector search disabled, returning empty", getName());
            publish(message.reply(AgentMessageType.HYBRID_SEARCH_RESULT)
                    .putPayload("documents", List.of()));
            return;
        }

        log.info("[{}] Hybrid search: query='{}', topK={}, keyword={}, vector={}, correlationId={}",
                getName(), query, topK, enableKeyword, enableVector, message.getCorrelationId());

        List<TBoxIndexDocument> results = hybridSearch(query, objectTypes, topK, enableKeyword, enableVector);

        log.info("[{}] Hybrid search returned {} results, correlationId={}",
                getName(), results.size(), message.getCorrelationId());

        publish(message.reply(AgentMessageType.HYBRID_SEARCH_RESULT)
                .putPayload("documents", results));
    }

    /**
     * 混合检索：关键词 BM25 + 向量 ANN，RRF 融合。
     */
    private List<TBoxIndexDocument> hybridSearch(String query, List<TBoxObjectType> objectTypes,
                                                  int topK, boolean enableKeyword, Boolean enableVector) {
        // 默认都启用
        if (enableVector == null) {
            enableVector = true;
        }

        List<TBoxIndexDocument> keywordDocs = List.of();
        List<TBoxIndexDocument> vectorDocs = List.of();

        // 1. 关键词召回（BM25 via Neo4j 全文索引）
        if (enableKeyword && !query.isBlank()) {
            try {
                keywordDocs = indexRepository.searchByKeyword(query, objectTypes, topK * 3);
            } catch (Exception e) {
                log.warn("[{}] Keyword search failed: {}", getName(), e.getMessage());
            }
        }

        // 2. 向量召回（ANN via HNSW）
        if (enableVector) {
            try {
                float[] queryEmbedding = embeddingClient.embed(query);
                if (queryEmbedding.length > 0) {
                    vectorDocs = indexRepository.searchByVector(queryEmbedding, objectTypes, topK * 3);
                }
            } catch (Exception e) {
                log.warn("[{}] Vector search failed: {}", getName(), e.getMessage());
            }
        }

        // 3. RRF 融合
        return reciprocalRankFusion(keywordDocs, vectorDocs, topK);
    }

    /**
     * RRF (Reciprocal Rank Fusion)：融合多路召回结果。
     */
    private List<TBoxIndexDocument> reciprocalRankFusion(
            List<TBoxIndexDocument> keywordDocs,
            List<TBoxIndexDocument> vectorDocs,
            int topK) {

        Map<String, Double> rrfScores = new HashMap<>();
        Map<String, TBoxIndexDocument> docMap = new HashMap<>();
        final double k = 60.0;

        for (int i = 0; i < keywordDocs.size(); i++) {
            String path = keywordDocs.get(i).getObjectPath();
            docMap.put(path, keywordDocs.get(i));
            rrfScores.merge(path, 1.0 / (k + i + 1), Double::sum);
        }

        for (int i = 0; i < vectorDocs.size(); i++) {
            String path = vectorDocs.get(i).getObjectPath();
            docMap.put(path, vectorDocs.get(i));
            rrfScores.merge(path, 1.0 / (k + i + 1), Double::sum);
        }

        return rrfScores.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(topK)
                .map(e -> docMap.get(e.getKey()))
                .toList();
    }
}
