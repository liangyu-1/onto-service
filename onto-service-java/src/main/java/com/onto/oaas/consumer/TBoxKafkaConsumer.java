package com.onto.oaas.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;
import com.onto.oaas.agent.event.EventAgent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

/**
 * TBox Kafka 消费者。
 *
 * <p>支持两种消息格式：</p>
 * <ul>
 *   <li><b>Wrapped 格式</b>（本体管理平台）：{@code {eventId, eventType, payload: {timestamp, domains, code, message}}}</li>
 *   <li><b>Direct 格式</b>（旧格式）：{@code {timestamp, domains, code, message}}</li>
 * </ul>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TBoxKafkaConsumer {

    private static final String EXPECTED_SCHEMA_VERSION = "1.0";

    private final ObjectMapper objectMapper;
    private final EventAgent eventAgent;

    @KafkaListener(topics = "${oaas.kafka.topic:ontology-events}", groupId = "${oaas.kafka.consumer.group-id:oaas-consumer-group}", autoStartup = "${oaas.full-sync.auto-on-startup:false}")
    public void consume(ConsumerRecord<String, String> record, Acknowledgment ack) {
        String value = record.value();
        log.debug("Received Kafka record, topic={}, partition={}, offset={}, key={}",
                record.topic(), record.partition(), record.offset(), record.key());

        try {
            // 1. parse JSON
            KafkaEventEnvelope<TBoxPayload> envelope = parseEnvelope(value);

            // 2. validate schema version
            if (envelope.getSchemaVersion() != null && !envelope.getSchemaVersion().equals(EXPECTED_SCHEMA_VERSION)) {
                log.warn("Schema version mismatch, expected={}, actual={}", EXPECTED_SCHEMA_VERSION, envelope.getSchemaVersion());
            }

            // 3. dispatch via EventAgent
            eventAgent.dispatchKafkaEvent(envelope);

            // 4. ack
            ack.acknowledge();
            log.debug("Acknowledged record, offset={}", record.offset());
        } catch (Exception e) {
            log.error("Failed to process Kafka record, offset={}", record.offset(), e);
            // Do not acknowledge; rely on retry / DLQ policy configured in Spring Kafka
        }
    }

    /**
     * 解析 Kafka 消息，自动识别 Wrapped 格式和 Direct 格式。
     */
    private KafkaEventEnvelope<TBoxPayload> parseEnvelope(String value) throws Exception {
        JsonNode rootNode = objectMapper.readTree(value);

        // 判断是否为 Wrapped 格式（有 payload 字段）
        if (rootNode.has("payload") && rootNode.get("payload").isObject()) {
            // Wrapped 格式：直接解析
            return objectMapper.readValue(
                    value,
                    objectMapper.getTypeFactory().constructParametricType(KafkaEventEnvelope.class, TBoxPayload.class));
        }

        // Direct 格式：将根节点作为 payload 包装
        if (rootNode.has("domains") || rootNode.has("timestamp")) {
            TBoxPayload payload = objectMapper.readValue(value, TBoxPayload.class);
            return KafkaEventEnvelope.<TBoxPayload>builder()
                    .eventId("direct-" + System.currentTimeMillis())
                    .eventType("FULL_SYNC_REQUIRED")
                    .payload(payload)
                    .build();
        }

        // 尝试直接解析（可能是其他格式）
        return objectMapper.readValue(
                value,
                objectMapper.getTypeFactory().constructParametricType(KafkaEventEnvelope.class, TBoxPayload.class));
    }
}
