package com.onto.oaas.controller;

import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.agent.retrieval.ContextAgent;
import com.onto.oaas.agent.retrieval.PlannerAgent;
import com.onto.oaas.agent.retrieval.RecallAgent;
import com.onto.oaas.agent.retrieval.RerankAgent;
import com.onto.oaas.agent.retrieval.SubgraphAgent;
import com.onto.oaas.dto.TBoxCandidateDto;
import com.onto.oaas.dto.TBoxObjectDetailResponse;
import com.onto.oaas.dto.TBoxRetrieveRequest;
import com.onto.oaas.dto.TBoxRetrieveResponse;
import com.onto.oaas.dto.TBoxSubgraphRequest;
import com.onto.oaas.dto.TBoxSubgraphResponse;
import com.onto.oaas.dto.TBoxValidateRequest;
import com.onto.oaas.dto.TBoxValidateResponse;
import com.onto.oaas.model.QueryIntent;
import com.onto.oaas.model.QueryIntentV2;
import com.onto.oaas.model.SubgraphResult;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.service.retrieval.TBoxContextService;
import com.onto.oaas.util.ObjectPathUtil;
import com.onto.oaas.util.TraceIdGenerator;
import jakarta.validation.Valid;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * TBox 检索控制器（多智能体版本）。
 *
 * <p>通过 AgentBus 发起检索 Pipeline，替代原有的直接 Service 调用。</p>
 */
@RestController
@RequestMapping("/v1/tbox")
@RequiredArgsConstructor
@Slf4j
public class TBoxRetrievalController {

    private final AgentBus agentBus;
    private final TBoxContextService contextService;

    // 用于同步等待 Agent 响应的临时存储
    private final Map<String, CompletableFuture<AgentMessage>> pendingResponses = new ConcurrentHashMap<>();
    private static final long RESPONSE_TIMEOUT_MS = 15000;

    @PostMapping("/retrieve")
    public ResponseEntity<TBoxRetrieveResponse> retrieveTopK(@Valid @RequestBody TBoxRetrieveRequest request) {
        String queryId = TraceIdGenerator.generateQueryId();
        String query = request.getQuery();
        int topK = request.getTopK();
        var filters = request.getFilters();
        var options = request.getOptions();

        log.info("Retrieve request: queryId={}, query={}, topK={}", queryId, query, topK);

        boolean skipIntent = options != null && options.isSkipIntentAnalysis();
        List<TBoxCandidateDto> objects;
        String mode;
        if (skipIntent) {
            mode = "direct";
            objects = executeDirectRetrieval(queryId, query, topK, filters, options);
        } else {
            mode = "agent-planned";
            objects = executePlannedRetrieval(queryId, query, topK, filters, options);
        }

        return ResponseEntity.ok(TBoxRetrieveResponse.builder()
                .queryId(queryId)
                .mode(mode)
                .objects(objects)
                .build());
    }

    /**
     * 直接召回：跳过意图识别和 Planner，直接调用 RecallAgent + RerankAgent。
     */
    @SuppressWarnings("unchecked")
    private List<TBoxCandidateDto> executeDirectRetrieval(String queryId, String query, int topK,
                                                           com.onto.oaas.dto.TBoxFilters filters,
                                                           com.onto.oaas.dto.RetrieveOptions options) {
        List<TBoxObjectType> objectTypes = filters != null ? filters.getObjectTypes() : null;
        boolean enableKeyword = options != null && options.isEnableKeywordRecall();
        boolean enableVector = options != null && options.isEnableVectorRecall();
        boolean includeContext = options != null && options.isIncludeContext();

        AgentMessage recallMsg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.RECALL_REQUEST)
                .build();
        recallMsg.putPayload("query", query);
        recallMsg.putPayload("topK", topK);
        recallMsg.putPayload("objectTypes", objectTypes);
        recallMsg.putPayload("enableKeywordRecall", enableKeyword);
        recallMsg.putPayload("enableVectorRecall", enableVector);

        List<RecallAgent.ScoredCandidate> candidates = waitForResponse(recallMsg, AgentMessageType.RECALL_RESULT)
                .getPayload("candidates", List.class);
        if (candidates == null) {
            candidates = Collections.emptyList();
        }

