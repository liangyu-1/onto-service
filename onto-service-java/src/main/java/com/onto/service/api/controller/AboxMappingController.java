package com.onto.service.api.controller;

import com.onto.service.common.Result;
import com.onto.service.entity.OntologyObjectAboxMapping;
import com.onto.service.tbox.neo4j.TboxNeo4jService;
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
    private TboxNeo4jService tbox;

    @PostMapping("/{domainName}/{version}")
    public Result<OntologyObjectAboxMapping> createMapping(@PathVariable String domainName,
                                                            @PathVariable String version,
                                                            @RequestBody OntologyObjectAboxMapping mapping) {
        mapping.setDomainName(domainName);
        mapping.setVersion(version);
        return Result.success(tbox.createAboxMapping(mapping));
    }

    @GetMapping("/{domainName}/{version}")
    public Result<List<OntologyObjectAboxMapping>> listMappings(@PathVariable String domainName,
                                                                 @PathVariable String version) {
        return Result.success(tbox.listAboxMappings(domainName, version));
    }

    @GetMapping("/{domainName}/{version}/{className}")
    public Result<OntologyObjectAboxMapping> getMapping(@PathVariable String domainName,
                                                         @PathVariable String version,
                                                         @PathVariable String className) {
        return Result.success(
                tbox.listAboxMappings(domainName, version).stream()
                        .filter(m -> className.equals(m.getClassName()))
                        .findFirst()
                        .orElse(null)
        );
    }

    @PutMapping("/{domainName}/{version}/{className}")
    public Result<OntologyObjectAboxMapping> updateMapping(@PathVariable String domainName,
                                                            @PathVariable String version,
                                                            @PathVariable String className,
                                                            @RequestBody OntologyObjectAboxMapping mapping) {
        mapping.setDomainName(domainName);
        mapping.setVersion(version);
        mapping.setClassName(className);
        return Result.success(tbox.createAboxMapping(mapping));
    }

    @DeleteMapping("/{domainName}/{version}/{className}")
    public Result<String> deleteMapping(@PathVariable String domainName,
                                         @PathVariable String version,
                                         @PathVariable String className) {
        // MVP: 未实现 delete
        return Result.success("not_implemented");
    }
}
