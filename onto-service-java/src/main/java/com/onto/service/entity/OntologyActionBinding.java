package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Action 外部绑定实体
 * 对应表: ontology_action_binding
 */
@Data
@TableName("ontology_action_binding")
public class OntologyActionBinding {

    private String domainName;
    private String version;
    private String actionName;
    private String platformName;
    private String platformActionRef;
    private String dryRunRef;
    private String resultRef;
    private String observabilityRef;
    private Boolean enabled;
}
