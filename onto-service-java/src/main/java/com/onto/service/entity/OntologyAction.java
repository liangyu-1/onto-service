package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Action 定义实体
 * 对应表: ontology_action
 */
@Data
@TableName("ontology_action")
public class OntologyAction {

    private String domainName;
    private String version;
    private String actionName;
    private String toolName;
    private String targetType;
    private String inputSchemaJson;
    private String outputSchemaJson;
    private String preconditionSql;
    private String preconditionLogic;
    private String externalPlatform;
    private String externalActionRef;
    private String invocationMode;
    private Boolean dryRunRequired;
    private String aiContext;
}
