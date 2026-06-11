package com.onto.oaas.agent.core;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Agent 间传递的标准消息结构。
 * 所有 Agent 通过 AgentBus 收发此消息，实现完全解耦。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentMessage {

    /** 消息唯一 ID */
    @Builder.Default
    private String messageId = UUID.randomUUID().toString();

    /** 关联 ID：trace_id / query_id / event_id，用于串联整个处理链路 */
    private String correlationId;

    /** 消息类型，决定由哪个 Agent 处理 */
    private AgentMessageType type;

    /** 消息负载，具体数据结构由消息类型决定 */
    @Builder.Default
    private Map<String, Object> payload = new HashMap<>();

    /** 消息发送时间 */
    @Builder.Default
    private Instant timestamp = Instant.now();

    /** 发送方 Agent 名称 */
    private String fromAgent;

    /** 目标 Agent 名称（可选，为空时由总线广播） */
    private String toAgent;

    /**
     * 便捷方法：从 payload 中获取指定类型的值。
     */
    @SuppressWarnings("unchecked")
    public <T> T getPayload(String key, Class<T> clazz) {
        Object value = payload.get(key);
        if (value == null) {
            return null;
        }
        if (clazz.isInstance(value)) {
            return clazz.cast(value);
        }
        throw new ClassCastException("Payload key '" + key + "' expected " + clazz.getName() + " but got " + value.getClass().getName());
    }

    /**
     * 便捷方法：向 payload 中放入值。
     */
    public AgentMessage putPayload(String key, Object value) {
        if (this.payload == null) {
            this.payload = new HashMap<>();
        }
        this.payload.put(key, value);
        return this;
    }

    /**
     * 创建响应消息，保持相同的 correlationId。
     */
    public AgentMessage reply(AgentMessageType replyType) {
        return AgentMessage.builder()
                .correlationId(this.correlationId)
                .type(replyType)
                .fromAgent(null)
                .toAgent(null)
                .build();
    }

}
