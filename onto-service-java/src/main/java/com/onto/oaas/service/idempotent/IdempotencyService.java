package com.onto.oaas.service.idempotent;

import com.onto.oaas.model.EventProcessRecord;
import com.onto.oaas.model.enums.EventProcessStatus;
import com.onto.oaas.model.enums.EventType;
import com.onto.oaas.repository.mybatis.EventProcessRecordMapper;
import java.time.Instant;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
@ConditionalOnBean(EventProcessRecordMapper.class)
public class IdempotencyService {

    private final EventProcessRecordMapper mapper;

    public boolean isProcessed(String eventId) {
        EventProcessRecord record = mapper.findByEventId(eventId);
        return record != null && record.getGraphStatus() == EventProcessStatus.SUCCESS;
    }

    public void recordReceived(String eventId, String eventType, String objectPath, String topic, int partition, long offset) {
        EventProcessRecord record = EventProcessRecord.builder()
                .eventId(eventId)
                .eventType(parseEventType(eventType))
                .objectPath(objectPath)
                .graphStatus(EventProcessStatus.PENDING)
                .indexStatus(EventProcessStatus.PENDING)
                .retryCount(0)
                .kafkaTopic(topic)
                .kafkaPartition(partition)
                .kafkaOffset(offset)
                .createdTime(Instant.now())
                .updatedTime(Instant.now())
                .build();
        mapper.insert(record);
        log.debug("Recorded event received: {}", eventId);
    }

    public void recordGraphSuccess(String eventId) {
        int updated = mapper.updateStatus(eventId, EventProcessStatus.SUCCESS);
        if (updated > 0) {
            log.debug("Recorded graph success for event: {}", eventId);
        }
    }

    public void recordGraphFailed(String eventId, String error) {
        EventProcessRecord record = mapper.findByEventId(eventId);
        if (record != null) {
            record.setGraphStatus(EventProcessStatus.FAILED);
            record.setLastError(error);
            record.setUpdatedTime(Instant.now());
            mapper.updateById(record);
        }
        log.warn("Recorded graph failed for event: {}, error: {}", eventId, error);
    }

    public void recordIndexSuccess(String eventId) {
        EventProcessRecord record = mapper.findByEventId(eventId);
        if (record != null) {
            record.setIndexStatus(EventProcessStatus.SUCCESS);
            record.setUpdatedTime(Instant.now());
            mapper.updateById(record);
        }
        log.debug("Recorded index success for event: {}", eventId);
    }

    public void recordIndexFailed(String eventId, String error) {
        EventProcessRecord record = mapper.findByEventId(eventId);
        if (record != null) {
            record.setIndexStatus(EventProcessStatus.FAILED);
            record.setLastError(error);
            record.setUpdatedTime(Instant.now());
            mapper.updateById(record);
        }
        log.warn("Recorded index failed for event: {}, error: {}", eventId, error);
    }

    protected EventType parseEventType(String eventType) {
        try {
            return EventType.valueOf(eventType);
        } catch (IllegalArgumentException | NullPointerException e) {
            return null;
        }
    }
}
