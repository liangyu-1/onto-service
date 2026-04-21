package com.onto.service.semantic;

import com.baomidou.mybatisplus.extension.service.IService;
import com.onto.service.entity.OntologyDomain;

import java.util.List;

/**
 * 本体域/图定义服务接口
 */
public interface OntologyDomainService extends IService<OntologyDomain> {

    /**
     * 创建本体域
     */
    OntologyDomain createDomain(String domainName, String ddlSql, String createdBy);

    /**
     * 发布新版本
     */
    OntologyDomain publishVersion(String domainName, String ddlSql, String createdBy);

    /**
     * 获取指定版本的域定义
     */
    OntologyDomain getDomainVersion(String domainName, String version);

    /**
     * 获取域的所有版本
     */
    List<OntologyDomain> getDomainVersions(String domainName);

    /**
     * 获取已发布的最新版本
     */
    OntologyDomain getLatestPublishedVersion(String domainName);
}
