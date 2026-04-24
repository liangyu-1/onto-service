package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * Action 实例实体
 * 对应表: semantic_action_instance
 */
@Data
@TableName("semantic_action_instance")
public class SemanticActionInstance {

    private String actionId;
    private String domainName;
    private String version;
    private String actionName;
    private String toolName;
    private String targetType;
    private String targetObjectId;
    private String inputJson;
    private Boolean dryRun;
    private String status;
    private String precheckResultJson;
    private String externalRequestRef;
    private String externalResultJson;
    private String errorMessage;
    private String requestedBy;
    private String requestedByAgent;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
