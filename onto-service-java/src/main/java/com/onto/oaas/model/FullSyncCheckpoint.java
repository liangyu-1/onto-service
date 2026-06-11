package com.onto.oaas.model;

import com.onto.oaas.model.enums.EventProcessStatus;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FullSyncCheckpoint {
    private String checkpointId;
    private String timestamp;
    private int domainCount;
    private int typeCount;
    private int propertyCount;
    private int relationshipCount;
    private int functionCount;
    private int ruleCount;
    private EventProcessStatus status;
    private Instant startedTime;
    private Instant completedTime;
    private String errorMessage;
}
