package com.onto.service.api.controller;

import com.onto.service.catalog.OntologyCatalogBuilder;
import com.onto.service.catalog.impl.OntologyCatalogBuilderImpl;
import com.onto.service.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * Catalog 管理 REST API
 */
@RestController
@RequestMapping("/api/v1/catalog")
public class CatalogController {

    @Autowired
    private OntologyCatalogBuilder catalogBuilder;

    @PostMapping("/build/{domainName}/{version}")
    public Result<OntologyCatalogBuilderImpl.CatalogMetadata> buildCatalog(@PathVariable String domainName,
                                                                            @PathVariable String version) {
        Object metadata = catalogBuilder.buildCatalog(domainName, version);
        return Result.success((OntologyCatalogBuilderImpl.CatalogMetadata) metadata);
    }

    @PostMapping("/refresh/{domainName}/{version}")
    public Result<String> refreshCatalog(@PathVariable String domainName,
                                          @PathVariable String version) {
        catalogBuilder.refreshCatalog(domainName, version);
        return Result.success("Catalog refreshed");
    }
}
