package com.onto.service.query;

import lombok.Data;

import java.util.Map;

/**
 * 逻辑查询请求
 * 用于查询推理事实 (Derived Facts)
 */
@Data
public class LogicQuery {

    /**
     * 目标 Logic 名称
     */
    private String logicName;

    /**
     * 目标对象类型
     */
    private String targetType;

    /**
     * 目标对象 ID (可选，为空则查询所有实例)
     */
    private String targetObjectId;

    /**
     * 目标属性
     */
    private String targetProperty;

    /**
     * 时间范围
     */
    private String timeRange;

    /**
     * 附加参数
     */
    private Map<String, Object> parameters;
}
