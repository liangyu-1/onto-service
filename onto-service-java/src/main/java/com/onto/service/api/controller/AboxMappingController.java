package com.onto.service.api.controller;

import com.onto.service.common.Result;
import com.onto.service.entity.OntologyObjectAboxMapping;
import com.onto.service.semantic.abox.OntologyObjectAboxMappingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * TBOX/ABOX 映射 REST API
 */
@RestController
@RequestMapping("/api/v1/abox-mappings")
public class AboxMappingController {

    @Autowired
    private OntologyObjectAboxMappingService aboxMappingService;

    @PostMapping("/{domainName}/{version}")
    public Result<OntologyObjectAboxMapping> createMapping(@PathVariable String domainName,
                                                            @PathVariable String version,
                                                            @RequestBody OntologyObjectAboxMapping mapping) {
        mapping.setDomainName(domainName);
        mapping.setVersion(version);
        return Result.success(aboxMappingService.createMapping(mapping));
    }

    @GetMapping("/{domainName}/{version}")
    public Result<List<OntologyObjectAboxMapping>> listMappings(@PathVariable String domainName,
                                                                 @PathVariable String version) {
        return Result.success(aboxMappingService.listMappings(domainName, version));
    }

    @GetMapping("/{domainName}/{version}/{className}")
    public Result<OntologyObjectAboxMapping> getMapping(@PathVariable String domainName,
                                                         @PathVariable String version,
                                                         @PathVariable String className) {
        return Result.success(aboxMappingService.getMapping(domainName, version, className));
    }

    @PutMapping("/{domainName}/{version}/{className}")
    public Result<OntologyObjectAboxMapping> updateMapping(@PathVariable String domainName,
                                                            @PathVariable String version,
                                                            @PathVariable String className,
                                                            @RequestBody OntologyObjectAboxMapping mapping) {
        mapping.setDomainName(domainName);
        mapping.setVersion(version);
        mapping.setClassName(className);
        return Result.success(aboxMappingService.updateMapping(mapping));
    }

    @DeleteMapping("/{domainName}/{version}/{className}")
    public Result<String> deleteMapping(@PathVariable String domainName,
                                         @PathVariable String version,
                                         @PathVariable String className) {
        aboxMappingService.deleteMapping(domainName, version, className);
        return Result.success("deleted");
    }
}
