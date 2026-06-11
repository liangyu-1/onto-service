package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.QueryIntent;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 查询理解 Agent。
 *
 * <p>职责：接收自然语言查询，分析意图，提取关键词、对象类型提示、可能的对象路径。</p>
 * <p>输入：{@link AgentMessageType#QUERY_ANALYZE}，payload 包含 "query" (String)</p>
 * <p>输出：{@link AgentMessageType#QUERY_ANALYZED}，payload 包含 "intent" ({@link QueryIntent})</p>
 */
@Slf4j
@Component
public class QueryAgent extends AbstractAgent {

    private static final Pattern PATH_PATTERN = Pattern.compile("[a-zA-Z_][a-zA-Z0-9_]*(?:\\.[a-zA-Z_][a-zA-Z0-9_]*)*");

    public QueryAgent(AgentBus agentBus) {
        super(agentBus);
        subscribeTo(AgentMessageType.QUERY_ANALYZE);
    }

    @Override
    public String getName() {
        return "QueryAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        String query = message.getPayload("query", String.class);
        if (query == null || query.isBlank()) {
            log.warn("[{}] Received empty query, correlationId={}", getName(), message.getCorrelationId());
            publishEmptyIntent(message);
            return;
        }

        log.info("[{}] Analyzing query: '{}', correlationId={}", getName(), query, message.getCorrelationId());

        QueryIntent intent = analyze(query);

        AgentMessage reply = message.reply(AgentMessageType.QUERY_ANALYZED)
                .putPayload("intent", intent)
                .putPayload("query", query);
        publish(reply);
    }

    private void publishEmptyIntent(AgentMessage original) {
        QueryIntent empty = QueryIntent.builder()
                .possibleObjectPaths(List.of())
                .objectTypeHints(List.of())
                .keywordHints(List.of())
                .build();
        publish(original.reply(AgentMessageType.QUERY_ANALYZED)
                .putPayload("intent", empty)
                .putPayload("query", ""));
    }

    /**
     * 核心分析逻辑：提取类型提示、可能路径、关键词。
     */
    public QueryIntent analyze(String query) {
        if (query == null || query.isBlank()) {
            return QueryIntent.builder()
                    .possibleObjectPaths(List.of())
                    .objectTypeHints(List.of())
                    .keywordHints(List.of())
                    .build();
        }
        List<String> objectTypeHints = detectObjectTypeHints(query);
        List<String> possibleObjectPaths = extractPossiblePaths(query);
        List<String> keywordHints = extractKeywords(query);

        return QueryIntent.builder()
                .possibleObjectPaths(possibleObjectPaths)
                .objectTypeHints(objectTypeHints)
                .keywordHints(keywordHints)
                .build();
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
        if (lower.contains("属性") || lower.contains("property")) {
            hints.add(TBoxObjectType.PROPERTY.name());
        }
        if (lower.contains("关系") || lower.contains("relationship")) {
            hints.add(TBoxObjectType.RELATIONSHIP.name());
        }
        if (lower.contains("函数") || lower.contains("function")) {
            hints.add(TBoxObjectType.FUNCTION.name());
        }
        if (lower.contains("规则") || lower.contains("rule") || lower.contains("指标") || lower.contains("measure")) {
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
}
