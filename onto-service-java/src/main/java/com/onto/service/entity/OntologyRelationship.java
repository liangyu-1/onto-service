package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 关系定义实体
 * 对应表: ontology_relationship
 */
@Data
@TableName("ontology_relationship")
public class OntologyRelationship {

    private String domainName;
    private String version;
    private String labelName;
    private String edgeTable;
    private String sourceLabel;
    private String targetLabel;
    private String sourceKey;
    private String targetKey;
    private String outgoingName;
    private String incomingName;
    private Boolean outgoingIsMulti;
    private Boolean incomingIsMulti;
    private String cardinality;
    private String aiContext;
}
