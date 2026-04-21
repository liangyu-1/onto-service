package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Logic 依赖实体
 * 对应表: ontology_logic_dependency
 */
@Data
@TableName("ontology_logic_dependency")
public class OntologyLogicDependency {

    private String domainName;
    private String version;
    private String logicName;
    private String dependencyKind;
    private String dependencyName;
    private String dependencyPath;
    private Boolean required;
    private String description;
}
