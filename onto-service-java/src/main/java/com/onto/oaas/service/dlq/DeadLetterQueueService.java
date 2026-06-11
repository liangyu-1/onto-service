package com.onto.oaas.service.dlq;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.DlqRecord;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class DeadLetterQueueService {
    private final Map<String, DlqRecord> store = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper;

    public void sendToDlq(KafkaEventEnvelope<TBoxPayload> envelope, String errorReason, String errorCode) {
        try {
            DlqRecord record = DlqRecord.builder()
                .dlqRecordId(UUID.randomUUID().toString())
                .originalEventId(envelope.getEventId())
                .eventType(envelope.getEventType() != null ? envelope.getEventType().toString() : null)
                .rawPayload(objectMapper.writeValueAsString(envelope))
                .errorReason(errorReason)
                .errorCode(errorCode)
                .status("PENDING")
                .createdTime(Instant.now())
                .build();
            store.put(record.getDlqRecordId(), record);
            log.warn("Message sent to DLQ: eventId={}, reason={}", envelope.getEventId(), errorReason);
        } catch (Exception e) {
            log.error("Failed to send message to DLQ: eventId={}", envelope.getEventId(), e);
        }
    }

    public void sendToDlq(String eventId, String eventType, String rawPayload, String errorReason, String errorCode) {
        DlqRecord record = DlqRecord.builder()
            .dlqRecordId(UUID.randomUUID().toString())
            .originalEventId(eventId)
            .eventType(eventType)
            .rawPayload(rawPayload)
            .errorReason(errorReason)
            .errorCode(errorCode)
            .status("PENDING")
            .createdTime(Instant.now())
            .build();
        store.put(record.getDlqRecordId(), record);
        log.warn("Message sent to DLQ: eventId={}, reason={}", eventId, errorReason);
    }

    public List<DlqRecord> queryDlq(String eventType, String errorType, int limit) {
        return store.values().stream()
            .filter(r -> eventType == null || eventType.equals(r.getEventType()))
            .filter(r -> errorType == null || errorType.equals(r.getErrorCode()))
            .limit(limit)
            .collect(Collectors.toList());
    }

    public void replayDlq(String dlqRecordId) {
        DlqRecord record = store.get(dlqRecordId);
        if (record != null) {
            record.setStatus("REPLAYED");
            record.setUpdatedTime(Instant.now());
        }
    }

    public void archiveDlq(String dlqRecordId) {
        DlqRecord record = store.get(dlqRecordId);
        if (record != null) {
            record.setStatus("ARCHIVED");
            record.setUpdatedTime(Instant.now());
        }
    }
}
