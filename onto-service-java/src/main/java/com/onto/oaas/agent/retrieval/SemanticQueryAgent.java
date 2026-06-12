package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.QueryIntentV2;
import com.onto.oaas.model.QueryIntentV2.StructureConstraint;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 语义查询理解 Agent（V2）。
 *
 * <p>职责：基于本地规则分析自然语言查询，执行实体链接、意图识别、结构约束提取、查询扩展。</p>
 *
 * <p>输入：{@link AgentMessageType#QUERY_ANALYZE_V2}</p>
 * <p>输出：{@link AgentMessageType#QUERY_ANALYZED_V2}</p>
 */
@Slf4j
@Component
public class SemanticQueryAgent extends AbstractAgent {

    private static final Pattern PATH_PATTERN = Pattern.compile("[a-zA-Z_][a-zA-Z0-9_]*(?:\\.[a-zA-Z_][a-zA-Z0-9_]*)*");

    public SemanticQueryAgent(AgentBus agentBus) {
        super(agentBus);
        subscribeTo(AgentMessageType.QUERY_ANALYZE_V2);
    }

    @Override
    public String getName() {
        return "SemanticQueryAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        String query = message.getPayload("query", String.class);
        if (query == null || query.isBlank()) {
            publishEmptyIntent(message);
            return;
        }

        log.info("[{}] Analyzing query V2: '{}', correlationId={}", getName(), query, message.getCorrelationId());

        QueryIntentV2 intent = analyzeLocal(query);

        AgentMessage reply = message.reply(AgentMessageType.QUERY_ANALYZED_V2)
                .putPayload("intent", intent)
                .putPayload("query", query);
        publish(reply);
    }

    private void publishEmptyIntent(AgentMessage original) {
        QueryIntentV2 empty = QueryIntentV2.builder()
                .linkedEntityPaths(List.of())
                .intent("UNKNOWN")
                .constraints(List.of())
                .expandedQueries(List.of())
                .keywordHints(List.of())
                .objectTypeHints(List.of())
                .possibleObjectPaths(List.of())
                .build();
        publish(original.reply(AgentMessageType.QUERY_ANALYZED_V2)
                .putPayload("intent", empty)
                .putPayload("query", ""));
    }

    /**
     * 本地规则分析。
     */
    public QueryIntentV2 analyzeLocal(String query) {
        if (query == null || query.isBlank()) {
            return emptyIntent();
        }

        // 1. 意图识别
        String intent = detectIntent(query);

        // 2. 结构约束提取
        List<StructureConstraint> constraints = extractStructureConstraints(query, intent);

        // 3. 对象类型提示（V1 兼容）
        List<String> objectTypeHints = detectObjectTypeHints(query);

        // 4. 可能路径（V1 兼容）
        List<String> possiblePaths = extractPossiblePaths(query);

        // 5. 关键词提取（V1 兼容）
        List<String> keywords = extractKeywords(query);

        // 6. 查询扩展（同义词）
        List<String> expandedQueries = expandQuery(query, keywords);

        // 7. 实体链接（简化版：基于路径匹配）
        List<String> linkedEntities = possiblePaths.stream()
                .filter(p -> p.split("\\.").length >= 2)
                .toList();

        return QueryIntentV2.builder()
                .linkedEntityPaths(linkedEntities)
                .intent(intent)
                .constraints(constraints)
                .expandedQueries(expandedQueries)
                .keywordHints(keywords)
                .objectTypeHints(objectTypeHints)
                .possibleObjectPaths(possiblePaths)
                .build();
    }

    /**
     * 意图识别：基于关键词规则分类。
     */
    private String detectIntent(String query) {
        String lower = query.toLowerCase();

        // 规则查询
        if (lower.contains("规则") || lower.contains("rule")
                || lower.contains("指标") || lower.contains("度量") || lower.contains("measure")
                || lower.contains("统计") || lower.contains("多少") || lower.contains("数")) {
            return "RULE_LOOKUP";
        }

        // 属性查询
        if (lower.contains("属性") || lower.contains("字段") || lower.contains("列")
                || lower.contains("property") || lower.contains("有什么")) {
            return "PROPERTY_SEARCH";
        }

        // 关系查询
        if (lower.contains("关系") || lower.contains("关联") || lower.contains("连接")
                || lower.contains("relationship") || lower.contains("related")) {
            return "RELATIONSHIP_QUERY";
        }

        // 定义/概念查询
        if (lower.contains("是什么") || lower.contains("定义") || lower.contains("概念")
                || lower.contains("什么意思") || lower.contains("介绍")) {
            return "DEFINITION";
        }

        // 函数/计算查询
        if (lower.contains("函数") || lower.contains("计算") || lower.contains("聚合")
                || lower.contains("function") || lower.contains("agg")) {
            return "FUNCTION_QUERY";
        }

        // 路径/导航查询
        if (lower.contains("路径") || lower.contains("怎么找") || lower.contains("从")
                || lower.contains("到") || lower.contains("经过")) {
            return "PATH_NAVIGATION";
        }

        return "GENERAL";
    }

    /**
     * 提取结构约束：根据查询中的语法模式识别结构约束。
     */
    private List<StructureConstraint> extractStructureConstraints(String query, String intent) {
        List<StructureConstraint> constraints = new ArrayList<>();
        String lower = query.toLowerCase();

        // 类型过滤约束："...的指标" → TYPE_FILTER: RULE
        if (lower.contains("的指标") || lower.contains("的度量") || lower.contains("的measure") || lower.contains("的规则")) {
            constraints.add(StructureConstraint.builder()
                    .type("TYPE_FILTER")
                    .value(TBoxObjectType.RULE.name())
                    .description("查询目标为规则/指标/度量")
                    .build());
        }
        if (lower.contains("的属性") || lower.contains("的字段")) {
            constraints.add(StructureConstraint.builder()
                    .type("TYPE_FILTER")
                    .value(TBoxObjectType.PROPERTY.name())
                    .description("查询目标为属性")
                    .build());
        }
        if (lower.contains("的关系") || lower.contains("的关联")) {
            constraints.add(StructureConstraint.builder()
                    .type("TYPE_FILTER")
                    .value(TBoxObjectType.RELATIONSHIP.name())
                    .description("查询目标为关系")
                    .build());
        }

        // 路径前缀约束：包含 domain 或 type 路径
        var matcher = PATH_PATTERN.matcher(query);
        while (matcher.find()) {
            String path = matcher.group();
            String[] parts = path.split("\\.");
            if (parts.length >= 1) {
                constraints.add(StructureConstraint.builder()
                        .type("PATH_PREFIX")
                        .value(parts[0])
                        .description("Domain 前缀约束: " + parts[0])
                        .build());
            }
        }

        // 跳数约束："附近"、"相关" → 1-2 hop
        if (lower.contains("相关") || lower.contains("附近") || lower.contains("周边")) {
            constraints.add(StructureConstraint.builder()
                    .type("HOP_DISTANCE")
                    .value("2")
                    .description("相关实体在 2 跳以内")
                    .build());
        }

        return constraints;
    }

    /**
     * 查询扩展：同义词和上下位词。
     */
    private List<String> expandQuery(String query, List<String> keywords) {
        List<String> expanded = new ArrayList<>();
        expanded.add(query);

        // 简单的同义词映射（可扩展为调用外部词库/LLM）
        for (String kw : keywords) {
            String synonym = switch (kw.toLowerCase()) {
                case "故障" -> "错误 异常 损坏 breakdown fault error";
                case "设备" -> "机器 装置 硬件 equipment machine device";
                case "统计" -> "计算 汇总 聚合 count sum aggregate";
                case "属性" -> "字段 列 特征 property field column";
                default -> null;
            };
            if (synonym != null) {
                expanded.add(query.replace(kw, synonym));
            }
        }

        return expanded.stream().distinct().toList();
    }

    private List<String> detectObjectTypeHints(String query) {
        List<String> hints = new ArrayList<>();
        String lower = query.toLowerCase();
        if (lower.contains("领域") || lower.contains("domain")) {
            hints.add(TBoxObjectType.DOMAIN.name());
        }
        if (lower.contains("类型") || lower.contains("type")) {
            hints.add(TBoxObjectType.TYPE.name());
        }
        if (lower.contains("属性") || lower.contains("property") || lower.contains("字段")) {
            hints.add(TBoxObjectType.PROPERTY.name());
        }
        if (lower.contains("关系") || lower.contains("relationship") || lower.contains("关联")) {
            hints.add(TBoxObjectType.RELATIONSHIP.name());
        }
        if (lower.contains("函数") || lower.contains("function") || lower.contains("计算")) {
            hints.add(TBoxObjectType.FUNCTION.name());
        }
        if (lower.contains("规则") || lower.contains("rule") || lower.contains("指标") || lower.contains("measure") || lower.contains("度量") || lower.contains("统计")) {
            hints.add(TBoxObjectType.RULE.name());
        }
        return hints;
    }

    private List<String> extractPossiblePaths(String query) {
        List<String> paths = new ArrayList<>();
        var matcher = PATH_PATTERN.matcher(query);
        while (matcher.find()) {
            String candidate = matcher.group();
            if (candidate.contains(".")) {
                paths.add(candidate);
            }
        }
        return paths;
    }

    private List<String> extractKeywords(String query) {
        String[] tokens = query.split("[\\s,，.。;；!！?？]+");
        List<String> keywords = new ArrayList<>();
        for (String token : tokens) {
            String trimmed = token.trim();
            if (!trimmed.isEmpty() && trimmed.length() > 1) {
                keywords.add(trimmed);
            }
        }
        return keywords;
    }

    private QueryIntentV2 emptyIntent() {
        return QueryIntentV2.builder()
                .linkedEntityPaths(List.of())
                .intent("UNKNOWN")
                .constraints(List.of())
                .expandedQueries(List.of())
                .keywordHints(List.of())
                .objectTypeHints(List.of())
                .possibleObjectPaths(List.of())
                .build();
    }
}
