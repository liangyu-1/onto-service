package com.onto.oaas.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DlqRecord {
    private String dlqRecordId;
    private String originalEventId;
    private String eventType;
    private String rawPayload;
    private String errorReason;
    private String errorCode;
    private String status;
    private Instant createdTime;
    private Instant updatedTime;
}
