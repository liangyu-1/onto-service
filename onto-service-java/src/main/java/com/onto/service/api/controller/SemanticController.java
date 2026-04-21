package com.onto.service.api.controller;

import com.onto.service.common.Result;
import com.onto.service.entity.*;
import com.onto.service.semantic.*;
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
    private OntologyObjectTypeService objectTypeService;

    @Autowired
    private OntologyPropertyService propertyService;

    @Autowired
    private OntologyRelationshipService relationshipService;

    // ===== Object Type APIs =====

    @PostMapping("/{domainName}/{version}/object-types")
    public Result<OntologyObjectType> createObjectType(@PathVariable String domainName,
                                                        @PathVariable String version,
                                                        @RequestBody OntologyObjectType objectType) {
        objectType.setDomainName(domainName);
        objectType.setVersion(version);
        return Result.success(objectTypeService.createObjectType(objectType));
    }

    @GetMapping("/{domainName}/{version}/object-types")
    public Result<List<OntologyObjectType>> listObjectTypes(@PathVariable String domainName,
                                                             @PathVariable String version) {
        return Result.success(objectTypeService.getObjectTypes(domainName, version));
    }

    @GetMapping("/{domainName}/{version}/object-types/{labelName}")
    public Result<OntologyObjectType> getObjectType(@PathVariable String domainName,
                                                     @PathVariable String version,
                                                     @PathVariable String labelName) {
        return Result.success(objectTypeService.getObjectType(domainName, version, labelName));
    }

    @GetMapping("/{domainName}/{version}/object-types/{labelName}/children")
    public Result<List<OntologyObjectType>> getChildTypes(@PathVariable String domainName,
                                                           @PathVariable String version,
                                                           @PathVariable String labelName) {
        return Result.success(objectTypeService.getChildTypes(domainName, version, labelName));
    }

    // ===== Property APIs =====

    @PostMapping("/{domainName}/{version}/properties")
    public Result<OntologyProperty> createProperty(@PathVariable String domainName,
                                                    @PathVariable String version,
                                                    @RequestBody OntologyProperty property) {
        property.setDomainName(domainName);
        property.setVersion(version);
        return Result.success(propertyService.createProperty(property));
    }

    @GetMapping("/{domainName}/{version}/object-types/{ownerLabel}/properties")
    public Result<List<OntologyProperty>> listProperties(@PathVariable String domainName,
                                                          @PathVariable String version,
                                                          @PathVariable String ownerLabel,
                                                          @RequestParam(required = false, defaultValue = "false") boolean visibleOnly) {
        if (visibleOnly) {
            return Result.success(propertyService.getVisibleProperties(domainName, version, ownerLabel));
        }
        return Result.success(propertyService.getPropertiesByOwner(domainName, version, ownerLabel));
    }

    // ===== Relationship APIs =====

    @PostMapping("/{domainName}/{version}/relationships")
    public Result<OntologyRelationship> createRelationship(@PathVariable String domainName,
                                                            @PathVariable String version,
                                                            @RequestBody OntologyRelationship relationship) {
        relationship.setDomainName(domainName);
        relationship.setVersion(version);
        return Result.success(relationshipService.createRelationship(relationship));
    }

    @GetMapping("/{domainName}/{version}/relationships")
    public Result<List<OntologyRelationship>> listRelationships(@PathVariable String domainName,
                                                                 @PathVariable String version) {
        return Result.success(relationshipService.getRelationships(domainName, version));
    }

    @GetMapping("/{domainName}/{version}/object-types/{sourceLabel}/outgoing-relationships")
    public Result<List<OntologyRelationship>> getOutgoingRelationships(@PathVariable String domainName,
                                                                        @PathVariable String version,
                                                                        @PathVariable String sourceLabel) {
        return Result.success(relationshipService.getOutgoingRelationships(domainName, version, sourceLabel));
    }
}
