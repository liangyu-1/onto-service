package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Logic 外部执行绑定实体
 * 对应表: ontology_logic_execution_binding
 */
@Data
@TableName("ontology_logic_execution_binding")
public class OntologyLogicExecutionBinding {

    private String domainName;
    private String version;
    private String logicName;
    private String platformName;
    private String platformJobRef;
    private String platformOutputRef;
    private String resultTable;
    private String executionModeHint;
    private String triggerRuleRef;
    private Boolean enabled;
    private String owner;
    private String observabilityRef;
}
