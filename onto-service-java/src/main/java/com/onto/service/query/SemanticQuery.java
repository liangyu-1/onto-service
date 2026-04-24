package com.onto.service.query;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 语义查询请求
 */
@Data
public class SemanticQuery {

    /**
     * 查询意图: select / insert / update / delete / aggregate
     */
    private String intent;

    /**
     * 目标对象类型
     */
    private String targetType;

    /**
     * 选择的属性列表
     */
    private List<String> selectProperties;

    /**
     * 过滤条件 (属性名 -> 条件值)
     */
    private Map<String, Object> filters;

    /**
     * 关系导航路径
     */
    private List<String> relationPath;

    /**
     * 排序条件
     */
    private List<OrderBy> orderBy;

    /**
     * 分页限制
     */
    private Integer limit;
    private Integer offset;

    @Data
    public static class OrderBy {
        private String property;
        private String direction; // ASC / DESC
    }
}
