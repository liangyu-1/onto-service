package com.onto.service.api.controller;

import com.onto.service.query.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 查询服务 REST API
 */
@RestController
@RequestMapping("/api/v1/query")
public class QueryController {

    @Autowired
    private QueryAdapter queryAdapter;

    @PostMapping("/semantic/{domainName}/{version}")
    public QueryResult executeSemanticQuery(@PathVariable String domainName,
                                             @PathVariable String version,
                                             @RequestBody SemanticQuery query) {
        return queryAdapter.executeSemanticQuery(domainName, version, query);
    }

    @PostMapping("/graph/{domainName}/{version}")
    public QueryResult executeGraphQuery(@PathVariable String domainName,
                                          @PathVariable String version,
                                          @RequestBody GraphQuery query) {
        return queryAdapter.executeGraphQuery(domainName, version, query);
    }

    @PostMapping("/logic/{domainName}/{version}")
    public QueryResult executeLogicQuery(@PathVariable String domainName,
                                          @PathVariable String version,
                                          @RequestBody LogicQuery query) {
        return queryAdapter.executeLogicQuery(domainName, version, query);
    }

    @PostMapping("/explain/{domainName}/{version}")
    public Explanation explainQuery(@PathVariable String domainName,
                                     @PathVariable String version,
                                     @RequestBody SemanticQuery query) {
        return queryAdapter.explainQuery(domainName, version, query);
    }
}