        AgentMessage rerankMsg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.RERANK_REQUEST)
                .build();
        rerankMsg.putPayload("query", query);
        rerankMsg.putPayload("candidates", candidates);
        rerankMsg.putPayload("topK", topK);
        rerankMsg.putPayload("objectTypes", objectTypes);
        rerankMsg.putPayload("structureDocuments", Collections.emptyList());
        rerankMsg.putPayload("queryIntent", "UNKNOWN");

        List<RerankAgent.RankedCandidate> ranked = waitForResponse(rerankMsg, AgentMessageType.RERANK_RESULT)
                .getPayload("rankedCandidates", List.class);
        if (ranked == null) {
            ranked = Collections.emptyList();
        }

        List<ContextAgent.EnrichedCandidate> enriched = Collections.emptyList();
        if (includeContext && !ranked.isEmpty()) {
            AgentMessage enrichMsg = AgentMessage.builder()
                    .correlationId(queryId)
                    .type(AgentMessageType.CONTEXT_ENRICH)
                    .build();
            enrichMsg.putPayload("rankedCandidates", ranked);

            List<ContextAgent.EnrichedCandidate> ctxResult = waitForResponse(enrichMsg, AgentMessageType.CONTEXT_ENRICHED)
                    .getPayload("enrichedCandidates", List.class);
            enriched = ctxResult != null ? ctxResult : Collections.emptyList();
        }

        List<TBoxCandidateDto> objects = new ArrayList<>();
        if (includeContext && !enriched.isEmpty()) {
            for (ContextAgent.EnrichedCandidate c : enriched) {
                objects.add(toCandidateDto(c.document, c.score, c.channels, c.context));
            }
        } else {
            for (RerankAgent.RankedCandidate c : ranked) {
                objects.add(toCandidateDto(c.document, c.score, c.channels, null));
            }
        }

        return objects;
    }

    /**
     * 执行 PlannerAgent 编排的智能检索流水线。
     */
    @SuppressWarnings("unchecked")
    private List<TBoxCandidateDto> executePlannedRetrieval(String queryId, String query, int topK,
                                                            com.onto.oaas.dto.TBoxFilters filters,
                                                            com.onto.oaas.dto.RetrieveOptions options) {
        List<TBoxObjectType> objectTypes = filters != null ? filters.getObjectTypes() : null;
        boolean enableKeyword = options != null && options.isEnableKeywordRecall();
        boolean enableVector = options != null && options.isEnableVectorRecall();
        boolean includeContext = options != null && options.isIncludeContext();

        // Step 1: SemanticQueryAgent 分析查询（V2）
        AgentMessage semanticMsg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.QUERY_ANALYZE_V2)
                .build();
        semanticMsg.putPayload("query", query);
        QueryIntentV2 intentV2 = waitForResponse(semanticMsg, AgentMessageType.QUERY_ANALYZED_V2)
                .getPayload("intent", QueryIntentV2.class);

        // Step 2: PlannerAgent 规划检索策略
        AgentMessage planMsg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.RETRIEVAL_PLAN_REQUEST)
                .build();
        planMsg.putPayload("query", query);
        planMsg.putPayload("intent", intentV2);
        PlannerAgent.RetrievalPlan plan = waitForResponse(planMsg, AgentMessageType.RETRIEVAL_PLAN_RESULT)
                .getPayload("plan", PlannerAgent.RetrievalPlan.class);

        String planDesc = plan != null ? plan.getDescription() : "default";
        log.info("Retrieval plan: {}", planDesc);

        // Step 3: 结构感知召回（如果计划启用）
        List<TBoxIndexDocument> structureDocs = Collections.emptyList();
        if (plan != null && plan.isEnableStructureRecall()) {
            AgentMessage structureMsg = AgentMessage.builder()
                    .correlationId(queryId)
                    .type(AgentMessageType.STRUCTURE_RECALL_REQUEST)
                    .build();
            structureMsg.putPayload("intent", intentV2);
            structureMsg.putPayload("topK", topK * 2);
            structureDocs = waitForResponse(structureMsg, AgentMessageType.STRUCTURE_RECALL_RESULT)
                    .getPayload("documents", List.class);
            if (structureDocs == null) {
                structureDocs = Collections.emptyList();
            }
        }

        // Step 4: 混合召回（RecallAgent）
        AgentMessage recallMsg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.RECALL_REQUEST)
                .build();
        recallMsg.putPayload("query", query);
        recallMsg.putPayload("intent", intentV2);
        recallMsg.putPayload("topK", topK);
        recallMsg.putPayload("objectTypes", objectTypes);
        recallMsg.putPayload("enableKeywordRecall", enableKeyword);
        recallMsg.putPayload("enableVectorRecall", enableVector);

        List<RecallAgent.ScoredCandidate> candidates = waitForResponse(recallMsg, AgentMessageType.RECALL_RESULT)
                .getPayload("candidates", List.class);
        if (candidates == null) {
            candidates = Collections.emptyList();
        }

        // Step 5: RerankAgent 重排序（传入结构召回结果）
        AgentMessage rerankMsg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.RERANK_REQUEST)
                .build();
        rerankMsg.putPayload("query", query);
        rerankMsg.putPayload("candidates", candidates);
        rerankMsg.putPayload("topK", topK);
        rerankMsg.putPayload("objectTypes", objectTypes);
        rerankMsg.putPayload("structureDocuments", structureDocs);
        rerankMsg.putPayload("queryIntent", intentV2 != null ? intentV2.getIntent() : null);

        List<RerankAgent.RankedCandidate> ranked = waitForResponse(rerankMsg, AgentMessageType.RERANK_RESULT)
                .getPayload("rankedCandidates", List.class);
        if (ranked == null) {
            ranked = Collections.emptyList();
        }

        // Step 6: ContextAgent 上下文增强（可选）
        List<ContextAgent.EnrichedCandidate> enriched = Collections.emptyList();
        if (includeContext && !ranked.isEmpty()) {
            AgentMessage enrichMsg = AgentMessage.builder()
                    .correlationId(queryId)
                    .type(AgentMessageType.CONTEXT_ENRICH)
                    .build();
            enrichMsg.putPayload("rankedCandidates", ranked);

            List<ContextAgent.EnrichedCandidate> ctxResult = waitForResponse(enrichMsg, AgentMessageType.CONTEXT_ENRICHED)
                    .getPayload("enrichedCandidates", List.class);
            enriched = ctxResult != null ? ctxResult : Collections.emptyList();
        }

        // 组装结果
        List<TBoxCandidateDto> objects = new ArrayList<>();
        if (includeContext && !enriched.isEmpty()) {
            for (ContextAgent.EnrichedCandidate c : enriched) {
                objects.add(toCandidateDto(c.document, c.score, c.channels, c.context));
            }
        } else {
            for (RerankAgent.RankedCandidate c : ranked) {
                objects.add(toCandidateDto(c.document, c.score, c.channels, null));
            }
        }

        return objects;
    }

    @PostMapping("/subgraph")
    public ResponseEntity<TBoxSubgraphResponse> retrieveSubgraph(@Valid @RequestBody TBoxSubgraphRequest request) {
        String queryId = TraceIdGenerator.generateQueryId();
        log.info("Subgraph request: queryId={}, start={}, hops={}", queryId, request.getStartObjectPath(), request.getHops());

        AgentMessage msg = AgentMessage.builder()
                .correlationId(queryId)
                .type(AgentMessageType.SUBGRAPH_EXPAND)
                .build();
        msg.putPayload("startObjectPath", request.getStartObjectPath());
        msg.putPayload("hops", request.getHops());
        msg.putPayload("direction", request.getDirection());
        msg.putPayload("relationTypes", request.getFilters() != null ? request.getFilters().getRelationTypes() : null);
        msg.putPayload("objectTypes", request.getFilters() != null ? request.getFilters().getObjectTypes() : null);
        msg.putPayload("maxNodes", request.getOptions() != null ? request.getOptions().getMaxNodes() : 100);
        msg.putPayload("maxEdges", request.getOptions() != null ? request.getOptions().getMaxEdges() : 200);

        SubgraphResult result = waitForResponse(msg, AgentMessageType.SUBGRAPH_RESULT)
                .getPayload("subgraphResult", SubgraphResult.class);

        return ResponseEntity.ok(toSubgraphResponse(queryId, result));
    }

    @GetMapping("/objects/detail")
    public ResponseEntity<TBoxObjectDetailResponse> getObjectDetail(@RequestParam String objectPath) {
        log.info("Object detail request: path={}", objectPath);
        TBoxObjectDetailResponse response = contextService.getObjectDetail(objectPath);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/objects/validate")
    public ResponseEntity<TBoxValidateResponse> validateObject(@Valid @RequestBody TBoxValidateRequest request) {
        log.info("Validate request: path={}", request.getObjectPath());
        TBoxObjectType objectType = ObjectPathUtil.getObjectTypeFromPath(request.getObjectPath());
        boolean exists = false;
        String name = null;
        try {
            TBoxObjectDetailResponse detail = contextService.getObjectDetail(request.getObjectPath());
            exists = true;
            name = detail.getName();
        } catch (Exception e) {
            log.debug("Validation failed for {}: {}", request.getObjectPath(), e.getMessage());
        }
        return ResponseEntity.ok(TBoxValidateResponse.builder()
                .exists(exists)
                .objectPath(request.getObjectPath())
                .objectType(objectType)
                .name(name)
                .build());
    }

    // ========== 内部辅助方法 ==========

    /**
     * 同步等待 Agent 响应。Controller 需要同步返回 HTTP 响应，因此使用 CompletableFuture 阻塞等待。
     * 注意：这是简化实现。生产环境可考虑使用 WebFlux 异步响应或 SSE。
     */
    private AgentMessage waitForResponse(AgentMessage request, AgentMessageType expectedResponseType) {
        String correlationId = request.getCorrelationId();
        CompletableFuture<AgentMessage> future = new CompletableFuture<>();
        pendingResponses.put(correlationId, future);

        // 注册一个临时监听器来接收响应
        agentBus.publish(request);

        try {
            AgentMessage response = future.get(RESPONSE_TIMEOUT_MS, TimeUnit.MILLISECONDS);
            return response;
        } catch (Exception e) {
            log.error("Timeout or error waiting for response: correlationId={}, expectedType={}", correlationId, expectedResponseType, e);
            return AgentMessage.builder()
                    .correlationId(correlationId)
                    .type(expectedResponseType)
                    .build();
        } finally {
            pendingResponses.remove(correlationId);
        }
    }

    /**
     * 监听 AgentBus 上的所有响应消息，完成对应的 Future。
     */
    @org.springframework.context.event.EventListener
    public void onAgentBusEvent(com.onto.oaas.agent.core.AgentBus.AgentBusEvent event) {
        onAgentResponse(event.getMessage());
    }

    private void onAgentResponse(AgentMessage response) {
        if (response == null || response.getCorrelationId() == null) {
            // 增量同步等事件没有 correlationId，忽略
            return;
        }
        CompletableFuture<AgentMessage> future = pendingResponses.get(response.getCorrelationId());
        if (future != null && !future.isDone()) {
            future.complete(response);
        }
    }

    private TBoxCandidateDto toCandidateDto(com.onto.oaas.model.TBoxIndexDocument doc,
                                             double score, List<String> channels,
                                             Map<String, Object> context) {
        return TBoxCandidateDto.builder()
                .objectPath(doc.getObjectPath())
                .objectType(doc.getObjectType())
                .name(doc.getName())
                .description(doc.getDescription())
                .score(score)
                .matchedFields(new ArrayList<>(channels))
                .context(context)
                .build();
    }

    private TBoxSubgraphResponse toSubgraphResponse(String queryId, SubgraphResult result) {
        if (result == null) {
            return TBoxSubgraphResponse.builder()
                    .queryId(queryId)
                    .mode("subgraph")
                    .nodes(Collections.emptyList())
                    .edges(Collections.emptyList())
                    .truncated(false)
                    .build();
        }

        List<com.onto.oaas.dto.SubgraphNodeDto> nodeDtos = new ArrayList<>();
        if (result.getNodes() != null) {
            for (var node : result.getNodes()) {
                nodeDtos.add(com.onto.oaas.dto.SubgraphNodeDto.builder()
                        .objectPath(node.getObjectPath())
                        .objectType(node.getObjectType())
                        .name(node.getName())
                        .description(node.getDescription())
                        .hopDistance(node.getHopDistance())
                        .build());
            }
        }

        List<com.onto.oaas.dto.SubgraphEdgeDto> edgeDtos = new ArrayList<>();
        if (result.getEdges() != null) {
            for (var edge : result.getEdges()) {
                edgeDtos.add(com.onto.oaas.dto.SubgraphEdgeDto.builder()
                        .source(edge.getSource())
                        .relationType(edge.getRelationType())
                        .target(edge.getTarget())
                        .build());
            }
        }

        return TBoxSubgraphResponse.builder()
                .queryId(queryId)
                .mode("subgraph")
                .startObjectPath(result.getStartObjectPath())
                .hops(result.getHops())
                .nodes(nodeDtos)
                .edges(edgeDtos)
                .truncated(result.isTruncated())
                .build();
    }

    // ========== 反馈 API ==========

    @PostMapping("/feedback")
    public ResponseEntity<Map<String, Object>> recordFeedback(@RequestBody Map<String, Object> request) {
        String queryId = (String) request.get("queryId");
        String query = (String) request.get("query");
        String objectPath = (String) request.get("objectPath");
        Integer position = request.get("position") instanceof Number n ? n.intValue() : null;
        Boolean clicked = request.get("clicked") instanceof Boolean b ? b : null;
        Long dwellTimeMs = request.get("dwellTimeMs") instanceof Number n ? n.longValue() : null;

        if (queryId == null || objectPath == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "queryId and objectPath are required"));
        }

        AgentMessage feedbackMsg = AgentMessage.builder()
                .type(AgentMessageType.FEEDBACK_RECORD)
                .build();
        feedbackMsg.putPayload("queryId", queryId);
        feedbackMsg.putPayload("query", query);
        feedbackMsg.putPayload("objectPath", objectPath);
        feedbackMsg.putPayload("position", position);
        feedbackMsg.putPayload("clicked", clicked);
        feedbackMsg.putPayload("dwellTimeMs", dwellTimeMs);

        agentBus.publish(feedbackMsg);

        log.info("Feedback recorded: queryId={}, objectPath={}, clicked={}", queryId, objectPath, clicked);
        return ResponseEntity.ok(Map.of("status", "recorded", "queryId", queryId));
    }
}
