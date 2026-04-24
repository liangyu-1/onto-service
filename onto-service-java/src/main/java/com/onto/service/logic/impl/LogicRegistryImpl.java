package com.onto.service.logic.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.service.entity.*;
import com.onto.service.exception.OntologyException;
import com.onto.service.logic.LogicRegistry;
import com.onto.service.mapper.*;
import com.onto.service.tbox.neo4j.TboxNeo4jService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Logic Registry 实现
 */
@Slf4j
@Service
public class LogicRegistryImpl extends ServiceImpl<OntologyLogicMapper, OntologyLogic> implements LogicRegistry {

    @Autowired
    private OntologyLogicDependencyMapper dependencyMapper;

    @Autowired
    private OntologyLogicExecutionBindingMapper bindingMapper;

    @Autowired
    private OntologyLogicExplanationMapper explanationMapper;

    @Autowired
    private SemanticFactMapper factMapper;

    @Autowired
    private SemanticLogicRunMapper logicRunMapper;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private TboxNeo4jService tbox;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    @Transactional
    public OntologyLogic createLogic(OntologyLogic logic) {
        // TBOX 唯一主存位于 Neo4j；Registry 侧仅保留执行/解释相关能力，不落 Doris 元数据主表
        return logic;
    }

    @Override
    @Transactional
    public OntologyLogic updateLogic(String domainName, String version, String logicName, OntologyLogic logic) {
        // MVP: 由 Ontology Service 负责更新 Neo4j TBOX；此处不再更新 Doris 元数据表
        logic.setDomainName(domainName);
        logic.setVersion(version);
        logic.setLogicName(logicName);
        return logic;
    }

    @Override
    @Transactional
    public void deleteLogic(String domainName, String version, String logicName) {
        // MVP: delete 由 Neo4j TBOX 侧实现；此处不处理
    }

    @Override
    public OntologyLogic getLogic(String domainName, String version, String logicName) {
        return tbox.listLogic(domainName, version).stream()
                .filter(l -> logicName.equals(l.getLogicName()))
                .findFirst()
                .orElse(null);
    }

    @Override
    public List<OntologyLogic> getLogicsByType(String domainName, String version, String logicKind) {
        return tbox.listLogic(domainName, version).stream()
                .filter(l -> logicKind.equals(l.getLogicKind()))
                .toList();
    }

    @Override
    public List<OntologyLogic> getLogicsByTarget(String domainName, String version, String targetType) {
        return tbox.listLogic(domainName, version).stream()
                .filter(l -> targetType.equals(l.getTargetType()))
                .toList();
    }

    @Override
    public List<OntologyLogic> list(String domainName, String version) {
        return tbox.listLogic(domainName, version);
    }

    @Override
    @Transactional
    public void addDependency(OntologyLogicDependency dependency) {
        dependencyMapper.insert(dependency);
    }

    @Override
    @Transactional
    public void removeDependency(String domainName, String version, String logicName, String dependencyName) {
        QueryWrapper<OntologyLogicDependency> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("logic_name", logicName)
               .eq("dependency_name", dependencyName);
        dependencyMapper.delete(wrapper);
    }

    @Override
    public List<OntologyLogicDependency> getDependencies(String domainName, String version, String logicName) {
        return dependencyMapper.selectByLogicName(domainName, version, logicName);
    }

    @Override
    public List<OntologyLogicDependency> getDependents(String domainName, String version, String dependencyName) {
        return dependencyMapper.selectByDependencyName(domainName, version, dependencyName);
    }

    @Override
    public List<String> getDependencyTopoOrder(String domainName, String version) {
        List<OntologyLogic> allLogics = tbox.listLogic(domainName, version);

        Map<String, List<String>> graph = new HashMap<>();
        Map<String, Integer> inDegree = new HashMap<>();

        for (OntologyLogic logic : allLogics) {
            graph.putIfAbsent(logic.getLogicName(), new ArrayList<>());
            inDegree.putIfAbsent(logic.getLogicName(), 0);
        }

        for (OntologyLogic logic : allLogics) {
            List<OntologyLogicDependency> deps = dependencyMapper.selectByLogicName(domainName, version, logic.getLogicName());
            for (OntologyLogicDependency dep : deps) {
                if (Boolean.TRUE.equals(dep.getRequired())) {
                    graph.computeIfAbsent(dep.getDependencyName(), k -> new ArrayList<>()).add(logic.getLogicName());
                    inDegree.merge(logic.getLogicName(), 1, Integer::sum);
                }
            }
        }

        Queue<String> queue = new LinkedList<>();
        for (Map.Entry<String, Integer> entry : inDegree.entrySet()) {
            if (entry.getValue() == 0) {
                queue.offer(entry.getKey());
            }
        }

        List<String> result = new ArrayList<>();
        while (!queue.isEmpty()) {
            String current = queue.poll();
            result.add(current);

            for (String neighbor : graph.getOrDefault(current, Collections.emptyList())) {
                int newDegree = inDegree.get(neighbor) - 1;
                inDegree.put(neighbor, newDegree);
                if (newDegree == 0) {
                    queue.offer(neighbor);
                }
            }
        }

        if (result.size() != allLogics.size()) {
            throw new OntologyException("Dependency cycle detected in logic rules");
        }

        return result;
    }

