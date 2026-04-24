package com.onto.service.query.impl;

import com.onto.service.entity.*;
import com.onto.service.exception.OntologyException;
import com.onto.service.mapper.*;
import com.onto.service.query.*;
import com.onto.service.tbox.neo4j.TboxNeo4jService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * 查询适配器实现
 */
@Slf4j
@Service
public class QueryAdapterImpl implements QueryAdapter {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private TboxNeo4jService tbox;

    @Autowired
    private OntologyLogicMapper logicMapper;

    @Autowired
    private SemanticFactMapper factMapper;

    @Autowired
    private OntologyLogicExplanationMapper explanationMapper;

    @Override
    public QueryResult executeSemanticQuery(String domainName, String version, SemanticQuery query) {
        long startTime = System.currentTimeMillis();

        // 1. 解析语义查询为 ResolvedSemanticPlan
        ResolvedSemanticPlan plan = resolveSemanticPlan(domainName, version, query);

        // 2. 生成 Doris SQL
        String dorisSql = generateDorisSql(domainName, version, plan);

        // 3. 执行查询
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(dorisSql);

        // 4. 组装结果
        QueryResult result = new QueryResult();
        result.setColumns(plan.getColumnProjections() != null ? new ArrayList<>(plan.getColumnProjections().keySet()) : Collections.emptyList());
        result.setRows(rows);
        result.setTotalCount((long) rows.size());
        result.setExecutedSql(dorisSql);
        result.setExecutionTimeMs(System.currentTimeMillis() - startTime);
        result.setContainsDerivedFacts(false);

        return result;
    }

    @Override
    public QueryResult executeGraphQuery(String domainName, String version, GraphQuery query) {
        // 将 Graph MATCH 转换为语义查询，再执行
        SemanticQuery semanticQuery = convertGraphToSemantic(domainName, version, query);
        return executeSemanticQuery(domainName, version, semanticQuery);
    }

    @Override
    public QueryResult executeLogicQuery(String domainName, String version, LogicQuery query) {
        long startTime = System.currentTimeMillis();

        // 查询推理事实表
        List<SemanticFact> facts;
        if (query.getTargetObjectId() != null) {
            facts = factMapper.selectByObject(domainName, version, query.getTargetType(), query.getTargetObjectId());
        } else {
            facts = factMapper.selectByLogicName(domainName, version, query.getLogicName());
        }

        // 转换为 QueryResult
        List<Map<String, Object>> rows = new ArrayList<>();
        for (SemanticFact fact : facts) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("object_type", fact.getObjectType());
            row.put("object_id", fact.getObjectId());
            row.put("property_name", fact.getPropertyName());
            row.put("value", extractValue(fact));
            row.put("computed_at", fact.getComputedAt());
            row.put("evidence", fact.getEvidenceJson());
            rows.add(row);
        }

        QueryResult result = new QueryResult();
        result.setColumns(Arrays.asList("object_type", "object_id", "property_name", "value", "computed_at", "evidence"));
        result.setRows(rows);
        result.setTotalCount((long) rows.size());
        result.setExecutionTimeMs(System.currentTimeMillis() - startTime);
        result.setContainsDerivedFacts(true);

