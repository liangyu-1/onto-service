package com.onto.oaas.agent.operational;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.DlqRecord;
import com.onto.oaas.service.dlq.DeadLetterQueueService;
import java.time.Instant;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 死信队列 Agent。
 *
 * <p>职责：管理消费失败或无法解析的消息，支持查询、重试、归档。</p>
 * <p>输入：{@link AgentMessageType#DLQ_STORE}</p>
 * <p>输出：无（内部管理 DLQ 记录）</p>
 */
@Slf4j
@Component
public class DlqAgent extends AbstractAgent {

    private final DeadLetterQueueService dlqService;

    public DlqAgent(AgentBus agentBus, DeadLetterQueueService dlqService) {
        super(agentBus);
        this.dlqService = dlqService;
        subscribeTo(AgentMessageType.DLQ_STORE);
    }

    @Override
    public String getName() {
        return "DlqAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        String eventId = message.getPayload("eventId", String.class);
        String eventType = message.getPayload("eventType", String.class);
        String rawPayload = message.getPayload("rawPayload", String.class);
        String errorReason = message.getPayload("errorReason", String.class);
        String errorCode = message.getPayload("errorCode", String.class);

        log.warn("[{}] Storing to DLQ: eventId={}, eventType={}, error={}, correlationId={}",
                getName(), eventId, eventType, errorReason, message.getCorrelationId());

        DlqRecord record = DlqRecord.builder()
                .dlqRecordId(java.util.UUID.randomUUID().toString())
                .originalEventId(eventId)
                .eventType(eventType)
                .rawPayload(rawPayload)
                .errorReason(errorReason)
                .errorCode(errorCode)
                .status("PENDING")
                .createdTime(Instant.now())
                .updatedTime(Instant.now())
                .build();

        dlqService.sendToDlq(eventId, eventType, rawPayload, errorReason, errorCode);
    }

    /**
     * 查询 DLQ 中的记录。
     */
    public List<DlqRecord> queryDlq() {
        return dlqService.queryDlq(null, null, 100);
    }

    /**
     * 重试 DLQ 中的记录。
     */
    public void replayDlq(String dlqRecordId) {
        dlqService.replayDlq(dlqRecordId);
    }
}
