package com.onto.service.api.controller;

import com.onto.service.entity.OntologyDomain;
import com.onto.service.tbox.neo4j.TboxNeo4jService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 本体域管理 REST API
 */
@RestController
@RequestMapping("/api/v1/domains")
public class DomainController {

    @Autowired
    private TboxNeo4jService tbox;

    @PostMapping
    public OntologyDomain createDomain(@RequestBody CreateDomainRequest request) {
        return tbox.createDomain(request.getDomainName(), request.getDdlSql(), request.getCreatedBy());
    }

    @PostMapping("/{domainName}/versions")
    public OntologyDomain publishVersion(@PathVariable String domainName,
                                          @RequestBody PublishVersionRequest request) {
        return tbox.publishVersion(domainName, request.getDdlSql(), request.getCreatedBy());
    }

    @GetMapping("/{domainName}/versions/{version}")
    public OntologyDomain getDomainVersion(@PathVariable String domainName, @PathVariable String version) {
        return tbox.getDomainVersion(domainName, version).orElse(null);
    }

    @GetMapping("/{domainName}/versions")
    public List<OntologyDomain> getDomainVersions(@PathVariable String domainName) {
        return tbox.listDomainVersions(domainName);
    }

    @GetMapping("/{domainName}/latest")
    public OntologyDomain getLatestVersion(@PathVariable String domainName) {
        return tbox.latestPublished(domainName).orElse(null);
    }

    // Request DTOs
    @lombok.Data
    public static class CreateDomainRequest {
        private String domainName;
        private String ddlSql;
        private String createdBy;
    }

    @lombok.Data
    public static class PublishVersionRequest {
        private String ddlSql;
        private String createdBy;
    }
}
