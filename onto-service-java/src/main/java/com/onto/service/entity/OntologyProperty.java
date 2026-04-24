package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.util.List;

/**
 * 属性定义实体
 * 对应表: ontology_property
 */
@Data
@TableName("ontology_property")
public class OntologyProperty {

    private String domainName;
    private String version;
    private String ownerLabel;
    private String propertyName;
    private String valueType;
    private String columnName;
    private String expressionSql;
    private Boolean isMeasure;
    private String semanticRole;
    private List<String> semanticAliases;
    private Boolean hidden;
    private String description;
    private String aiContext;
}
