package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 本体域/图定义实体
 * 对应表: ontology_domain
 */
@Data
@TableName("ontology_domain")
public class OntologyDomain {

    @TableId(type = IdType.INPUT)
    private String id;

    private String domainName;

    private String version;

    private String ddlSql;
    private String status;
    private LocalDateTime createdAt;
    private String createdBy;
    private String ddlHash;
}
