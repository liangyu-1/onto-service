package com.onto.oaas.service.fullsync;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.Cardinality;
import com.onto.oaas.model.enums.JoinType;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 本体管理平台（Ontology Management Platform）快照适配器。
 *
 * <p>将本体管理平台的 OpenAPI 响应格式转换为 OaaS 内部的 {@link TBoxSnapshot} 格式。</p>
 *
 * <p><b>外部格式特征：</b></p>
 * <ul>
 *   <li>外层有 code/message/timestamp 包装</li>
 *   <li>domains 为 map&lt;long, Domain&gt;，key 是数字 ID</li>
 *   <li>types 为 map&lt;long, Type&gt;，key 是数字 ID</li>
 *   <li>properties 为 map&lt;long, Property&gt;，key 是数字 ID</li>
 *   <li>relationships 为 map&lt;long, Relation&gt;，key 是数字 ID</li>
 *   <li>functions 结构为 {"rules": {ruleId: Rule}}</li>
 *   <li>binding.datasource 为 long 类型</li>
 *   <li>linkProperties 格式为 [{"srcId": "tgtId"}, ...]</li>
 * </ul>
 *
 * <p><b>内部格式特征：</b></p>
 * <ul>
 *   <li>domains 为 map&lt;String, DomainDef&gt;，key 是 domain 编码（name 的小写）</li>
 *   <li>types/properties/relationships/functions 的 key 是编码名称</li>
 *   <li>binding.datasource 为 Long 类型</li>
 * </ul>
 */
@Slf4j
@Component
public class OntologyMgmtSnapshotAdapter {

    private final ObjectMapper objectMapper;

    public OntologyMgmtSnapshotAdapter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * 将本体管理平台的 JSON 响应适配为内部 TBoxSnapshot 格式。
     */
    public TBoxSnapshot adapt(JsonNode externalResponse) {
        if (externalResponse == null || externalResponse.isNull()) {
            return null;
        }

        // 检查外层包装
        JsonNode domainsNode;
        if (externalResponse.has("domains")) {
            // 完整响应: {"code": 200, "message": "success", "domains": {...}}
            domainsNode = externalResponse.get("domains");
        } else if (externalResponse.has("types")) {
            // 可能是旧格式或单 domain 格式
            return null; // 不处理，交给其他适配器
        } else {
            log.warn("Unrecognized external response format, missing 'domains' field");
            return null;
        }

        TBoxSnapshot snapshot = new TBoxSnapshot();
        snapshot.setTimestamp(Instant.now().toString());
        snapshot.setCode(externalResponse.has("code") ? externalResponse.get("code").asText("200") : "200");
        snapshot.setMessage(externalResponse.has("message") ? externalResponse.get("message").asText("success") : "success");

        // 解析所有 domains
        if (domainsNode != null && domainsNode.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> domainFields = domainsNode.fields();
            while (domainFields.hasNext()) {
                Map.Entry<String, JsonNode> domainEntry = domainFields.next();
                String domainId = domainEntry.getKey();
                JsonNode domainNode = domainEntry.getValue();
                DomainDef domain = parseDomain(domainNode, domainId);
                if (domain != null) {
                    String domainKey = sanitizeKey(domain.getName());
                    snapshot.getDomains().put(domainKey, domain);
                }
            }
        }

        log.info("Adapted ontology management platform snapshot: domains={}, totalTypes={}",
                snapshot.getDomains().size(),
                snapshot.getDomains().values().stream()
                        .mapToInt(d -> d.getTypes() != null ? d.getTypes().size() : 0)
                        .sum());
        return snapshot;
    }

    private DomainDef parseDomain(JsonNode node, String domainId) {
        if (node == null || !node.isObject()) {
            return null;
        }

        DomainDef.DomainDefBuilder builder = DomainDef.builder()
                .id(domainId)
                .types(new HashMap<>());

        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("displayName")) {
            builder.displayName(node.get("displayName").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }

        DomainDef domain = builder.build();

        // 解析 types (map<long, Type>)
        if (node.has("types") && node.get("types").isObject()) {
            JsonNode typesNode = node.get("types");
            Iterator<Map.Entry<String, JsonNode>> typeFields = typesNode.fields();
            while (typeFields.hasNext()) {
                Map.Entry<String, JsonNode> typeEntry = typeFields.next();
                String typeId = typeEntry.getKey();
                JsonNode typeNode = typeEntry.getValue();
                TypeDef typeDef = parseTypeDef(typeNode, typeId, domainId);
                if (typeDef != null) {
                    String typeKey = sanitizeKey(typeDef.getName());
                    domain.getTypes().put(typeKey, typeDef);
                }
            }
        }

        return domain;
    }

