package com.onto.service.api.controller;

import com.onto.service.common.Result;
import com.onto.service.entity.*;
import com.onto.service.logic.LogicRegistry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Logic Registry REST API
 */
@RestController
@RequestMapping("/api/v1/logic")
public class LogicController {

    @Autowired
    private LogicRegistry logicRegistry;

    @PostMapping("/{domainName}/{version}")
    public Result<OntologyLogic> createLogic(@PathVariable String domainName,
                                              @PathVariable String version,
                                              @RequestBody OntologyLogic logic) {
        logic.setDomainName(domainName);
        logic.setVersion(version);
        return Result.success(logicRegistry.createLogic(logic));
    }

    @GetMapping("/{domainName}/{version}/{logicName}")
    public Result<OntologyLogic> getLogic(@PathVariable String domainName,
                                           @PathVariable String version,
                                           @PathVariable String logicName) {
        return Result.success(logicRegistry.getLogic(domainName, version, logicName));
    }

    @GetMapping("/{domainName}/{version}")
    public Result<List<OntologyLogic>> listLogics(@PathVariable String domainName,
                                                   @PathVariable String version,
                                                   @RequestParam(required = false) String logicKind,
                                                   @RequestParam(required = false) String targetType) {
        if (logicKind != null) {
            return Result.success(logicRegistry.getLogicsByType(domainName, version, logicKind));
        }
        if (targetType != null) {
            return Result.success(logicRegistry.getLogicsByTarget(domainName, version, targetType));
        }
        return Result.success(logicRegistry.list());
    }

    @GetMapping("/{domainName}/{version}/{logicName}/dependencies")
    public Result<List<OntologyLogicDependency>> getDependencies(@PathVariable String domainName,
                                                                  @PathVariable String version,
                                                                  @PathVariable String logicName) {
        return Result.success(logicRegistry.getDependencies(domainName, version, logicName));
    }

    @GetMapping("/{domainName}/{version}/topo-order")
    public Result<List<String>> getTopoOrder(@PathVariable String domainName,
                                              @PathVariable String version) {
        return Result.success(logicRegistry.getDependencyTopoOrder(domainName, version));
    }

    @PostMapping("/{domainName}/{version}/{logicName}/execute")
    public Result<List<SemanticFact>> executeLogic(@PathVariable String domainName,
                                                    @PathVariable String version,
                                                    @PathVariable String logicName,
                                                    @RequestBody(required = false) Map<String, Object> params) {
        return Result.success(logicRegistry.executeSqlLogic(domainName, version, logicName, params));
    }

    @GetMapping("/{domainName}/{version}/{logicName}/explanation")
    public Result<String> getExplanation(@PathVariable String domainName,
                                          @PathVariable String version,
                                          @PathVariable String logicName,
                                          @RequestParam(defaultValue = "zh-CN") String language) {
        OntologyLogicExplanation explanation = logicRegistry.getExplanation(domainName, version, logicName, language);
        return Result.success(explanation != null ? explanation.getTemplateText() : null);
    }

    @PostMapping("/{domainName}/{version}/{logicName}/explain")
    public Result<String> renderExplanation(@PathVariable String domainName,
                                             @PathVariable String version,
                                             @PathVariable String logicName,
                                             @RequestParam(defaultValue = "zh-CN") String language,
                                             @RequestBody Map<String, Object> context) {
        return Result.success(logicRegistry.renderExplanation(domainName, version, logicName, language, context));
    }
}
