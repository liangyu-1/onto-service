package com.onto.service.api.controller;

import com.onto.service.action.admin.OntologyActionService;
import com.onto.service.common.Result;
import com.onto.service.entity.OntologyAction;
import com.onto.service.entity.OntologyActionBinding;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Action 管理 REST API（定义 + 绑定 CRUD）
 */
@RestController
@RequestMapping("/api/v1/actions")
public class ActionAdminController {

    @Autowired
    private OntologyActionService actionService;

    // ========== Action 定义 CRUD ==========

    @PostMapping("/definitions/{domainName}/{version}")
    public Result<OntologyAction> createAction(@PathVariable String domainName,
                                                @PathVariable String version,
                                                @RequestBody OntologyAction action) {
        action.setDomainName(domainName);
        action.setVersion(version);
        return Result.success(actionService.createAction(action));
    }

    @GetMapping("/definitions/{domainName}/{version}")
    public Result<List<OntologyAction>> listActions(@PathVariable String domainName,
                                                     @PathVariable String version) {
        return Result.success(actionService.listActions(domainName, version));
    }

    @GetMapping("/definitions/{domainName}/{version}/{actionName}")
    public Result<OntologyAction> getAction(@PathVariable String domainName,
                                             @PathVariable String version,
                                             @PathVariable String actionName) {
        return Result.success(actionService.getAction(domainName, version, actionName));
    }

    @PutMapping("/definitions/{domainName}/{version}/{actionName}")
    public Result<OntologyAction> updateAction(@PathVariable String domainName,
                                                @PathVariable String version,
                                                @PathVariable String actionName,
                                                @RequestBody OntologyAction action) {
        action.setDomainName(domainName);
        action.setVersion(version);
        action.setActionName(actionName);
        return Result.success(actionService.updateAction(action));
    }

    @DeleteMapping("/definitions/{domainName}/{version}/{actionName}")
    public Result<String> deleteAction(@PathVariable String domainName,
                                        @PathVariable String version,
                                        @PathVariable String actionName) {
        actionService.deleteAction(domainName, version, actionName);
        return Result.success("deleted");
    }

    // ========== Action 绑定 CRUD ==========

    @PostMapping("/bindings/{domainName}/{version}")
    public Result<OntologyActionBinding> createBinding(@PathVariable String domainName,
                                                        @PathVariable String version,
                                                        @RequestBody OntologyActionBinding binding) {
        binding.setDomainName(domainName);
        binding.setVersion(version);
        return Result.success(actionService.createBinding(binding));
    }

    @GetMapping("/bindings/{domainName}/{version}")
    public Result<List<OntologyActionBinding>> listBindings(@PathVariable String domainName,
                                                             @PathVariable String version) {
        return Result.success(actionService.listBindings(domainName, version));
    }

    @GetMapping("/bindings/{domainName}/{version}/{actionName}")
    public Result<List<OntologyActionBinding>> getBindingsByAction(@PathVariable String domainName,
                                                                    @PathVariable String version,
                                                                    @PathVariable String actionName) {
        return Result.success(actionService.listBindings(domainName, version).stream()
            .filter(b -> b.getActionName().equals(actionName))
            .toList());
    }

    @PutMapping("/bindings/{domainName}/{version}/{actionName}/{platformName}")
    public Result<OntologyActionBinding> updateBinding(@PathVariable String domainName,
                                                        @PathVariable String version,
                                                        @PathVariable String actionName,
                                                        @PathVariable String platformName,
                                                        @RequestBody OntologyActionBinding binding) {
        binding.setDomainName(domainName);
        binding.setVersion(version);
        binding.setActionName(actionName);
        binding.setPlatformName(platformName);
        return Result.success(actionService.updateBinding(binding));
    }

    @DeleteMapping("/bindings/{domainName}/{version}/{actionName}/{platformName}")
    public Result<String> deleteBinding(@PathVariable String domainName,
                                         @PathVariable String version,
                                         @PathVariable String actionName,
                                         @PathVariable String platformName) {
        actionService.deleteBinding(domainName, version, actionName, platformName);
        return Result.success("deleted");
    }
}
