package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 节点类型/对象类型实体
 * 对应表: ontology_object_type
 */
@Data
@TableName("ontology_object_type")
public class OntologyObjectType {

    @TableId
    private String domainName;
    private String version;
    private String labelName;
    private String parentLabel;
    private String displayName;
    private String description;
    private String aiContext;
}
