package com.onto.service.action;

import com.onto.service.entity.OntologyAction;
import com.onto.service.entity.SemanticActionInstance;

import java.util.List;
import java.util.Map;

/**
 * Action Gateway 接口
 * 动作控制面，管理 LLM tool contract、外部动作绑定和调用记录
 */
public interface ActionGateway {

    // ========== Tool 管理 ==========

    List<OntologyAction> listTools(String domainName, String version);
    OntologyAction getTool(String domainName, String version, String toolName);
    List<OntologyAction> getToolsByTargetType(String domainName, String version, String targetType);

    // ========== Action 执行 ==========

    /**
     * Dry-run: 只校验，不真正执行外部动作
     */
    DryRunResult dryRun(ActionRequest request);

    /**
     * Submit: 用户确认后，提交给外部平台
     */
    ActionResult submitAction(ActionRequest request);

    /**
     * 获取 Action 状态
     */
    ActionResult getActionStatus(String actionId);

    /**
     * 取消 Action
     */
    ActionResult cancelAction(String actionId);

    // ========== Action 记录 ==========

    List<SemanticActionInstance> listActionInstances(String domainName, Map<String, Object> filters);
    SemanticActionInstance getActionInstance(String actionId);

    // ========== 前置条件检查 ==========

    /**
     * 检查 Action 前置条件
     */
    PrecheckResult checkPreconditions(String domainName, String version, String actionName, String targetObjectId);
}