        return result;
    }

    @Override
    public Explanation explainQuery(String domainName, String version, SemanticQuery query) {
        Explanation explanation = new Explanation();

        // 1. 获取涉及的 Logic 规则
        List<String> involvedLogics = new ArrayList<>();
        if (query.getSelectProperties() != null) {
            for (String prop : query.getSelectProperties()) {
                // 检查是否是推理属性
                List<OntologyLogic> logics = logicMapper.selectByTargetType(domainName, version, query.getTargetType());
                for (OntologyLogic logic : logics) {
                    if (prop.equals(logic.getTargetProperty())) {
                        involvedLogics.add(logic.getLogicName());
                    }
                }
            }
        }
        explanation.setInvolvedLogicRules(involvedLogics);

        // 2. 生成自然语言解释
        StringBuilder nlText = new StringBuilder();
        nlText.append("查询目标: ").append(query.getTargetType()).append("\n");
        if (query.getSelectProperties() != null) {
            nlText.append("查询属性: ").append(String.join(", ", query.getSelectProperties())).append("\n");
        }
        if (!involvedLogics.isEmpty()) {
            nlText.append("涉及推理规则: ").append(String.join(", ", involvedLogics));
        }
        explanation.setNaturalLanguageText(nlText.toString());

        // 3. 数据来源
        List<String> sources = new ArrayList<>();
        OntologyObjectAboxMapping mapping = tbox.listAboxMappings(domainName, version).stream()
                .filter(m -> query.getTargetType() != null && query.getTargetType().equals(m.getClassName()))
                .findFirst()
                .orElse(null);
        if (mapping != null) {
            sources.add(mapping.getObjectSourceName());
        }
        explanation.setDataSources(sources);

        return explanation;
    }

    @Override
    public String getExplanationTemplate(String domainName, String version, String logicName, String language) {
        OntologyLogicExplanation explanation = explanationMapper.selectByLogicAndLanguage(domainName, version, logicName, language);
        return explanation != null ? explanation.getTemplateText() : null;
    }

    @Override
    public String generateDorisSql(String domainName, String version, ResolvedSemanticPlan plan) {
        StringBuilder sql = new StringBuilder();

        // SELECT
        sql.append("SELECT ");
        if (plan.getColumnProjections() != null && !plan.getColumnProjections().isEmpty()) {
            List<String> projections = new ArrayList<>();
            for (Map.Entry<String, String> entry : plan.getColumnProjections().entrySet()) {
                projections.add(entry.getValue() + " AS " + entry.getKey());
            }
            sql.append(String.join(", ", projections));
        } else {
            sql.append("*");
        }

        // FROM
        sql.append(" FROM ");
        if (plan.getSourceTables() != null && !plan.getSourceTables().isEmpty()) {
            sql.append(plan.getSourceTables().get(0));
        }

        // JOINs
        if (plan.getJoins() != null) {
            for (ResolvedSemanticPlan.JoinCondition join : plan.getJoins()) {
                sql.append(" ").append(join.getJoinType()).append(" JOIN ")
                   .append(join.getRightTable())
                   .append(" ON ").append(join.getLeftTable()).append(".")
                   .append(join.getLeftColumn()).append(" = ")
                   .append(join.getRightTable()).append(".")
                   .append(join.getRightColumn());
            }
        }

        // WHERE
        if (plan.getWhereClause() != null && !plan.getWhereClause().isEmpty()) {
            sql.append(" WHERE ").append(plan.getWhereClause());
        }

        // GROUP BY
        if (plan.getGroupBy() != null && !plan.getGroupBy().isEmpty()) {
            sql.append(" GROUP BY ").append(String.join(", ", plan.getGroupBy()));
        }

        // ORDER BY
        if (plan.getOrderBy() != null && !plan.getOrderBy().isEmpty()) {
            sql.append(" ORDER BY ").append(String.join(", ", plan.getOrderBy()));
        }

        // LIMIT
        if (plan.getLimit() != null) {
            sql.append(" LIMIT ").append(plan.getLimit());
        }

        return sql.toString();
    }

    /**
     * 解析语义查询为执行计划
     */
    private ResolvedSemanticPlan resolveSemanticPlan(String domainName, String version, SemanticQuery query) {
        ResolvedSemanticPlan plan = new ResolvedSemanticPlan();
        plan.setQueryType(query.getIntent());

        // 1. 确定数据源
        List<String> sources = new ArrayList<>();
        OntologyObjectAboxMapping mapping = tbox.listAboxMappings(domainName, version).stream()
                .filter(m -> query.getTargetType() != null && query.getTargetType().equals(m.getClassName()))
                .findFirst()
                .orElse(null);
        if (mapping == null || mapping.getObjectSourceName() == null || mapping.getObjectSourceName().trim().isEmpty()) {
            throw new OntologyException("Missing ABOX mapping for targetType=" + query.getTargetType()
                    + ". Please create TBOX/ABOX mapping first (objectSourceName/primaryKey).");
        }
        sources.add(mapping.getObjectSourceName().trim());
        plan.setSourceTables(sources);

        // 2. 解析属性投影
        Map<String, String> projections = new LinkedHashMap<>();
        if (query.getSelectProperties() != null) {
            for (String propName : query.getSelectProperties()) {
                OntologyProperty property = tbox.listProperties(domainName, version, query.getTargetType()).stream()
                        .filter(p -> propName.equals(p.getPropertyName()))
                        .findFirst()
                        .orElse(null);
                if (property != null) {
                    String physicalCol = property.getColumnName() != null ? property.getColumnName() : property.getExpressionSql();
                    projections.put(propName, physicalCol != null ? physicalCol : propName);
                } else {
                    projections.put(propName, propName);
                }
            }
        }
        plan.setColumnProjections(projections);

        // 3. 解析关系导航 (JOIN)
        List<ResolvedSemanticPlan.JoinCondition> joins = new ArrayList<>();
        if (query.getRelationPath() != null) {
            String currentType = query.getTargetType();
            for (String nav : query.getRelationPath()) {
                // 查找关系定义
                String ct = currentType;
                List<OntologyRelationship> rels = tbox.listRelationships(domainName, version).stream()
                        .filter(r -> ct != null && ct.equals(r.getSourceLabel()))
                        .toList();
                for (OntologyRelationship rel : rels) {
                    if (nav.equals(rel.getOutgoingName()) || nav.equals(rel.getLabelName())) {
                        OntologyObjectAboxMapping targetMapping = tbox.listAboxMappings(domainName, version).stream()
                                .filter(m -> rel.getTargetLabel() != null && rel.getTargetLabel().equals(m.getClassName()))
                                .findFirst()
                                .orElse(null);
                        if (targetMapping != null && mapping != null) {
                            ResolvedSemanticPlan.JoinCondition join = new ResolvedSemanticPlan.JoinCondition();
                            join.setJoinType("LEFT");
                            join.setLeftTable(mapping.getObjectSourceName());
                            join.setRightTable(targetMapping.getObjectSourceName());
                            join.setLeftColumn(rel.getSourceKey());
                            join.setRightColumn(rel.getTargetKey());
                            join.setRelationLabel(rel.getLabelName());
                            joins.add(join);

                            // 更新当前类型为下一个导航起点
                            currentType = rel.getTargetLabel();
                            mapping = targetMapping;
                        }
                        break;
                    }
                }
            }
        }
        plan.setJoins(joins);

        // 4. 构建 WHERE 条件
        StringBuilder whereClause = new StringBuilder();
        if (query.getFilters() != null) {
            List<String> conditions = new ArrayList<>();
            for (Map.Entry<String, Object> filter : query.getFilters().entrySet()) {
                OntologyProperty prop = tbox.listProperties(domainName, version, query.getTargetType()).stream()
                        .filter(p -> filter.getKey().equals(p.getPropertyName()))
                        .findFirst()
                        .orElse(null);
                String colName = prop != null && prop.getColumnName() != null ? prop.getColumnName() : filter.getKey();
                Object value = filter.getValue();
                if (value instanceof String) {
                    conditions.add(colName + " = '" + value + "'");
                } else {
                    conditions.add(colName + " = " + value);
                }
            }
            whereClause.append(String.join(" AND ", conditions));
        }
        plan.setWhereClause(whereClause.toString());

        // 5. 分页
        plan.setLimit(query.getLimit());
        plan.setOffset(query.getOffset());

        return plan;
    }

    /**
     * 将 GraphQuery 转换为 SemanticQuery
     */
    private SemanticQuery convertGraphToSemantic(String domainName, String version, GraphQuery graphQuery) {
        SemanticQuery semanticQuery = new SemanticQuery();
        semanticQuery.setIntent("select");

        // 解析 MATCH 模式提取目标类型
        // 简化实现：从模式中提取第一个节点标签
        String pattern = graphQuery.getMatchPattern();
        if (pattern.contains(":")) {
            int colonIdx = pattern.indexOf(':');
            int closeIdx = pattern.indexOf(')', colonIdx);
            if (closeIdx > colonIdx) {
                String label = pattern.substring(colonIdx + 1, closeIdx).trim();
                semanticQuery.setTargetType(label);
            }
        }

        semanticQuery.setSelectProperties(graphQuery.getReturnExpressions());
        // WHERE 条件简化处理
        if (graphQuery.getWhereClause() != null) {
            // 解析 WHERE 为 filters (简化)
        }
        semanticQuery.setLimit(graphQuery.getLimit());

        return semanticQuery;
    }

    private Object extractValue(SemanticFact fact) {
        if (fact.getValueString() != null) return fact.getValueString();
        if (fact.getValueNumber() != null) return fact.getValueNumber();
        if (fact.getValueBool() != null) return fact.getValueBool();
        if (fact.getValueJson() != null) return fact.getValueJson();
        return null;
    }
}
