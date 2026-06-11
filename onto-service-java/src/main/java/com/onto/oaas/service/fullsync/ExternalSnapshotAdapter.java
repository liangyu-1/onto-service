package com.onto.oaas.service.fullsync;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import java.time.Instant;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 外部系统快照适配器。
 *
 * <p>将外部系统的快照格式（如 TPC-H 的 {"name":"TPC-H","types":{...}}）
 * 转换为本系统内部的 {@link TBoxSnapshot} 格式。</p>
 */
@Slf4j
@Component
public class ExternalSnapshotAdapter {

    private final ObjectMapper objectMapper;

    public ExternalSnapshotAdapter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * 将外部系统的 JSON 响应转换为 TBoxSnapshot。
     *
     * <p>外部格式示例：</p>
     * <pre>
     * {
     *   "name": "TPC-H",
     *   "description": "...",
     *   "types": {
     *     "orders": { "name": "orders", "properties": {...}, ... },
     *     "customer": { ... }
     *   }
     * }
     * </pre>
     *
     * <p>转换为内部格式：</p>
     * <pre>
     * {
     *   "timestamp": "2024-...",
     *   "domains": {
     *     "tpch": {
     *       "name": "TPC-H",
     *       "description": "...",
     *       "types": { "orders": {...}, "customer": {...} }
     *     }
     *   },
     *   "code": "200",
     *   "message": "ok"
     * }
     * </pre>
     */
    public TBoxSnapshot adapt(JsonNode externalResponse) {
        if (externalResponse == null || externalResponse.isNull()) {
            return null;
        }

        String domainName = externalResponse.has("name")
                ? externalResponse.get("name").asText("default")
                : "default";
        String domainKey = domainName.toLowerCase().replaceAll("[^a-z0-9_]", "_");

        String description = externalResponse.has("description")
                ? externalResponse.get("description").asText("")
                : "";

        DomainDef domain = DomainDef.builder()
                .name(domainName)
                .description(description)
                .types(new HashMap<>())
                .build();

        // 解析 types
        if (externalResponse.has("types") && externalResponse.get("types").isObject()) {
            JsonNode typesNode = externalResponse.get("types");
            Iterator<Map.Entry<String, JsonNode>> fields = typesNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                String typeKey = entry.getKey();
                JsonNode typeNode = entry.getValue();
                TypeDef typeDef = parseTypeDef(typeNode);
                if (typeDef != null) {
                    domain.getTypes().put(typeKey, typeDef);
                }
            }
        }

        TBoxSnapshot snapshot = new TBoxSnapshot();
        snapshot.setTimestamp(Instant.now().toString());
        snapshot.setCode("200");
        snapshot.setMessage("ok");
        snapshot.getDomains().put(domainKey, domain);

        log.info("Adapted external snapshot: domain={}, types={}", domainKey, domain.getTypes().size());
        return snapshot;
    }

    private TypeDef parseTypeDef(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }

        TypeDef.TypeDefBuilder builder = TypeDef.builder()
                .properties(new HashMap<>())
                .relationships(new HashMap<>())
                .functions(new HashMap<>());

        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }
        if (node.has("display_property")) {
            builder.displayProperty(node.get("display_property").asText());
        }

        // 解析 properties
        if (node.has("properties") && node.get("properties").isObject()) {
            JsonNode propsNode = node.get("properties");
            Iterator<Map.Entry<String, JsonNode>> fields = propsNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                PropertyDef prop = parsePropertyDef(entry.getValue());
                if (prop != null) {
                    builder.build().getProperties().put(entry.getKey(), prop);
                }
            }
        }

        // 解析 relationships
        if (node.has("relationships") && node.get("relationships").isObject()) {
            JsonNode relsNode = node.get("relationships");
            Iterator<Map.Entry<String, JsonNode>> fields = relsNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                RelationshipDef rel = parseRelationshipDef(entry.getValue());
                if (rel != null) {
                    builder.build().getRelationships().put(entry.getKey(), rel);
                }
            }
        }

        // 解析 functions
        if (node.has("functions") && node.get("functions").isObject()) {
            JsonNode funcsNode = node.get("functions");
            Iterator<Map.Entry<String, JsonNode>> fields = funcsNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                FunctionDef func = parseFunctionDef(entry.getValue());
                if (func != null) {
                    builder.build().getFunctions().put(entry.getKey(), func);
                }
            }
        }

        return builder.build();
    }

    private PropertyDef parsePropertyDef(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }
        PropertyDef.PropertyDefBuilder builder = PropertyDef.builder();
        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("type")) {
            builder.type(node.get("type").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }
        if (node.has("binding") && node.get("binding").isObject()) {
            JsonNode bindingNode = node.get("binding");
            Long datasource = null;
            if (bindingNode.has("datasource")) {
                JsonNode dsNode = bindingNode.get("datasource");
                if (dsNode.isNumber()) {
                    datasource = dsNode.asLong();
                } else if (dsNode.isTextual()) {
                    try {
                        datasource = Long.parseLong(dsNode.asText());
                    } catch (NumberFormatException ignored) {}
                }
            }
            Binding binding = Binding.builder()
                    .datasource(datasource)
                    .schema(bindingNode.has("schema") ? bindingNode.get("schema").asText() : null)
                    .database(bindingNode.has("database") ? bindingNode.get("database").asText() : null)
                    .table(bindingNode.has("table") ? bindingNode.get("table").asText() : null)
                    .column(bindingNode.has("column") ? bindingNode.get("column").asText() : null)
                    .build();
            builder.binding(binding);
        }
        if (node.has("pk_column")) {
            builder.pkColumn(node.get("pk_column").asBoolean(false));
        }
        return builder.build();
    }

    private RelationshipDef parseRelationshipDef(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }
        RelationshipDef.RelationshipDefBuilder builder = RelationshipDef.builder();
        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }
        if (node.has("cardinality")) {
            try {
                builder.cardinality(com.onto.oaas.model.enums.Cardinality.valueOf(node.get("cardinality").asText()));
            } catch (IllegalArgumentException ignored) {}
        }
        return builder.build();
    }

    private FunctionDef parseFunctionDef(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }
        FunctionDef.FunctionDefBuilder builder = FunctionDef.builder()
                .rules(new HashMap<>());

        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }
        if (node.has("dimensions") && node.get("dimensions").isArray()) {
            java.util.List<String> dims = new java.util.ArrayList<>();
            for (JsonNode dim : node.get("dimensions")) {
                dims.add(dim.asText());
            }
            builder.dimensions(dims);
        }

        // 解析 rules
        if (node.has("rules") && node.get("rules").isObject()) {
            JsonNode rulesNode = node.get("rules");
            Iterator<Map.Entry<String, JsonNode>> fields = rulesNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                RuleDef rule = parseRuleDef(entry.getValue());
                if (rule != null) {
                    builder.build().getRules().put(entry.getKey(), rule);
                }
            }
        }

        return builder.build();
    }

    private RuleDef parseRuleDef(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }
        RuleDef.RuleDefBuilder builder = RuleDef.builder();
        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }
        if (node.has("type")) {
            builder.type(node.get("type").asText());
        }
        if (node.has("definition")) {
            builder.definition(node.get("definition").asText());
        }
        return builder.build();
    }
}
