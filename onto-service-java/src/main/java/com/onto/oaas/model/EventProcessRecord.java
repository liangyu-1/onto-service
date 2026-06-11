package com.onto.oaas.model;

import com.onto.oaas.model.enums.EventProcessStatus;
import com.onto.oaas.model.enums.EventType;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EventProcessRecord {
    private String eventId;
    private EventType eventType;
    private String objectPath;
    private EventProcessStatus graphStatus;
    private EventProcessStatus indexStatus;
    private int retryCount;
    private String lastError;
    private String kafkaTopic;
    private int kafkaPartition;
    private long kafkaOffset;
    private Instant createdTime;
    private Instant updatedTime;
}
