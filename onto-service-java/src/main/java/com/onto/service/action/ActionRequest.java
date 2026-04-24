package com.onto.service.action;

import lombok.Data;

import java.util.Map;

/**
 * Action 执行请求
 */
@Data
public class ActionRequest {

    private String domainName;
    private String version;
    private String actionName;
    private String toolName;
    private String targetType;
    private String targetObjectId;
    private Map<String, Object> input;
    private Boolean dryRun;
    private String requestedBy;
    private String requestedByAgent;
}
