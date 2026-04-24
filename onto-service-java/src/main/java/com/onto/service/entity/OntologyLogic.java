package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Logic 规则定义实体
 * 对应表: ontology_logic
 */
@Data
@TableName("ontology_logic")
public class OntologyLogic {

    private String domainName;
    private String version;
    private String logicName;
    private String targetType;
    private String targetProperty;
    private String logicKind;
    private String implementationType;
    private String expressionSql;
    private String udfName;
    private String pythonEntrypoint;
    private String serviceEndpoint;
    private Boolean deterministic;
    private String executionModeHint;
    private String externalBindingName;
    private String outputType;
    private String aiContext;
}
