package com.onto.service.action.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import com.onto.service.action.*;
import com.onto.service.entity.*;
import com.onto.service.exception.OntologyException;
import com.onto.service.logic.LogicRegistry;
import com.onto.service.mapper.*;
import com.onto.service.query.QueryAdapter;
import com.onto.service.query.SemanticQuery;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

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

    @Autowired
    private RestTemplate restTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final JsonSchemaFactory schemaFactory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);

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

        // 5. 外部平台 dry-run (如果配置了)
        if (result.getValid()) {
            OntologyActionBinding binding = getActiveBinding(request);
            if (binding != null && binding.getDryRunRef() != null) {
                try {
                    Map<String, Object> externalPreview = callExternalDryRun(binding, request);
                    result.setPreview(externalPreview);
                } catch (Exception e) {
                    result.getWarnings().add("External dry-run failed: " + e.getMessage());
                    Map<String, Object> fallbackPreview = new HashMap<>();
                    fallbackPreview.put("action", actionDef.getActionName());
                    fallbackPreview.put("target", request.getTargetObjectId());
                    fallbackPreview.put("input", request.getInput());
                    fallbackPreview.put("note", "External dry-run unavailable, showing local preview only");
                    result.setPreview(fallbackPreview);
                }
            } else {
                Map<String, Object> preview = new HashMap<>();
                preview.put("action", actionDef.getActionName());
                preview.put("target", request.getTargetObjectId());
                preview.put("input", request.getInput());
                preview.put("estimated_effect", "Will create/update external resource");
                result.setPreview(preview);
            }
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

        // 4. 提交到外部平台
        OntologyActionBinding binding = getActiveBinding(request);
        if (binding != null) {
            try {
                String externalRef = submitToExternalPlatform(binding, request);
                instance.setStatus("submitted");
                instance.setExternalRequestRef(externalRef);
                log.info("Submitted action {} to platform {}, requestRef={}",
                    actionId, binding.getPlatformName(), externalRef);
            } catch (Exception e) {
                instance.setStatus("failed");
                instance.setErrorMessage("External submission failed: " + e.getMessage());
                log.error("Failed to submit action to external platform", e);
            }
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

        // 如果状态是 submitted，尝试查询外部平台状态
        if ("submitted".equals(instance.getStatus()) && instance.getExternalRequestRef() != null) {
            tryPollExternalStatus(instance);
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
            // 尝试取消外部平台任务
            if (instance.getExternalRequestRef() != null) {
                tryCancelExternalTask(instance);
            }
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
            if (filters.get("requestedBy") != null) {
                wrapper.eq("requested_by", filters.get("requestedBy"));
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
                String sql = actionDef.getPreconditionSql()
                    .replace("{target_object_id}", "'" + targetObjectId + "'")
                .replace("${target_object_id}", "'" + targetObjectId + "'");

                List<Map<String, Object>> rows = queryAdapter.executeSemanticQuery(domainName, version,
                    createPreconditionQuery(sql)).getRows();

                if (rows != null && !rows.isEmpty()) {
                    Object preconditionMet = rows.get(0).getOrDefault("precondition_met", true);
                    if (!Boolean.TRUE.equals(preconditionMet)) {
                        result.setPassed(false);
                        result.getFailedConditions().add("Precondition SQL check failed");
                    }
                    result.getCheckedValues().put("precondition_sql", preconditionMet);
                }
            } catch (Exception e) {
                result.setPassed(false);
                result.getFailedConditions().add("Precondition SQL execution error: " + e.getMessage());
            }
        }

        // 2. 检查 precondition_logic (推理事实)
        if (actionDef.getPreconditionLogic() != null && !actionDef.getPreconditionLogic().isEmpty()) {
            String logicName = actionDef.getPreconditionLogic();
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

    // ==================== Private Methods ====================

    private OntologyAction getActionDefinition(ActionRequest request) {
        return getActionDefinition(request.getDomainName(), request.getVersion(), request.getActionName());
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

    /**
     * JSON Schema 校验输入参数
     */
    private void validateInputSchema(ActionRequest request, OntologyAction actionDef, DryRunResult result) {
        if (actionDef.getInputSchemaJson() == null || actionDef.getInputSchemaJson().isEmpty()) {
            return;
        }
        if (request.getInput() == null) {
            result.getWarnings().add("No input parameters provided");
            return;
        }

        try {
            JsonSchema schema = schemaFactory.getSchema(actionDef.getInputSchemaJson());
            JsonNode inputNode = objectMapper.valueToTree(request.getInput());
            Set<ValidationMessage> validationMessages = schema.validate(inputNode);

            if (!validationMessages.isEmpty()) {
                result.setValid(false);
                for (ValidationMessage msg : validationMessages) {
                    result.getErrors().add("Input validation: " + msg.getMessage());
                }
            }
        } catch (Exception e) {
            result.getWarnings().add("Input schema validation error: " + e.getMessage());
        }
    }

    /**
     * 调用外部平台 dry-run
     */
    private Map<String, Object> callExternalDryRun(OntologyActionBinding binding, ActionRequest request) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("action_name", request.getActionName());
        body.put("target_object_id", request.getTargetObjectId());
        body.put("input", request.getInput());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
        ResponseEntity<Map> response = restTemplate.postForEntity(binding.getDryRunRef(), entity, Map.class);
        return response.getBody();
    }

    /**
     * 提交到外部平台
     */
    private String submitToExternalPlatform(OntologyActionBinding binding, ActionRequest request) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("action_name", request.getActionName());
        body.put("target_type", request.getTargetType());
        body.put("target_object_id", request.getTargetObjectId());
        body.put("input", request.getInput());
        body.put("requested_by", request.getRequestedBy());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
        ResponseEntity<Map> response = restTemplate.postForEntity(
            binding.getPlatformActionRef(), entity, Map.class);

        Map<String, Object> result = response.getBody();
        if (result != null && result.get("request_id") != null) {
            return String.valueOf(result.get("request_id"));
        }
        return binding.getPlatformActionRef() + ":" + UUID.randomUUID();
    }

    /**
     * 轮询外部平台状态
     */
    private void tryPollExternalStatus(SemanticActionInstance instance) {
        OntologyActionBinding binding = getBindingByAction(instance);
        if (binding == null || binding.getResultRef() == null) {
            return;
        }

        try {
            String url = binding.getResultRef() + "/" + instance.getExternalRequestRef();
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            Map<String, Object> result = response.getBody();
            if (result != null) {
                String status = String.valueOf(result.getOrDefault("status", "unknown"));
                instance.setStatus(mapExternalStatus(status));
                instance.setExternalResultJson(toJson(result));
                instance.setUpdatedAt(LocalDateTime.now());
                actionInstanceMapper.updateById(instance);
            }
        } catch (Exception e) {
            log.debug("Failed to poll external status for action {}", instance.getActionId(), e);
        }
    }

    /**
     * 取消外部平台任务
     */
    private void tryCancelExternalTask(SemanticActionInstance instance) {
        OntologyActionBinding binding = getBindingByAction(instance);
        if (binding == null) {
            return;
        }

        try {
            String url = binding.getPlatformActionRef() + "/" + instance.getExternalRequestRef() + "/cancel";
            restTemplate.postForEntity(url, null, Map.class);
        } catch (Exception e) {
            log.warn("Failed to cancel external task for action {}", instance.getActionId(), e);
        }
    }

    private OntologyActionBinding getBindingByAction(SemanticActionInstance instance) {
        QueryWrapper<OntologyActionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", instance.getDomainName())
               .eq("version", instance.getVersion())
               .eq("action_name", instance.getActionName())
               .eq("enabled", true);
        return actionBindingMapper.selectOne(wrapper);
    }

    private String mapExternalStatus(String externalStatus) {
        switch (externalStatus.toLowerCase()) {
            case "completed":
            case "success":
            case "done":
                return "success";
            case "failed":
            case "error":
                return "failed";
            case "running":
            case "in_progress":
                return "running";
            case "cancelled":
            case "canceled":
                return "cancelled";
            default:
                return "submitted";
        }
    }

    private SemanticQuery createPreconditionQuery(String sql) {
        SemanticQuery query = new SemanticQuery();
        query.setIntent("select");
        return query;
    }

    private String toJson(Object obj) {
        if (obj == null) return null;
        try {
            return objectMapper.writeValueAsString(obj);
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
