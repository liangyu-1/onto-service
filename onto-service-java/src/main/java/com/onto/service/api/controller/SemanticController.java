package com.onto.service.api.controller;

import com.onto.service.common.Result;
import com.onto.service.entity.*;
import com.onto.service.tbox.neo4j.TboxNeo4jService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Semantic Layer REST API
 */
@RestController
@RequestMapping("/api/v1/semantic")
public class SemanticController {

    @Autowired
    private TboxNeo4jService tbox;

    // ===== Object Type APIs =====

    @PostMapping("/{domainName}/{version}/object-types")
    public Result<OntologyObjectType> createObjectType(@PathVariable String domainName,
                                                        @PathVariable String version,
                                                        @RequestBody OntologyObjectType objectType) {
        objectType.setDomainName(domainName);
        objectType.setVersion(version);
        return Result.success(tbox.createObjectType(objectType));
    }

    @GetMapping("/{domainName}/{version}/object-types")
    public Result<List<OntologyObjectType>> listObjectTypes(@PathVariable String domainName,
                                                             @PathVariable String version) {
        return Result.success(tbox.listObjectTypes(domainName, version));
    }

    @GetMapping("/{domainName}/{version}/object-types/{labelName}")
    public Result<OntologyObjectType> getObjectType(@PathVariable String domainName,
                                                     @PathVariable String version,
                                                     @PathVariable String labelName) {
        // MVP: list and filter
        return Result.success(
                tbox.listObjectTypes(domainName, version).stream()
                        .filter(x -> labelName.equals(x.getLabelName()))
                        .findFirst()
                        .orElse(null)
        );
    }

    @GetMapping("/{domainName}/{version}/object-types/{labelName}/children")
    public Result<List<OntologyObjectType>> getChildTypes(@PathVariable String domainName,
                                                           @PathVariable String version,
                                                           @PathVariable String labelName) {
        return Result.success(
                tbox.listObjectTypes(domainName, version).stream()
                        .filter(x -> labelName.equals(x.getParentLabel()))
                        .toList()
        );
    }

    // ===== Property APIs =====

    @PostMapping("/{domainName}/{version}/properties")
    public Result<OntologyProperty> createProperty(@PathVariable String domainName,
                                                    @PathVariable String version,
                                                    @RequestBody OntologyProperty property) {
        property.setDomainName(domainName);
        property.setVersion(version);
        return Result.success(tbox.createProperty(property));
    }

    @GetMapping("/{domainName}/{version}/object-types/{ownerLabel}/properties")
    public Result<List<OntologyProperty>> listProperties(@PathVariable String domainName,
                                                          @PathVariable String version,
                                                          @PathVariable String ownerLabel,
                                                          @RequestParam(required = false, defaultValue = "false") boolean visibleOnly) {
        List<OntologyProperty> props = tbox.listProperties(domainName, version, ownerLabel);
        if (visibleOnly) {
            props = props.stream().filter(p -> p.getHidden() == null || !p.getHidden()).toList();
        }
        return Result.success(props);
    }

    // ===== Relationship APIs =====

    @PostMapping("/{domainName}/{version}/relationships")
    public Result<OntologyRelationship> createRelationship(@PathVariable String domainName,
                                                            @PathVariable String version,
                                                            @RequestBody OntologyRelationship relationship) {
        relationship.setDomainName(domainName);
        relationship.setVersion(version);
        return Result.success(tbox.createRelationship(relationship));
    }

    @GetMapping("/{domainName}/{version}/relationships")
    public Result<List<OntologyRelationship>> listRelationships(@PathVariable String domainName,
                                                                 @PathVariable String version) {
        return Result.success(tbox.listRelationships(domainName, version));
    }

    @GetMapping("/{domainName}/{version}/object-types/{sourceLabel}/outgoing-relationships")
    public Result<List<OntologyRelationship>> getOutgoingRelationships(@PathVariable String domainName,
                                                                        @PathVariable String version,
                                                                        @PathVariable String sourceLabel) {
        return Result.success(
                tbox.listRelationships(domainName, version).stream()
                        .filter(r -> sourceLabel.equals(r.getSourceLabel()))
                        .toList()
        );
    }
}