    @Override
    @Transactional
    public void createExecutionBinding(OntologyLogicExecutionBinding binding) {
        bindingMapper.insert(binding);
    }

    @Override
    @Transactional
    public void updateExecutionBinding(OntologyLogicExecutionBinding binding) {
        QueryWrapper<OntologyLogicExecutionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", binding.getDomainName())
               .eq("version", binding.getVersion())
               .eq("logic_name", binding.getLogicName())
               .eq("platform_name", binding.getPlatformName());
        bindingMapper.update(binding, wrapper);
    }

    @Override
    public OntologyLogicExecutionBinding getExecutionBinding(String domainName, String version, String logicName, String platformName) {
        QueryWrapper<OntologyLogicExecutionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("logic_name", logicName)
               .eq("platform_name", platformName);
        return bindingMapper.selectOne(wrapper);
    }

    @Override
    public List<OntologyLogicExecutionBinding> getExecutionBindings(String domainName, String version, String logicName) {
        return bindingMapper.selectByLogicName(domainName, version, logicName);
    }

    @Override
    @Transactional
    public void createExplanation(OntologyLogicExplanation explanation) {
        explanationMapper.insert(explanation);
    }

    @Override
    public OntologyLogicExplanation getExplanation(String domainName, String version, String logicName, String language) {
        return explanationMapper.selectByLogicAndLanguage(domainName, version, logicName, language);
    }

    @Override
    public String renderExplanation(String domainName, String version, String logicName, String language, Map<String, Object> context) {
        OntologyLogicExplanation explanation = getExplanation(domainName, version, logicName, language);
        if (explanation == null || explanation.getTemplateText() == null) {
            return "No explanation template found";
        }

        String template = explanation.getTemplateText();
        for (Map.Entry<String, Object> entry : context.entrySet()) {
            template = template.replace("{" + entry.getKey() + "}", String.valueOf(entry.getValue()));
        }
        return template;
    }

    @Override
    public SemanticFact getDerivedFact(String domainName, String version, String objectType, String objectId, String propertyName) {
        QueryWrapper<SemanticFact> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("object_type", objectType)
               .eq("object_id", objectId)
               .eq("property_name", propertyName);
        return factMapper.selectOne(wrapper);
    }

    @Override
    public List<SemanticFact> getDerivedFacts(String domainName, String version, String objectType, String objectId) {
        return factMapper.selectByObject(domainName, version, objectType, objectId);
    }

    @Override
    public List<SemanticFact> getDerivedFactsByLogic(String domainName, String version, String logicName) {
        return factMapper.selectByLogicName(domainName, version, logicName);
    }

