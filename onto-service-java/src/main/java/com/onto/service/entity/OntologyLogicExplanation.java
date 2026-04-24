package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Logic 解释模板实体
 * 对应表: ontology_logic_explanation
 */
@Data
@TableName("ontology_logic_explanation")
public class OntologyLogicExplanation {

    private String domainName;
    private String version;
    private String logicName;
    private String language;
    private String templateText;
    private String evidenceSchemaJson;
    private String aiContext;
}
