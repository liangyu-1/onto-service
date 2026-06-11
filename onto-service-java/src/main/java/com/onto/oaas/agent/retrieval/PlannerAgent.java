package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.QueryIntentV2;
import java.util.ArrayList;
import java.util.List;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 检索规划 Agent（编排器）。
 *
 * <p>职责：根据查询特征动态规划检索策略，决定调用哪些 Agent 以及调用顺序。</p>
 * <p>这是多智能体检索系统的"大脑"，将硬编码流水线升级为自适应编排。</p>
 *
 * <p>输入：{@link AgentMessageType#RETRIEVAL_PLAN_REQUEST}</p>
 * <p>输出：{@link AgentMessageType#RETRIEVAL_PLAN_RESULT}</p>
 */
@Slf4j
@Component
public class PlannerAgent extends AbstractAgent {

    public PlannerAgent(AgentBus agentBus) {
        super(agentBus);
        subscribeTo(AgentMessageType.RETRIEVAL_PLAN_REQUEST);
    }

    @Override
    public String getName() {
        return "PlannerAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        String query = message.getPayload("query", String.class);
        QueryIntentV2 intent = message.getPayload("intent", QueryIntentV2.class);

        log.info("[{}] Planning retrieval strategy for query='{}', intent={}, correlationId={}",
                getName(), query,
                intent != null ? intent.getIntent() : "UNKNOWN",
                message.getCorrelationId());

        RetrievalPlan plan = buildPlan(intent);

        log.info("[{}] Planned pipeline: {}, correlationId={}",
                getName(), plan.getAgentPipeline(), message.getCorrelationId());

        publish(message.reply(AgentMessageType.RETRIEVAL_PLAN_RESULT)
                .putPayload("plan", plan));
    }

    /**
     * 根据查询意图构建检索计划。
     */
    private RetrievalPlan buildPlan(QueryIntentV2 intent) {
        if (intent == null) {
            return defaultPlan();
        }

        return switch (intent.getIntent()) {
            case "RULE_LOOKUP" -> RetrievalPlan.builder()
                    .agentPipeline(List.of(
                            "SemanticQueryAgent",
                            "StructureAwareRecallAgent",
                            "RecallAgent",
                            "RerankAgent"))
                    .recallStrategy("structure_priority")
                    .enableHybrid(true)
                    .enableStructureRecall(true)
                    .description("规则查询：结构召回优先，结合混合检索")
                    .build();

            case "PROPERTY_SEARCH" -> RetrievalPlan.builder()
                    .agentPipeline(List.of(
                            "SemanticQueryAgent",
                            "StructureAwareRecallAgent",
                            "RecallAgent",
                            "RerankAgent"))
                    .recallStrategy("structure_priority")
                    .enableHybrid(true)
                    .enableStructureRecall(true)
                    .description("属性查询：结构召回优先")
                    .build();

            case "RELATIONSHIP_QUERY" -> RetrievalPlan.builder()
                    .agentPipeline(List.of(
                            "SemanticQueryAgent",
                            "SubgraphAgent",
                            "RecallAgent",
                            "RerankAgent"))
                    .recallStrategy("subgraph_priority")
                    .enableHybrid(true)
                    .enableStructureRecall(true)
                    .description("关系查询：子图扩展优先")
                    .build();

            case "DEFINITION" -> RetrievalPlan.builder()
                    .agentPipeline(List.of(
                            "SemanticQueryAgent",
                            "RecallAgent",
                            "RerankAgent"))
                    .recallStrategy("vector_priority")
                    .enableHybrid(true)
                    .enableStructureRecall(false)
                    .description("定义查询：向量语义召回优先")
                    .build();

            case "FUNCTION_QUERY" -> RetrievalPlan.builder()
                    .agentPipeline(List.of(
                            "SemanticQueryAgent",
                            "StructureAwareRecallAgent",
                            "RecallAgent",
                            "RerankAgent"))
                    .recallStrategy("structure_priority")
                    .enableHybrid(true)
                    .enableStructureRecall(true)
                    .description("函数查询：结构召回优先")
                    .build();

            case "PATH_NAVIGATION" -> RetrievalPlan.builder()
                    .agentPipeline(List.of(
                            "SemanticQueryAgent",
                            "SubgraphAgent",
                            "RerankAgent"))
                    .recallStrategy("subgraph_only")
                    .enableHybrid(false)
                    .enableStructureRecall(true)
                    .description("路径导航：纯子图扩展")
                    .build();

            default -> defaultPlan();
        };
    }

    private RetrievalPlan defaultPlan() {
        return RetrievalPlan.builder()
                .agentPipeline(List.of(
                        "QueryAgent",
                        "RecallAgent",
                        "RerankAgent"))
                .recallStrategy("balanced")
                .enableHybrid(true)
                .enableStructureRecall(false)
                .description("默认流水线：平衡召回策略")
                .build();
    }

    /**
     * 检索计划定义。
     */
    @Data
    @Builder
    public static class RetrievalPlan {
        /** Agent 执行流水线（有序） */
        private List<String> agentPipeline;
        /** 召回策略：structure_priority / vector_priority / subgraph_priority / balanced / subgraph_only */
        private String recallStrategy;
        /** 是否启用混合检索 */
        private boolean enableHybrid;
        /** 是否启用结构感知召回 */
        private boolean enableStructureRecall;
        /** 计划描述 */
        private String description;
    }
}
