package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.service.ranking.VLLMRerankClient;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 语义对象重排 Agent。
 *
 * <p>职责：接收召回候选列表，基于 vLLM Reranker 模型进行重排序。</p>
 * <p>优先调用 vLLM Reranker 服务，不可用时回退到固定权重融合。</p>
 * <p>输入：{@link AgentMessageType#RERANK_REQUEST}</p>
 * <p>输出：{@link AgentMessageType#RERANK_RESULT}</p>
 */
@Slf4j
@Component
public class RerankAgent extends AbstractAgent {

    // 固定权重配置（reranker 不可用时的回退）
    private static final double W_EXACT = 0.3;
    private static final double W_KEYWORD = 0.2;
    private static final double W_VECTOR = 0.2;
    private static final double W_STRUCTURE = 0.2;
    private static final double W_TYPE_MATCH = 0.1;

    private final VLLMRerankClient rerankClient;
    private boolean rerankAvailable = true;

    public RerankAgent(AgentBus agentBus, VLLMRerankClient rerankClient) {
        super(agentBus);
        this.rerankClient = rerankClient;
        subscribeTo(AgentMessageType.RERANK_REQUEST);
    }

    @Override
    public String getName() {
        return "RerankAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        String query = message.getPayload("query", String.class);
        List<RecallAgent.ScoredCandidate> candidates = message.getPayload("candidates", List.class);
        int topK = message.getPayload("topK", Integer.class);
        List<TBoxObjectType> objectTypes = message.getPayload("objectTypes", List.class);
        List<TBoxIndexDocument> structureDocs = message.getPayload("structureDocuments", List.class);
        String queryIntent = message.getPayload("queryIntent", String.class);

        if (candidates == null || candidates.isEmpty()) {
            log.info("[{}] No candidates to rerank, correlationId={}", getName(), message.getCorrelationId());
            publish(message.reply(AgentMessageType.RERANK_RESULT)
                    .putPayload("rankedCandidates", List.of()));
            return;
        }

        log.info("[{}] Reranking {} candidates, structureDocs={}, topK={}, correlationId={}",
                getName(), candidates.size(),
                structureDocs != null ? structureDocs.size() : 0,
                topK, message.getCorrelationId());

        List<RankedCandidate> ranked = rerank(query, candidates, objectTypes, structureDocs, queryIntent, topK);

        log.info("[{}] Reranked to {} candidates, correlationId={}",
                getName(), ranked.size(), message.getCorrelationId());

        publish(message.reply(AgentMessageType.RERANK_RESULT)
                .putPayload("rankedCandidates", ranked));
    }

    /**
     * 核心重排逻辑：优先使用 vLLM Reranker，不可用时回退到固定权重融合。
     */
    public List<RankedCandidate> rerank(String query,
                                         List<RecallAgent.ScoredCandidate> candidates,
                                         List<TBoxObjectType> objectTypes,
                                         List<TBoxIndexDocument> structureDocs,
                                         String queryIntent, int topK) {
        java.util.Set<String> structurePaths = structureDocs != null
                ? structureDocs.stream().map(TBoxIndexDocument::getObjectPath).collect(java.util.stream.Collectors.toSet())
                : java.util.Set.of();

        // 尝试使用 vLLM Reranker
        if (rerankAvailable && query != null && !query.isBlank()) {
            List<RankedCandidate> rerankResult = rerankWithVLLM(query, candidates, topK);
            if (rerankResult != null) {
                // 结构匹配和类型匹配加分
                for (RankedCandidate rc : rerankResult) {
                    double boost = 0.0;
                    if (structurePaths.contains(rc.document.getObjectPath())) {
                        boost += 0.05;
                    }
                    boost += computeTypeMatchScore(rc.document, objectTypes) * 0.05;
                    rc.score = Math.min(rc.score + boost, 1.0);
                }
                rerankResult.sort(Comparator.comparingDouble((RankedCandidate c) -> c.score).reversed());
                return rerankResult;
            }
            rerankAvailable = false;
        }

        // 回退到固定权重融合
        return rerankWithFixedWeights(candidates, objectTypes, structurePaths, queryIntent, topK);
    }

    /**
     * 使用 vLLM Reranker 重排序。
     */
    private List<RankedCandidate> rerankWithVLLM(String query,
                                                  List<RecallAgent.ScoredCandidate> candidates,
                                                  int topK) {
        try {
            List<String> documents = new ArrayList<>();
            for (RecallAgent.ScoredCandidate c : candidates) {
                String text = c.document.getName() != null ? c.document.getName() : "";
                if (c.document.getDescription() != null) {
                    text += " " + c.document.getDescription();
                }
                documents.add(text.trim());
            }

            List<VLLMRerankClient.RerankResult> results = rerankClient.rerank(query, documents, topK);
            if (results == null || results.isEmpty()) {
                return null;
            }

            List<RankedCandidate> ranked = new ArrayList<>();
            for (VLLMRerankClient.RerankResult r : results) {
                int idx = r.getIndex();
                if (idx >= 0 && idx < candidates.size()) {
                    RecallAgent.ScoredCandidate c = candidates.get(idx);
                    ranked.add(new RankedCandidate(c.document, r.getRelevance_score(), new ArrayList<>(c.channels)));
                }
            }
            return ranked;
        } catch (Exception e) {
            log.warn("[{}] vLLM reranking failed: {}", getName(), e.getMessage());
            return null;
        }
    }

    /**
     * 固定权重融合重排序（回退策略）。
     */
    private List<RankedCandidate> rerankWithFixedWeights(List<RecallAgent.ScoredCandidate> candidates,
                                                          List<TBoxObjectType> objectTypes,
                                                          java.util.Set<String> structurePaths,
                                                          String queryIntent, int topK) {
        List<RankedCandidate> result = new ArrayList<>();

        for (RecallAgent.ScoredCandidate c : candidates) {
            double typeMatchScore = computeTypeMatchScore(c.document, objectTypes);
            double structureScore = computeStructureScore(c.document, structurePaths, queryIntent);

            double finalScore = c.exactScore * W_EXACT
                    + c.keywordScore * W_KEYWORD
                    + c.vectorScore * W_VECTOR
                    + structureScore * W_STRUCTURE
                    + typeMatchScore * W_TYPE_MATCH;

            result.add(new RankedCandidate(c.document, finalScore, new ArrayList<>(c.channels)));
        }

        result.sort(Comparator.comparingDouble((RankedCandidate c) -> c.score).reversed());
        return result.size() > topK ? result.subList(0, topK) : result;
    }

    private double computeStructureScore(TBoxIndexDocument doc, java.util.Set<String> structurePaths, String queryIntent) {
        double score = 0.0;
        if (structurePaths.contains(doc.getObjectPath())) {
            score += 0.8;
        }
        if (queryIntent != null && doc.getObjectType() != null) {
            score += switch (queryIntent) {
                case "RULE_LOOKUP" -> doc.getObjectType() == TBoxObjectType.RULE ? 0.5 : 0.0;
                case "PROPERTY_SEARCH" -> doc.getObjectType() == TBoxObjectType.PROPERTY ? 0.5 : 0.0;
                case "RELATIONSHIP_QUERY" -> doc.getObjectType() == TBoxObjectType.RELATIONSHIP ? 0.5 : 0.0;
                case "FUNCTION_QUERY" -> doc.getObjectType() == TBoxObjectType.FUNCTION ? 0.5 : 0.0;
                default -> 0.1;
            };
        }
        return Math.min(score, 1.0);
    }

    private double computeTypeMatchScore(TBoxIndexDocument doc, List<TBoxObjectType> objectTypes) {
        if (objectTypes == null || objectTypes.isEmpty()) {
            return 0.5;
        }
        return objectTypes.contains(doc.getObjectType()) ? 1.0 : 0.0;
    }

    public static class RankedCandidate {
        public final TBoxIndexDocument document;
        public double score;
        public final List<String> channels;

        public RankedCandidate(TBoxIndexDocument document, double score, List<String> channels) {
            this.document = document;
            this.score = score;
            this.channels = channels;
        }
    }
}
