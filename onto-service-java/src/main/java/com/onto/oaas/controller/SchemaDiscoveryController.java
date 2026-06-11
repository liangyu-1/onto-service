package com.onto.oaas.controller;

import com.onto.oaas.dto.DomainSummaryDto;
import com.onto.oaas.dto.GraphEdgeTypeDto;
import com.onto.oaas.dto.GraphNodeTypeDto;
import com.onto.oaas.dto.SchemaDiscoveryResponse;
import com.onto.oaas.dto.TypeSummaryDto;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.repository.TBoxGraphRepository;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/tbox")
@RequiredArgsConstructor
public class SchemaDiscoveryController {

    private final TBoxGraphRepository graphRepository;

    @GetMapping("/schema")
    public ResponseEntity<SchemaDiscoveryResponse> getSchema() {
        List<DomainDef> domains = graphRepository.findAllDomains();
        Map<String, DomainSummaryDto> domainMap = new HashMap<>();

        for (DomainDef domain : domains) {
            String domainKey = domain.getName(); // fallback if key not present
            Map<String, TypeSummaryDto> typeMap = new HashMap<>();
            int typeCount = 0;

            if (domain.getTypes() != null) {
                typeCount = domain.getTypes().size();
                for (Map.Entry<String, TypeDef> entry : domain.getTypes().entrySet()) {
                    TypeDef type = entry.getValue();
                    TypeSummaryDto typeDto = TypeSummaryDto.builder()
                            .name(type.getName())
                            .description(type.getDescription())
                            .propertyCount(type.getProperties() != null ? type.getProperties().size() : 0)
                            .relationshipCount(type.getRelationships() != null ? type.getRelationships().size() : 0)
                            .functionCount(type.getFunctions() != null ? type.getFunctions().size() : 0)
                            .build();
                    typeMap.put(entry.getKey(), typeDto);
                }
            }

            DomainSummaryDto domainDto = DomainSummaryDto.builder()
                    .name(domain.getName())
                    .description(domain.getDescription())
                    .typeCount(typeCount)
                    .types(typeMap)
                    .build();

            domainMap.put(domain.getName(), domainDto);
        }

        SchemaDiscoveryResponse response = SchemaDiscoveryResponse.builder()
                .timestamp(Instant.now().toString())
                .domains(domainMap)
                .code("0")
                .message("success")
                .build();

        return ResponseEntity.ok(response);
    }

    @GetMapping("/graph/node-types")
    public ResponseEntity<List<GraphNodeTypeDto>> getNodeTypes() {
        return ResponseEntity.ok(List.of(
                GraphNodeTypeDto.builder().type("Domain").description("领域节点").build(),
                GraphNodeTypeDto.builder().type("Type").description("类型节点").build(),
                GraphNodeTypeDto.builder().type("Property").description("属性节点").build(),
                GraphNodeTypeDto.builder().type("Relationship").description("关系节点").build(),
                GraphNodeTypeDto.builder().type("Function").description("函数节点").build(),
                GraphNodeTypeDto.builder().type("Rule").description("规则节点").build()
        ));
    }

    @GetMapping("/graph/edge-types")
    public ResponseEntity<List<GraphEdgeTypeDto>> getEdgeTypes() {
        return ResponseEntity.ok(List.of(
                GraphEdgeTypeDto.builder().type("HAS_TYPE").source("Domain").target("Type").description("领域包含类型").build(),
                GraphEdgeTypeDto.builder().type("HAS_PROPERTY").source("Type").target("Property").description("类型包含属性").build(),
                GraphEdgeTypeDto.builder().type("HAS_RELATIONSHIP").source("Type").target("Relationship").description("类型包含关系").build(),
                GraphEdgeTypeDto.builder().type("HAS_FUNCTION").source("Type").target("Function").description("类型包含函数").build(),
                GraphEdgeTypeDto.builder().type("HAS_RULE").source("Function").target("Rule").description("函数包含规则").build(),
                GraphEdgeTypeDto.builder().type("LINK_TO").source("Relationship").target("Property").description("关系连接属性").build(),
                GraphEdgeTypeDto.builder().type("USES_DIMENSION").source("Function").target("Property").description("函数使用维度属性").build()
        ));
    }
}
