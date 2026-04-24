package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 推理事实实体 (ABOX Derived Facts)
 * 对应表: semantic_fact
 */
@Data
@TableName("semantic_fact")
public class SemanticFact {

    private String domainName;
    private String version;
    private String objectType;
    private String objectId;
    private String propertyName;
    private String valueType;
    private String valueString;
    private Double valueNumber;
    private Boolean valueBool;
    private String valueJson;
    private String computedByLogic;
    private LocalDateTime computedAt;
    private LocalDateTime validFrom;
    private LocalDateTime validTo;
    private String evidenceJson;
    private String provenanceJson;
}
