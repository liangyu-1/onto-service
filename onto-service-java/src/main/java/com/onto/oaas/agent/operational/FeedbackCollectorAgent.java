package com.onto.oaas.agent.operational;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 用户反馈收集 Agent。
 *
 * <p>职责：收集检索结果的用户交互反馈（点击、停留时间等），
 * 为学习排序（LTR）提供训练数据。</p>
 *
 * <p>输入：{@link AgentMessageType#FEEDBACK_RECORD}</p>
 * <p>输出：无（内部存储，定期批量写入数据库）</p>
 */
@Slf4j
@Component
public class FeedbackCollectorAgent extends AbstractAgent {

    // 内存中暂存反馈数据（生产环境应写入数据库）
    private final Map<String, UserFeedback> feedbackStore = new ConcurrentHashMap<>();

    public FeedbackCollectorAgent(AgentBus agentBus) {
        super(agentBus);
        subscribeTo(AgentMessageType.FEEDBACK_RECORD);
    }

    @Override
    public String getName() {
        return "FeedbackCollectorAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        String queryId = message.getPayload("queryId", String.class);
        String query = message.getPayload("query", String.class);
        String objectPath = message.getPayload("objectPath", String.class);
        Integer position = message.getPayload("position", Integer.class);
        Boolean clicked = message.getPayload("clicked", Boolean.class);
        Long dwellTimeMs = message.getPayload("dwellTimeMs", Long.class);

        if (queryId == null || objectPath == null) {
            log.warn("[{}] Invalid feedback record: missing queryId or objectPath", getName());
            return;
        }

        UserFeedback feedback = UserFeedback.builder()
                .queryId(queryId)
                .query(query)
                .objectPath(objectPath)
                .position(position != null ? position : -1)
                .clicked(clicked != null ? clicked : false)
                .dwellTimeMs(dwellTimeMs != null ? dwellTimeMs : 0)
                .timestamp(Instant.now())
                .build();

        String key = queryId + ":" + objectPath;
        feedbackStore.put(key, feedback);

        log.info("[{}] Recorded feedback: queryId={}, objectPath={}, clicked={}, position={}",
                getName(), queryId, objectPath, clicked, position);
    }

    /**
     * 获取反馈统计（供 LTRTrainingAgent 使用）。
     */
    public Map<String, UserFeedback> getFeedbackStore() {
        return Map.copyOf(feedbackStore);
    }

    /**
     * 用户反馈记录。
     */
    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class UserFeedback {
        private String queryId;
        private String query;
        private String objectPath;
        private int position;
        private boolean clicked;
        private long dwellTimeMs;
        private Instant timestamp;
    }
}
