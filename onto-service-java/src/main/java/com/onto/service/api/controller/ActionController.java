package com.onto.service.api.controller;

import com.onto.service.action.*;
import com.onto.service.entity.SemanticActionInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Action Gateway REST API
 */
@RestController
@RequestMapping("/api/v1/actions")
public class ActionController {

    @Autowired
    private ActionGateway actionGateway;

    @GetMapping("/tools/{domainName}/{version}")
    public List<com.onto.service.entity.OntologyAction> listTools(@PathVariable String domainName,
                                                                   @PathVariable String version) {
        return actionGateway.listTools(domainName, version);
    }

    @PostMapping("/dry-run")
    public DryRunResult dryRun(@RequestBody ActionRequest request) {
        return actionGateway.dryRun(request);
    }

    @PostMapping("/submit")
    public ActionResult submitAction(@RequestBody ActionRequest request) {
        return actionGateway.submitAction(request);
    }

    @GetMapping("/{actionId}/status")
    public ActionResult getActionStatus(@PathVariable String actionId) {
        return actionGateway.getActionStatus(actionId);
    }

    @PostMapping("/{actionId}/cancel")
    public ActionResult cancelAction(@PathVariable String actionId) {
        return actionGateway.cancelAction(actionId);
    }

    @GetMapping("/instances/{domainName}")
    public List<SemanticActionInstance> listInstances(@PathVariable String domainName,
                                                       @RequestParam Map<String, Object> filters) {
        return actionGateway.listActionInstances(domainName, filters);
    }
}