    private TypeDef parseTypeDef(JsonNode node, String typeId, String domainId) {
        if (node == null || !node.isObject()) {
            return null;
        }

        TypeDef.TypeDefBuilder builder = TypeDef.builder()
                .id(typeId)
                .properties(new HashMap<>())
                .relationships(new HashMap<>())
                .functions(new HashMap<>());

        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("displayName")) {
            builder.displayName(node.get("displayName").asText());
        }
        if (node.has("description")) {
            builder.description(node.get("description").asText());
        }
        if (node.has("displayProperty")) {
            JsonNode dpNode = node.get("displayProperty");
            if (!dpNode.isNull()) {
                builder.displayProperty(dpNode.asText());
            }
        }

        TypeDef typeDef = builder.build();

        // 解析 properties (map<long, Property>)
        if (node.has("properties") && node.get("properties").isObject()) {
            JsonNode propsNode = node.get("properties");
            Iterator<Map.Entry<String, JsonNode>> propFields = propsNode.fields();
            while (propFields.hasNext()) {
                Map.Entry<String, JsonNode> propEntry = propFields.next();
                String propId = propEntry.getKey();
                PropertyDef prop = parsePropertyDef(propEntry.getValue(), propId);
                if (prop != null) {
                    String propKey = sanitizeKey(prop.getName());
                    typeDef.getProperties().put(propKey, prop);
                }
            }
        }

        // 解析 relationships (map<long, Relation>)
        if (node.has("relationships") && node.get("relationships").isObject()) {
            JsonNode relsNode = node.get("relationships");
            Iterator<Map.Entry<String, JsonNode>> relFields = relsNode.fields();
            while (relFields.hasNext()) {
                Map.Entry<String, JsonNode> relEntry = relFields.next();
                String relId = relEntry.getKey();
                RelationshipDef rel = parseRelationshipDef(relEntry.getValue(), relId, domainId, typeId);
                if (rel != null) {
                    String relKey = sanitizeKey(rel.getName());
                    typeDef.getRelationships().put(relKey, rel);
                }
            }
        }

        // 解析 functions (格式: {"rules": {ruleId: Rule}})
        if (node.has("functions") && node.get("functions").isObject()) {
            JsonNode funcsNode = node.get("functions");
            if (funcsNode.has("rules") && funcsNode.get("rules").isObject()) {
                JsonNode rulesNode = funcsNode.get("rules");
                Iterator<Map.Entry<String, JsonNode>> ruleFields = rulesNode.fields();
                while (ruleFields.hasNext()) {
                    Map.Entry<String, JsonNode> ruleEntry = ruleFields.next();
                    String ruleId = ruleEntry.getKey();
                    FunctionDef func = parseFunctionDef(ruleEntry.getValue(), ruleId);
                    if (func != null) {
                        String funcKey = sanitizeKey(func.getName());
                        typeDef.getFunctions().put(funcKey, func);
                    }
                }
            }
        }

