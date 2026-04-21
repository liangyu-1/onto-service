package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * Object 到 ABOX 映射实体
 * 对应表: ontology_object_abox_mapping
 */
@Data
@TableName("ontology_object_abox_mapping")
public class OntologyObjectAboxMapping {

    private String domainName;
    private String version;
    private String className;
    private String parentClass;
    private String mappingStrategy;
    private String objectSourceName;
    private String sourceKind;
    private String primaryKey;
    private String discriminatorColumn;
    private String typeFilterSql;
    private String propertyProjectionJson;
    private String viewSql;
    private String materializationStrategy;
    private String aiContext;
}
