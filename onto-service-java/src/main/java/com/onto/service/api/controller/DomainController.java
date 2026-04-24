package com.onto.service.api.controller;

import com.onto.service.entity.OntologyDomain;
import com.onto.service.semantic.OntologyDomainService;
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
    private OntologyDomainService domainService;

    @PostMapping
    public OntologyDomain createDomain(@RequestBody CreateDomainRequest request) {
        return domainService.createDomain(request.getDomainName(), request.getDdlSql(), request.getCreatedBy());
    }

    @PostMapping("/{domainName}/versions")
    public OntologyDomain publishVersion(@PathVariable String domainName,
                                          @RequestBody PublishVersionRequest request) {
        return domainService.publishVersion(domainName, request.getDdlSql(), request.getCreatedBy());
    }

    @GetMapping("/{domainName}/versions/{version}")
    public OntologyDomain getDomainVersion(@PathVariable String domainName, @PathVariable String version) {
        return domainService.getDomainVersion(domainName, version);
    }

    @GetMapping("/{domainName}/versions")
    public List<OntologyDomain> getDomainVersions(@PathVariable String domainName) {
        return domainService.getDomainVersions(domainName);
    }

    @GetMapping("/{domainName}/latest")
    public OntologyDomain getLatestVersion(@PathVariable String domainName) {
        return domainService.getLatestPublishedVersion(domainName);
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
