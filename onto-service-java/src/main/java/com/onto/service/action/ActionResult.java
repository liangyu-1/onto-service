package com.onto.service.action;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Action 执行结果
 */
@Data
public class ActionResult {

    private String actionId;
    private String status; // pending / submitted / running / success / failed / cancelled
    private String precheckResultJson;
    private String externalRequestRef;
    private String externalResultJson;
    private String requestedBy;
    private String requestedByAgent;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String errorMessage;
}
