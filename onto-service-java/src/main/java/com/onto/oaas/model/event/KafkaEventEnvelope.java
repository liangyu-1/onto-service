package com.onto.oaas.model.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Kafka 事件信封。
 *
 * <p>支持两种消息格式：</p>
 * <ul>
 *   <li><b>Wrapped 格式</b>（本体管理平台）：{@code {eventId, eventSequence, eventType, payload: {...}}}</li>
 *   <li><b>Direct 格式</b>（旧格式/测试）：{@code {timestamp, domains, code, message}}</li>
 * </ul>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class KafkaEventEnvelope<T> {

    // ===== Wrapped 格式字段 (本体管理平台使用驼峰命名) =====

    @JsonProperty("eventId")
    private String eventId;

    @JsonProperty("eventSequence")
    private String eventSequence;

    @JsonProperty("eventType")
    private String eventType;

    @JsonProperty("schemaVersion")
    private String schemaVersion;

    @JsonProperty("publishTime")
    private Instant publishTime;

    @JsonProperty("payload")
    private T payload;

    // ===== Direct 格式字段 (无包装层，直接是 payload 内容) =====

    /** 直接格式的时间戳（当没有 payload 包装时使用）。 */
    @JsonProperty("timestamp")
    private String timestamp;

    /** 直接格式的响应码。 */
    @JsonProperty("code")
    private String code;

    /** 直接格式的响应消息。 */
    @JsonProperty("message")
    private String message;

    // ===== 兼容旧版 snake_case 格式 =====

    @JsonProperty(value = "event_type", access = JsonProperty.Access.WRITE_ONLY)
    private String eventTypeSnake;

    @JsonProperty(value = "event_id", access = JsonProperty.Access.WRITE_ONLY)
    private String eventIdSnake;

    @JsonProperty(value = "event_sequence", access = JsonProperty.Access.WRITE_ONLY)
    private Long eventSequenceSnake;

    @JsonProperty(value = "schema_version", access = JsonProperty.Access.WRITE_ONLY)
    private String schemaVersionSnake;

    @JsonProperty(value = "publish_time", access = JsonProperty.Access.WRITE_ONLY)
    private Instant publishTimeSnake;

    /**
     * 获取事件类型，兼容驼峰和 snake_case。
     */
    public String getEventType() {
        if (eventType != null) return eventType;
        if (eventTypeSnake != null) return eventTypeSnake;
        return null;
    }

    /**
     * 获取事件 ID，兼容驼峰和 snake_case。
     */
    public String getEventId() {
        if (eventId != null) return eventId;
        if (eventIdSnake != null) return eventIdSnake;
        return null;
    }

    /**
     * 获取事件序列号，兼容驼峰和 snake_case。
     */
    public String getEventSequence() {
        if (eventSequence != null) return eventSequence;
        if (eventSequenceSnake != null) return String.valueOf(eventSequenceSnake);
        return null;
    }

    /**
     * 获取 Schema 版本，兼容驼峰和 snake_case。
     */
    public String getSchemaVersion() {
        if (schemaVersion != null) return schemaVersion;
        if (schemaVersionSnake != null) return schemaVersionSnake;
        return null;
    }

    /**
     * 获取发布时间，兼容驼峰和 snake_case。
     */
    public Instant getPublishTime() {
        if (publishTime != null) return publishTime;
        if (publishTimeSnake != null) return publishTimeSnake;
        return null;
    }

    /**
     * 判断是否为 Wrapped 格式（有 payload 层）。
     */
    public boolean isWrappedFormat() {
        return payload != null;
    }

    /**
     * 判断是否为 Direct 格式（无 payload 层，直接是数据）。
     */
    public boolean isDirectFormat() {
        return payload == null && timestamp != null;
    }
}
