package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * Logic 运行记录实体
 * 对应表: semantic_logic_run
 */
@Data
@TableName("semantic_logic_run")
public class SemanticLogicRun {

    private String runId;
    private String domainName;
    private String version;
    private String logicName;
    private String executionModeHint;
    private String externalPlatform;
    private String externalJobRef;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private String status;
    private Integer inputCount;
    private Integer outputCount;
    private String errorMessage;
    private String metricsJson;
}
