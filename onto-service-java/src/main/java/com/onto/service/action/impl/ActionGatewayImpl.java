package com.onto.service.action.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.onto.service.action.*;
import com.onto.service.entity.*;
import com.onto.service.exception.OntologyException;
import com.onto.service.logic.LogicRegistry;
import com.onto.service.mapper.*;
import com.onto.service.query.QueryAdapter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

/**
 * Action Gateway 实现
 */
@Slf4j
@Service
public class ActionGatewayImpl implements ActionGateway {

    @Autowired
    private OntologyActionMapper actionMapper;

    @Autowired
    private OntologyActionBindingMapper actionBindingMapper;

    @Autowired
    private SemanticActionInstanceMapper actionInstanceMapper;

    @Autowired
    private LogicRegistry logicRegistry;

    @Autowired
    private QueryAdapter queryAdapter;

    @Override
    public List<OntologyAction> listTools(String domainName, String version) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName).eq("version", version);
        return actionMapper.selectList(wrapper);
    }

    @Override
    public OntologyAction getTool(String domainName, String version, String toolName) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("tool_name", toolName);
        return actionMapper.selectOne(wrapper);
    }

    @Override
    public List<OntologyAction> getToolsByTargetType(String domainName, String version, String targetType) {
        return actionMapper.selectByTargetType(domainName, version, targetType);
    }

    @Override
    @Transactional
    public DryRunResult dryRun(ActionRequest request) {
        DryRunResult result = new DryRunResult();
        result.setValid(true);
        result.setWarnings(new ArrayList<>());
        result.setErrors(new ArrayList<>());

        // 1. 获取 Action 定义
        OntologyAction actionDef = getActionDefinition(request);
        if (actionDef == null) {
            result.setValid(false);
            result.getErrors().add("Action not found: " + request.getActionName());
            return result;
        }

        // 2. 目标对象校验
        if (request.getTargetObjectId() == null || request.getTargetObjectId().isEmpty()) {
            result.setValid(false);
            result.getErrors().add("Target object ID is required");
        }

        // 3. Schema 校验
        validateInputSchema(request, actionDef, result);

        // 4. 前置条件检查
        PrecheckResult precheck = checkPreconditions(
            request.getDomainName(), request.getVersion(),
            request.getActionName(), request.getTargetObjectId()
        );
        result.setPrecheckResultJson(toJson(precheck));

        if (!precheck.getPassed()) {
            result.setValid(false);
            result.getErrors().addAll(precheck.getFailedConditions());
        }

        // 5. 生成预览
        if (result.getValid()) {
            Map<String, Object> preview = new HashMap<>();
            preview.put("action", actionDef.getActionName());
            preview.put("target", request.getTargetObjectId());
            preview.put("input", request.getInput());
            preview.put("estimated_effect", "Will create/update external resource");
            result.setPreview(preview);
            result.getWarnings().add("This is a dry-run. No actual action will be performed.");
        }

        return result;
    }

    @Override
    @Transactional
    public ActionResult submitAction(ActionRequest request) {
        // 1. 先执行 dry-run 校验
        if (Boolean.TRUE.equals(request.getDryRun())) {
            DryRunResult dryRun = dryRun(request);
            if (!dryRun.getValid()) {
                ActionResult result = new ActionResult();
                result.setStatus("failed");
                result.setErrorMessage("Dry-run validation failed: " + String.join(", ", dryRun.getErrors()));
                return result;
            }
        }

        // 2. 创建 Action 实例记录
        String actionId = UUID.randomUUID().toString();
        SemanticActionInstance instance = new SemanticActionInstance();
        instance.setActionId(actionId);
        instance.setDomainName(request.getDomainName());
        instance.setVersion(request.getVersion());
        instance.setActionName(request.getActionName());
        instance.setToolName(request.getToolName());
        instance.setTargetType(request.getTargetType());
        instance.setTargetObjectId(request.getTargetObjectId());
        instance.setInputJson(toJson(request.getInput()));
        instance.setDryRun(request.getDryRun());
        instance.setStatus("pending");
        instance.setRequestedBy(request.getRequestedBy());
        instance.setRequestedByAgent(request.getRequestedByAgent());
        instance.setCreatedAt(LocalDateTime.now());
        instance.setUpdatedAt(LocalDateTime.now());
        actionInstanceMapper.insert(instance);

        // 3. 执行前置条件检查并记录
        PrecheckResult precheck = checkPreconditions(
            request.getDomainName(), request.getVersion(),
            request.getActionName(), request.getTargetObjectId()
        );
        instance.setPrecheckResultJson(toJson(precheck));

        if (!precheck.getPassed()) {
            instance.setStatus("failed");
            instance.setUpdatedAt(LocalDateTime.now());
            actionInstanceMapper.updateById(instance);

            ActionResult result = new ActionResult();
            result.setActionId(actionId);
            result.setStatus("failed");
            result.setPrecheckResultJson(instance.getPrecheckResultJson());
            result.setCreatedAt(instance.getCreatedAt());
            result.setUpdatedAt(instance.getUpdatedAt());
            return result;
        }

        // 4. 提交到外部平台 (模拟)
        OntologyActionBinding binding = getActiveBinding(request);
        if (binding != null) {
            instance.setStatus("submitted");
            instance.setExternalRequestRef(binding.getPlatformActionRef() + ":" + actionId);
            log.info("Submitted action {} to platform {}, requestRef={}",
                actionId, binding.getPlatformName(), instance.getExternalRequestRef());
        } else {
            // 本地执行模式
            instance.setStatus("success");
            instance.setExternalResultJson("{\"status\":\"completed_locally\"}");
        }

        instance.setUpdatedAt(LocalDateTime.now());
        actionInstanceMapper.updateById(instance);

        // 5. 返回结果
        ActionResult result = new ActionResult();
        result.setActionId(actionId);
        result.setStatus(instance.getStatus());
        result.setPrecheckResultJson(instance.getPrecheckResultJson());
        result.setExternalRequestRef(instance.getExternalRequestRef());
        result.setExternalResultJson(instance.getExternalResultJson());
        result.setCreatedAt(instance.getCreatedAt());
        result.setUpdatedAt(instance.getUpdatedAt());
        return result;
    }

    @Override
    public ActionResult getActionStatus(String actionId) {
        SemanticActionInstance instance = actionInstanceMapper.selectById(actionId);
        if (instance == null) {
            throw new OntologyException("Action not found: " + actionId);
        }

        ActionResult result = new ActionResult();
        result.setActionId(actionId);
        result.setStatus(instance.getStatus());
        result.setExternalRequestRef(instance.getExternalRequestRef());
        result.setExternalResultJson(instance.getExternalResultJson());
        result.setCreatedAt(instance.getCreatedAt());
        result.setUpdatedAt(instance.getUpdatedAt());
        return result;
    }

    @Override
    public ActionResult cancelAction(String actionId) {
        SemanticActionInstance instance = actionInstanceMapper.selectById(actionId);
        if (instance == null) {
            throw new OntologyException("Action not found: " + actionId);
        }

        if ("running".equals(instance.getStatus()) || "pending".equals(instance.getStatus()) || "submitted".equals(instance.getStatus())) {
            instance.setStatus("cancelled");
            instance.setUpdatedAt(LocalDateTime.now());
            actionInstanceMapper.updateById(instance);
        }

        return getActionStatus(actionId);
    }

    @Override
    public List<SemanticActionInstance> listActionInstances(String domainName, Map<String, Object> filters) {
        QueryWrapper<SemanticActionInstance> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName);
        if (filters != null) {
            if (filters.get("status") != null) {
                wrapper.eq("status", filters.get("status"));
            }
            if (filters.get("actionName") != null) {
                wrapper.eq("action_name", filters.get("actionName"));
            }
        }
        wrapper.orderByDesc("created_at");
        return actionInstanceMapper.selectList(wrapper);
    }

    @Override
    public SemanticActionInstance getActionInstance(String actionId) {
        return actionInstanceMapper.selectById(actionId);
    }

    @Override
    public PrecheckResult checkPreconditions(String domainName, String version, String actionName, String targetObjectId) {
        PrecheckResult result = new PrecheckResult();
        result.setPassed(true);
        result.setFailedConditions(new ArrayList<>());
        result.setCheckedValues(new HashMap<>());

        OntologyAction actionDef = getActionDefinition(domainName, version, actionName);
        if (actionDef == null) {
            result.setPassed(false);
            result.getFailedConditions().add("Action definition not found: " + actionName);
            return result;
        }

        // 1. 检查 precondition_sql
        if (actionDef.getPreconditionSql() != null && !actionDef.getPreconditionSql().isEmpty()) {
            try {
                // 执行前置条件 SQL
                String sql = actionDef.getPreconditionSql().replace("{target_object_id}", "'" + targetObjectId + "'");
                Map<String, Object> sqlResult = queryAdapter.executeSemanticQuery(domainName, version,
                    createPreconditionQuery(sql)).getRows().get(0);
                Boolean preconditionMet = (Boolean) sqlResult.getOrDefault("precondition_met", true);
                if (!Boolean.TRUE.equals(preconditionMet)) {
                    result.setPassed(false);
                    result.getFailedConditions().add("Precondition SQL check failed: " + actionDef.getPreconditionSql());
                }
                result.getCheckedValues().put("precondition_sql", preconditionMet);
            } catch (Exception e) {
                result.setPassed(false);
                result.getFailedConditions().add("Precondition SQL execution error: " + e.getMessage());
            }
        }

        // 2. 检查 precondition_logic (推理事实)
        if (actionDef.getPreconditionLogic() != null && !actionDef.getPreconditionLogic().isEmpty()) {
            String logicName = actionDef.getPreconditionLogic();
            // 解析 logic_name 获取 target_type 和 target_property
            String[] parts = logicName.split("\\.");
            if (parts.length >= 2) {
                String targetType = parts[0];
                String targetProperty = parts[1];
                SemanticFact fact = logicRegistry.getDerivedFact(domainName, version, targetType, targetObjectId, targetProperty);
                if (fact == null) {
                    result.setPassed(false);
                    result.getFailedConditions().add("Required derived fact not found: " + logicName);
                } else {
                    result.getCheckedValues().put(logicName, extractValue(fact));
                }
            }
        }

        // 3. 检查目标对象状态
        result.getCheckedValues().put("target_object_id", targetObjectId);
        result.getCheckedValues().put("action_name", actionName);

        if (result.getPassed()) {
            result.setExplanation("All preconditions passed for action " + actionName);
        } else {
            result.setExplanation("Preconditions failed: " + String.join(", ", result.getFailedConditions()));
        }

        return result;
    }

    private OntologyAction getActionDefinition(ActionRequest request) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", request.getDomainName())
               .eq("version", request.getVersion())
               .eq("action_name", request.getActionName());
        return actionMapper.selectOne(wrapper);
    }

    private OntologyAction getActionDefinition(String domainName, String version, String actionName) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("action_name", actionName);
        return actionMapper.selectOne(wrapper);
    }

    private OntologyActionBinding getActiveBinding(ActionRequest request) {
        QueryWrapper<OntologyActionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", request.getDomainName())
               .eq("version", request.getVersion())
               .eq("action_name", request.getActionName())
               .eq("enabled", true);
        return actionBindingMapper.selectOne(wrapper);
    }

    private void validateInputSchema(ActionRequest request, OntologyAction actionDef, DryRunResult result) {
        if (actionDef.getInputSchemaJson() == null || actionDef.getInputSchemaJson().isEmpty()) {
            return;
        }
        // 简化校验：检查必填字段是否存在
        if (request.getInput() == null) {
            result.getWarnings().add("No input parameters provided");
            return;
        }
        // TODO: 解析 JSON Schema 进行完整校验
    }

    private SemanticQuery createPreconditionQuery(String sql) {
        SemanticQuery query = new SemanticQuery();
        query.setIntent("select");
        // 将 SQL 包装为子查询
        return query;
    }

    private String toJson(Object obj) {
        if (obj == null) return null;
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(obj);
        } catch (Exception e) {
            return obj.toString();
        }
    }

    private Object extractValue(SemanticFact fact) {
        if (fact.getValueString() != null) return fact.getValueString();
        if (fact.getValueNumber() != null) return fact.getValueNumber();
        if (fact.getValueBool() != null) return fact.getValueBool();
        if (fact.getValueJson() != null) return fact.getValueJson();
        return null;
    }
}
