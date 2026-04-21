package com.onto.service.semantic;

import com.baomidou.mybatisplus.extension.service.IService;
import com.onto.service.entity.OntologyRelationship;

import java.util.List;

/**
 * 关系定义服务接口
 */
public interface OntologyRelationshipService extends IService<OntologyRelationship> {

    /**
     * 创建关系定义
     */
    OntologyRelationship createRelationship(OntologyRelationship relationship);

    /**
     * 获取域下的所有关系
     */
    List<OntologyRelationship> getRelationships(String domainName, String version);

    /**
     * 获取指定关系
     */
    OntologyRelationship getRelationship(String domainName, String version, String labelName);

    /**
     * 获取源类型的所有出边关系
     */
    List<OntologyRelationship> getOutgoingRelationships(String domainName, String version, String sourceLabel);

    /**
     * 获取目标类型的所有入边关系
     */
    List<OntologyRelationship> getIncomingRelationships(String domainName, String version, String targetLabel);
}