    @Override
    @Transactional
    public List<SemanticFact> executeSqlLogic(String domainName, String version, String logicName, Map<String, Object> params) {
        OntologyLogic logic = getLogic(domainName, version, logicName);
        if (logic == null) {
            throw new OntologyException("Logic not found: " + logicName);
        }
        if (!"sql".equals(logic.getImplementationType())) {
            throw new OntologyException("Logic is not SQL type: " + logicName);
        }

        String sql = logic.getExpressionSql();
        if (sql == null || sql.isEmpty()) {
            throw new OntologyException("SQL expression is empty for logic: " + logicName);
        }

        // 参数替换
        if (params != null) {
            for (Map.Entry<String, Object> param : params.entrySet()) {
                String placeholder = "{" + param.getKey() + "}";
                String value = param.getValue() instanceof String
                    ? "'" + param.getValue() + "'" : String.valueOf(param.getValue());
                sql = sql.replace(placeholder, value);
            }
        }

        // 记录运行
        SemanticLogicRun run = new SemanticLogicRun();
        run.setRunId(UUID.randomUUID().toString());
        run.setDomainName(domainName);
        run.setVersion(version);
        run.setLogicName(logicName);
        run.setExecutionModeHint("on_read");
        run.setStartedAt(LocalDateTime.now());
        run.setStatus("running");
        logicRunMapper.insert(run);

        try {
            // 执行 SQL
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql);

            // 转换为 SemanticFact
            List<SemanticFact> facts = new ArrayList<>();
            for (Map<String, Object> row : rows) {
                SemanticFact fact = new SemanticFact();
                fact.setDomainName(domainName);
                fact.setVersion(version);
                fact.setObjectType(logic.getTargetType());
                fact.setObjectId(String.valueOf(row.getOrDefault("object_id", row.getOrDefault("id", ""))));
                fact.setPropertyName(logic.getTargetProperty());
                fact.setValueType(logic.getOutputType());
                fact.setComputedByLogic(logicName);
                fact.setComputedAt(LocalDateTime.now());
                fact.setValidFrom(LocalDateTime.now());

                Object value = row.get("value");
                if (value == null) {
                    // 尝试其他常见列名
                    value = row.getOrDefault(logic.getTargetProperty(), row.values().iterator().next());
                }
                setFactValue(fact, value, logic.getOutputType());

                facts.add(fact);
            }

            // 批量插入
            for (SemanticFact fact : facts) {
                factMapper.insert(fact);
            }

            // 更新运行记录
            run.setStatus("success");
            run.setFinishedAt(LocalDateTime.now());
            run.setInputCount(rows.size());
            run.setOutputCount(facts.size());
            logicRunMapper.updateById(run);

            return facts;
        } catch (Exception e) {
            run.setStatus("failed");
            run.setFinishedAt(LocalDateTime.now());
            run.setErrorMessage(e.getMessage());
            logicRunMapper.updateById(run);
            throw new OntologyException("SQL logic execution failed: " + e.getMessage());
        }
    }

    @Override
    public String triggerExternalLogic(String domainName, String version, String logicName, String platformName) {
        OntologyLogicExecutionBinding binding = getExecutionBinding(domainName, version, logicName, platformName);
        if (binding == null || !Boolean.TRUE.equals(binding.getEnabled())) {
            throw new OntologyException("External binding not found or disabled");
        }

        // 记录运行
        SemanticLogicRun run = new SemanticLogicRun();
        run.setRunId(UUID.randomUUID().toString());
        run.setDomainName(domainName);
        run.setVersion(version);
        run.setLogicName(logicName);
        run.setExecutionModeHint(binding.getExecutionModeHint());
        run.setExternalPlatform(platformName);
        run.setExternalJobRef(binding.getPlatformJobRef());
        run.setStartedAt(LocalDateTime.now());
        run.setStatus("submitted");
        logicRunMapper.insert(run);

        // 尝试触发外部平台
        try {
            triggerExternalPlatform(binding, run);
        } catch (Exception e) {
            log.warn("Failed to trigger external platform synchronously, run marked as submitted: {}", e.getMessage());
        }

        log.info("Triggered external logic {} on platform {}, runId={}", logicName, platformName, run.getRunId());
        return run.getRunId();
    }

    // ==================== Private Methods ====================

    /**
     * 触发外部平台执行
     */
    private void triggerExternalPlatform(OntologyLogicExecutionBinding binding, SemanticLogicRun run) {
        if (binding.getPlatformJobRef() == null) {
            return;
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("run_id", run.getRunId());
        body.put("logic_name", run.getLogicName());
        body.put("domain_name", run.getDomainName());
        body.put("version", run.getVersion());
        body.put("result_table", binding.getResultTable());
        body.put("trigger_rule_ref", binding.getTriggerRuleRef());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(
                binding.getPlatformJobRef(), entity, Map.class);

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Map<String, Object> result = response.getBody();
                String externalJobId = String.valueOf(result.getOrDefault("job_id", ""));
                run.setExternalJobRef(externalJobId);
                logicRunMapper.updateById(run);
                log.info("External platform accepted job, externalJobId={}", externalJobId);
            }
        } catch (Exception e) {
            log.error("External platform trigger failed: {}", e.getMessage());
            throw e;
        }
    }

    private void setFactValue(SemanticFact fact, Object value, String outputType) {
        if (value == null) return;
        switch (outputType != null ? outputType.toUpperCase() : "STRING") {
            case "STRING":
                fact.setValueString(String.valueOf(value));
                break;
            case "DOUBLE":
            case "FLOAT":
                fact.setValueNumber(Double.valueOf(String.valueOf(value)));
                break;
            case "INT":
            case "INT64":
            case "INTEGER":
                fact.setValueNumber(Double.valueOf(String.valueOf(value)));
                break;
            case "BOOL":
            case "BOOLEAN":
                fact.setValueBool(Boolean.valueOf(String.valueOf(value)));
                break;
            case "JSON":
                fact.setValueJson(String.valueOf(value));
                break;
            default:
                fact.setValueString(String.valueOf(value));
        }
    }
}
