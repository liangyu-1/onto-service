package com.onto.service.semantic;

import com.baomidou.mybatisplus.extension.service.IService;
import com.onto.service.entity.OntologyObjectType;

import java.util.List;

/**
 * 节点类型/对象类型服务接口
 */
public interface OntologyObjectTypeService extends IService<OntologyObjectType> {

    /**
     * 创建对象类型
     */
    OntologyObjectType createObjectType(OntologyObjectType objectType);

    /**
     * 获取域下的所有对象类型
     */
    List<OntologyObjectType> getObjectTypes(String domainName, String version);

    /**
     * 获取指定对象类型
     */
    OntologyObjectType getObjectType(String domainName, String version, String labelName);

    /**
     * 获取子类型列表
     */
    List<OntologyObjectType> getChildTypes(String domainName, String version, String parentLabel);
}
