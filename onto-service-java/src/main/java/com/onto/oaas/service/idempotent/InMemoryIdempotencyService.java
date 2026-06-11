package com.onto.oaas.service.idempotent;

import com.onto.oaas.model.EventProcessRecord;
import com.onto.oaas.model.enums.EventProcessStatus;
import com.onto.oaas.model.enums.EventType;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Service;

/**
 * 内存模式幂等性服务。
 *
 * <p>当 Doris/MySQL 数据库不可用时，使用内存存储替代，支持 Kafka 消费链路测试。</p>
 * <p>注意：内存模式重启后数据丢失，仅用于开发和测试环境。</p>
 */
@Slf4j
@Service
@Primary
public class InMemoryIdempotencyService extends IdempotencyService {

    private final Map<String, EventProcessRecord> records = new ConcurrentHashMap<>();

    public InMemoryIdempotencyService() {
        super(null);
        log.info("InMemoryIdempotencyService initialized (no database required)");
    }

    @Override
    public boolean isProcessed(String eventId) {
        EventProcessRecord record = records.get(eventId);
        return record != null && record.getGraphStatus() == EventProcessStatus.SUCCESS;
    }

    @Override
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
        records.put(eventId, record);
        log.debug("Recorded event received: {}", eventId);
    }

    @Override
    public void recordGraphSuccess(String eventId) {
        EventProcessRecord record = records.get(eventId);
        if (record != null) {
            record.setGraphStatus(EventProcessStatus.SUCCESS);
            record.setUpdatedTime(Instant.now());
            log.debug("Recorded graph success for event: {}", eventId);
        }
    }

    @Override
    public void recordGraphFailed(String eventId, String error) {
        EventProcessRecord record = records.get(eventId);
        if (record != null) {
            record.setGraphStatus(EventProcessStatus.FAILED);
            record.setLastError(error);
            record.setUpdatedTime(Instant.now());
        }
        log.warn("Recorded graph failed for event: {}, error: {}", eventId, error);
    }

    @Override
    public void recordIndexSuccess(String eventId) {
        EventProcessRecord record = records.get(eventId);
        if (record != null) {
            record.setIndexStatus(EventProcessStatus.SUCCESS);
            record.setUpdatedTime(Instant.now());
            log.debug("Recorded index success for event: {}", eventId);
        }
    }

    @Override
    public void recordIndexFailed(String eventId, String error) {
        EventProcessRecord record = records.get(eventId);
        if (record != null) {
            record.setIndexStatus(EventProcessStatus.FAILED);
            record.setLastError(error);
            record.setUpdatedTime(Instant.now());
        }
        log.warn("Recorded index failed for event: {}, error: {}", eventId, error);
    }

    @Override
    protected EventType parseEventType(String eventType) {
        try {
            return EventType.valueOf(eventType);
        } catch (IllegalArgumentException | NullPointerException e) {
            return null;
        }
    }
}