        return typeDef;
    }

    private PropertyDef parsePropertyDef(JsonNode node, String propId) {
        if (node == null || !node.isObject()) {
            return null;
        }
        PropertyDef.PropertyDefBuilder builder = PropertyDef.builder().id(propId);
        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("displayName")) {
            builder.displayName(node.get("displayName").asText());
        }
        if (node.has("type")) {
            builder.type(node.get("type").asText());
        }
        if (node.has("description")) {
            JsonNode descNode = node.get("description");
            if (!descNode.isNull()) {
                builder.description(descNode.asText());
            }
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
                    .schema(getTextOrNull(bindingNode, "schema"))
                    .database(getTextOrNull(bindingNode, "database"))
                    .table(getTextOrNull(bindingNode, "table"))
                    .column(getTextOrNull(bindingNode, "column"))
                    .build();
            builder.binding(binding);
        }
        if (node.has("pkColumn")) {
            builder.pkColumn(node.get("pkColumn").asBoolean(false));
        }
        return builder.build();
    }

    private RelationshipDef parseRelationshipDef(JsonNode node, String relId, String domainId, String typeId) {
        if (node == null || !node.isObject()) {
            return null;
        }
        RelationshipDef.RelationshipDefBuilder builder = RelationshipDef.builder();
        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("displayName")) {
            builder.displayName(node.get("displayName").asText());
        }
        if (node.has("description")) {
            JsonNode descNode = node.get("description");
            if (!descNode.isNull()) {
                builder.description(descNode.asText());
            }
        }
        if (node.has("cardinality")) {
            try {
                String cardStr = node.get("cardinality").asText().toUpperCase().replace("-", "_");
                builder.cardinality(Cardinality.valueOf(cardStr));
            } catch (IllegalArgumentException e) {
                log.debug("Unknown cardinality: {}", node.get("cardinality").asText());
            }
        }
        if (node.has("type")) {
            try {
                String joinStr = node.get("type").asText().toUpperCase().replace("_", "_");
                builder.type(JoinType.valueOf(joinStr));
            } catch (IllegalArgumentException e) {
                log.debug("Unknown join type: {}", node.get("type").asText());
            }
        }

        // 解析 linkProperties
        // 格式: [{"srcDomainId.srcTypeId.srcPropId": "tgtDomainId.tgtTypeId.tgtPropId"}, ...]
        if (node.has("linkProperties") && node.get("linkProperties").isArray()) {
            List<Map<String, String>> linkProps = new ArrayList<>();
            for (JsonNode lpNode : node.get("linkProperties")) {
                if (lpNode.isObject()) {
                    Map<String, String> lpMap = new HashMap<>();
                    Iterator<Map.Entry<String, JsonNode>> fields = lpNode.fields();
                    while (fields.hasNext()) {
                        Map.Entry<String, JsonNode> entry = fields.next();
                        lpMap.put(entry.getKey(), entry.getValue().asText());
                    }
                    if (!lpMap.isEmpty()) {
                        linkProps.add(lpMap);
                    }
                }
            }
            if (!linkProps.isEmpty()) {
                builder.linkProperties(linkProps);
            }
        }

        return builder.build();
    }

    private FunctionDef parseFunctionDef(JsonNode node, String ruleId) {
        if (node == null || !node.isObject()) {
            return null;
        }
        FunctionDef.FunctionDefBuilder builder = FunctionDef.builder()
                .rules(new HashMap<>());

        if (node.has("name")) {
            builder.name(node.get("name").asText());
        }
        if (node.has("displayName")) {
            builder.displayName(node.get("displayName").asText());
        }
        if (node.has("description")) {
            JsonNode descNode = node.get("description");
            if (!descNode.isNull()) {
                builder.description(descNode.asText());
            }
        }
        if (node.has("type")) {
            builder.type(node.get("type").asText());
        }
        if (node.has("definition")) {
            JsonNode defNode = node.get("definition");
            if (!defNode.isNull()) {
                builder.definition(defNode.asText());
            }
        }

        return builder.build();
    }

    /**
     * 将名称转换为合法的 key。
     * 保留中文字符、字母、数字、下划线，替换其他字符为下划线。
     */
    private String sanitizeKey(String name) {
        if (name == null || name.isEmpty()) {
            return "unknown";
        }
        // 保留中文字符(\u4e00-\u9fff)、字母、数字、下划线
        String sanitized = name
                .replaceAll("[^\\u4e00-\\u9fffa-zA-Z0-9_]", "_")
                .replaceAll("_+", "_")
                .replaceAll("^_|_$", "");
        return sanitized.isEmpty() ? "unknown" : sanitized;
    }

    private String getTextOrNull(JsonNode node, String fieldName) {
        if (node.has(fieldName)) {
            JsonNode field = node.get(fieldName);
            if (!field.isNull()) {
                return field.asText();
            }
        }
        return null;
    }
}
