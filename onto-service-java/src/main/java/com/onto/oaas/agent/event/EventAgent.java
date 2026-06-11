package com.onto.oaas.agent.event;

import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.enums.EventType;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;
import com.onto.oaas.service.idempotent.IdempotencyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Kafka 事件处理 Agent。
 *
 * <p>职责：接收 Kafka 消息，执行幂等校验，解析事件类型，转发给 SyncAgent 处理。</p>
 * <p>注意：本 Agent 不通过 AgentBus 订阅消息，只通过 {@link #dispatchKafkaEvent} 外部入口接收 Kafka 事件。</p>
 * <p>这样可以避免 SyncAgent 发布的 SYNC_CHECKPOINT 被本 Agent 误收。</p>
 */
@Slf4j
@Component
public class EventAgent {

    private final AgentBus agentBus;
    private final IdempotencyService idempotencyService;

    public EventAgent(AgentBus agentBus, IdempotencyService idempotencyService) {
        this.agentBus = agentBus;
        this.idempotencyService = idempotencyService;
    }

    /**
     * 供外部调用：将 Kafka 事件包装为 AgentMessage 并发布到总线。
     * 这是本 Agent 的唯一入口，不通过 AgentBus 订阅接收消息。
     */
    public void dispatchKafkaEvent(KafkaEventEnvelope<TBoxPayload> envelope) {
        String eventId = envelope.getEventId();
        if (eventId == null || eventId.isBlank()) {
            eventId = "auto-" + System.currentTimeMillis();
            log.warn("[EventAgent] eventId is null/blank, generated: {}", eventId);
        }
        String eventTypeStr = envelope.getEventType();
        TBoxPayload payload = envelope.getPayload();

        EventType eventType;
        try {
            eventType = EventType.valueOf(eventTypeStr);
        } catch (IllegalArgumentException | NullPointerException e) {
            log.error("[EventAgent] Unknown event type: {}, eventId={}", eventTypeStr, eventId);
            return;
        }

        // 1. 幂等校验
        if (idempotencyService.isProcessed(eventId)) {
            log.info("[EventAgent] Event already processed, skipping: {}", eventId);
            return;
        }

        // 2. 记录已接收
        idempotencyService.recordReceived(eventId, eventTypeStr, null, null, 0, 0L);

        log.info("[EventAgent] Processing event: eventId={}, type={}", eventId, eventType);

        // 3. 根据事件类型路由到 SyncAgent
        switch (eventType) {
            case DOMAIN_UPSERT, TYPE_UPSERT, PROPERTY_UPSERT,
                 RELATIONSHIP_UPSERT, FUNCTION_UPSERT, RULE_UPSERT -> {
                AgentMessage msg = AgentMessage.builder()
                        .correlationId(eventId)
                        .type(AgentMessageType.SYNC_INCREMENTAL_EVENT)
                        .fromAgent("EventAgent")
                        .build();
                msg.putPayload("eventType", eventTypeStr);
                msg.putPayload("payload", payload);
                agentBus.publish(msg);
            }
            case REBUILD_INDEX -> {
                AgentMessage msg = AgentMessage.builder()
                        .correlationId(eventId)
                        .type(AgentMessageType.INDEX_REBUILD)
                        .fromAgent("EventAgent")
                        .build();
                agentBus.publish(msg);
            }
            case FULL_SYNC_REQUIRED -> {
                AgentMessage msg = AgentMessage.builder()
                        .correlationId(eventId)
                        .type(AgentMessageType.SYNC_FULL_REQUEST)
                        .fromAgent("EventAgent")
                        .build();
                msg.putPayload("ontologyId", "default");
                msg.putPayload("ontologyVersion", "latest");
                agentBus.publish(msg);
            }
            case DELETE -> {
                AgentMessage msg = AgentMessage.builder()
                        .correlationId(eventId)
                        .type(AgentMessageType.SYNC_INCREMENTAL_EVENT)
                        .fromAgent("EventAgent")
                        .build();
                msg.putPayload("eventType", eventTypeStr);
                msg.putPayload("payload", payload);
                agentBus.publish(msg);
            }
            default -> log.warn("[EventAgent] Unhandled event type: {}", eventType);
        }
    }
}
