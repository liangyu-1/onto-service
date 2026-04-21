package com.onto.service.logic;

import com.onto.service.entity.*;

import java.util.List;
import java.util.Map;

/**
 * Logic Registry 接口
 * 规则控制面，管理规则定义、依赖、外部绑定和解释模板
 */
public interface LogicRegistry {

    // ========== Logic 定义管理 ==========

    OntologyLogic createLogic(OntologyLogic logic);
    OntologyLogic updateLogic(String domainName, String version, String logicName, OntologyLogic logic);
    void deleteLogic(String domainName, String version, String logicName);
    OntologyLogic getLogic(String domainName, String version, String logicName);
    List<OntologyLogic> getLogicsByType(String domainName, String version, String logicKind);
    List<OntologyLogic> getLogicsByTarget(String domainName, String version, String targetType);

    // ========== 依赖管理 ==========

    void addDependency(OntologyLogicDependency dependency);
    void removeDependency(String domainName, String version, String logicName, String dependencyName);
    List<OntologyLogicDependency> getDependencies(String domainName, String version, String logicName);
    List<OntologyLogicDependency> getDependents(String domainName, String version, String dependencyName);

    /**
     * 获取依赖拓扑排序
     */
    List<String> getDependencyTopoOrder(String domainName, String version);

    // ========== 外部执行绑定 ==========

    void createExecutionBinding(OntologyLogicExecutionBinding binding);
    void updateExecutionBinding(OntologyLogicExecutionBinding binding);
    OntologyLogicExecutionBinding getExecutionBinding(String domainName, String version, String logicName, String platformName);
    List<OntologyLogicExecutionBinding> getExecutionBindings(String domainName, String version, String logicName);

    // ========== 解释模板 ==========

    void createExplanation(OntologyLogicExplanation explanation);
    OntologyLogicExplanation getExplanation(String domainName, String version, String logicName, String language);
    String renderExplanation(String domainName, String version, String logicName, String language, Map<String, Object> context);

    // ========== 推理事实管理 ==========

    SemanticFact getDerivedFact(String domainName, String version, String objectType, String objectId, String propertyName);
    List<SemanticFact> getDerivedFacts(String domainName, String version, String objectType, String objectId);
    List<SemanticFact> getDerivedFactsByLogic(String domainName, String version, String logicName);

    // ========== 规则执行 ==========

    /**
     * 执行 SQL 类型的 Logic (本地执行)
     */
    List<SemanticFact> executeSqlLogic(String domainName, String version, String logicName, Map<String, Object> params);

    /**
     * 触发外部 Logic 执行
     */
    String triggerExternalLogic(String domainName, String version, String logicName, String platformName);
}
