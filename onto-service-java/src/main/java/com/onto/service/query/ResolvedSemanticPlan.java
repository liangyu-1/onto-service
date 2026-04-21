package com.onto.service.query;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 解析后的语义计划
 * 中间表示层，介于语义查询和物理 SQL 之间
 */
@Data
public class ResolvedSemanticPlan {

    /**
     * 查询类型
     */
    private String queryType;

    /**
     * 涉及的 ABOX 数据源
     */
    private List<String> sourceTables;

    /**
     * 列投影映射 (语义属性 -> 物理列/表达式)
     */
    private Map<String, String> columnProjections;

    /**
     * JOIN 条件 (用于关系导航)
     */
    private List<JoinCondition> joins;

    /**
     * WHERE 条件
     */
    private String whereClause;

    /**
     * 聚合表达式
     */
    private List<String> aggregations;

    /**
     * GROUP BY
     */
    private List<String> groupBy;

    /**
     * 排序
     */
    private List<String> orderBy;

    /**
     * 分页
     */
    private Integer limit;
    private Integer offset;

    @Data
    public static class JoinCondition {
        private String joinType; // INNER / LEFT
        private String leftTable;
        private String rightTable;
        private String leftColumn;
        private String rightColumn;
        private String relationLabel; // 关系名称，用于解释
    }
}
