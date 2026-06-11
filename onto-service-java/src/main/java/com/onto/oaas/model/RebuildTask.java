package com.onto.oaas.model;

import com.onto.oaas.model.enums.RebuildScope;
import com.onto.oaas.model.enums.RebuildStatus;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RebuildTask {
    private String taskId;
    private RebuildScope scope;
    private TBoxObjectType objectType;
    private RebuildStatus status;
    private long totalCount;
    private long processedCount;
    private long failedCount;
    private Instant createdTime;
    private Instant startedTime;
    private Instant completedTime;
    private String errorMessage;
}
