package com.onto.service.query;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 查询结果
 */
@Data
public class QueryResult {

    /**
     * 结果列名
     */
    private List<String> columns;

    /**
     * 结果行数据
     */
    private List<Map<String, Object>> rows;

    /**
     * 总行数
     */
    private Long totalCount;

    /**
     * 执行的 Doris SQL
     */
    private String executedSql;

    /**
     * 查询耗时 (ms)
     */
    private Long executionTimeMs;

    /**
     * 是否包含推理事实
     */
    private Boolean containsDerivedFacts;
}
