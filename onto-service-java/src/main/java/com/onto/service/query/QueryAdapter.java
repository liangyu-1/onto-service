package com.onto.service.query;

import com.onto.service.entity.*;

import java.util.List;
import java.util.Map;

/**
 * 查询适配器接口
 * 负责将语义查询转换为 Doris 可执行的 SQL
 */
public interface QueryAdapter {

    /**
     * 执行语义查询
     * Semantic Query -> Resolved Semantic Plan -> Doris SQL -> ABOX rows
     */
    QueryResult executeSemanticQuery(String domainName, String version, SemanticQuery query);

    /**
     * 执行图查询 (MATCH 语句)
     */
    QueryResult executeGraphQuery(String domainName, String version, GraphQuery query);

    /**
     * 执行逻辑查询
     */
    QueryResult executeLogicQuery(String domainName, String version, LogicQuery query);

    /**
     * 解释查询结果
     */
    Explanation explainQuery(String domainName, String version, SemanticQuery query);

    /**
     * 获取解释模板
     */
    String getExplanationTemplate(String domainName, String version, String logicName, String language);

    /**
     * 生成 Doris SQL
     */
    String generateDorisSql(String domainName, String version, ResolvedSemanticPlan plan);
}
