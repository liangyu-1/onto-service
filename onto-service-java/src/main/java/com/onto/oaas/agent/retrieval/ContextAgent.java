package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.dto.TBoxObjectDetailResponse;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.service.retrieval.TBoxContextService;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 上下文增强 Agent。
 *
 * <p>职责：为 Top-K 检索结果中的每个候选对象补充详细上下文信息（如维度、指标、绑定等）。</p>
 * <p>输入：{@link AgentMessageType#CONTEXT_ENRICH}，payload 包含 "rankedCandidates" (List&lt;RerankAgent.RankedCandidate&gt;)</p>
 * <p>输出：{@link AgentMessageType#CONTEXT_ENRICHED}，payload 包含 "enrichedCandidates" (List&lt;EnrichedCandidate&gt;)</p>
 */
@Slf4j
@Component
public class ContextAgent extends AbstractAgent {

    private final TBoxContextService contextService;

    public ContextAgent(AgentBus agentBus, TBoxContextService contextService) {
        super(agentBus);
        this.contextService = contextService;
        subscribeTo(AgentMessageType.CONTEXT_ENRICH);
    }

    @Override
    public String getName() {
        return "ContextAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        List<RerankAgent.RankedCandidate> candidates = message.getPayload("rankedCandidates", List.class);
        if (candidates == null || candidates.isEmpty()) {
            publish(message.reply(AgentMessageType.CONTEXT_ENRICHED)
                    .putPayload("enrichedCandidates", List.of()));
            return;
        }

        log.info("[{}] Enriching context for {} candidates, correlationId={}",
                getName(), candidates.size(), message.getCorrelationId());

        List<EnrichedCandidate> enriched = new ArrayList<>();
        for (RerankAgent.RankedCandidate c : candidates) {
            Map<String, Object> context = fetchContext(c.document);
            enriched.add(new EnrichedCandidate(c.document, c.score, c.channels, context));
        }

        publish(message.reply(AgentMessageType.CONTEXT_ENRICHED)
                .putPayload("enrichedCandidates", enriched));
    }

    private Map<String, Object> fetchContext(TBoxIndexDocument doc) {
        Map<String, Object> ctx = new HashMap<>();
        try {
            TBoxObjectDetailResponse detail = contextService.getObjectDetail(doc.getObjectPath());
            if (detail != null && detail.getContext() != null) {
                ctx.putAll(detail.getContext());
            }
        } catch (Exception e) {
            log.debug("[{}] Failed to fetch context for {}: {}", getName(), doc.getObjectPath(), e.getMessage());
        }
        return ctx;
    }

    /**
     * 增强后的候选结果。
     */
    public static class EnrichedCandidate {
        public final TBoxIndexDocument document;
        public final double score;
        public final List<String> channels;
        public final Map<String, Object> context;

        public EnrichedCandidate(TBoxIndexDocument document, double score, List<String> channels, Map<String, Object> context) {
            this.document = document;
            this.score = score;
            this.channels = channels;
            this.context = context;
        }
    }
}
