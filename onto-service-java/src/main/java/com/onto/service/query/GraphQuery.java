package com.onto.service.query;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 图查询请求 (Property Graph MATCH 语句)
 */
@Data
public class GraphQuery {

    /**
     * MATCH 模式，例如: (p:ICSProcess)-[:HAS_POINT]->(pt:SCADAPoint)
     */
    private String matchPattern;

    /**
     * WHERE 条件
     */
    private String whereClause;

    /**
     * RETURN 表达式
     */
    private List<String> returnExpressions;

    /**
     * 参数绑定
     */
    private Map<String, Object> parameters;

    /**
     * 排序和分页
     */
    private String orderByClause;
    private Integer limit;
}
