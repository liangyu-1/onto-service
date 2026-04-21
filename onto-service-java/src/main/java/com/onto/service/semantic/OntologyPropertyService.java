package com.onto.service.semantic;

import com.baomidou.mybatisplus.extension.service.IService;
import com.onto.service.entity.OntologyProperty;

import java.util.List;

/**
 * 属性定义服务接口
 */
public interface OntologyPropertyService extends IService<OntologyProperty> {

    /**
     * 创建属性定义
     */
    OntologyProperty createProperty(OntologyProperty property);

    /**
     * 获取指定类型的所有属性
     */
    List<OntologyProperty> getPropertiesByOwner(String domainName, String version, String ownerLabel);

    /**
     * 获取指定属性
     */
    OntologyProperty getProperty(String domainName, String version, String ownerLabel, String propertyName);

    /**
     * 获取类型的可见属性（排除 hidden=true）
     */
    List<OntologyProperty> getVisibleProperties(String domainName, String version, String ownerLabel);
}
