package com.onto.oaas.service;

import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class TBoxIndexBuilder {

    public List<TBoxIndexDocument> buildFromSnapshot(TBoxSnapshot snapshot) {
        List<TBoxIndexDocument> docs = new ArrayList<>();
        if (snapshot == null || snapshot.getDomains() == null) {
            return docs;
        }
        snapshot.getDomains().forEach((domainKey, domain) -> {
            docs.add(buildFromDomain(domainKey, domain));
            if (domain.getTypes() != null) {
                domain.getTypes().forEach((typeKey, type) -> {
                    docs.add(buildFromType(domainKey, typeKey, type));
                    if (type.getProperties() != null) {
                        type.getProperties().forEach((propertyKey, property) ->
                                docs.add(buildFromProperty(domainKey, typeKey, propertyKey, property)));
                    }
                    if (type.getRelationships() != null) {
                        type.getRelationships().forEach((relationshipKey, relationship) ->
                                docs.add(buildFromRelationship(domainKey, typeKey, relationshipKey, relationship)));
                    }
                    if (type.getFunctions() != null) {
                        type.getFunctions().forEach((functionKey, function) -> {
                            docs.add(buildFromFunction(domainKey, typeKey, functionKey, function));
                            if (function.getRules() != null) {
                                function.getRules().forEach((ruleKey, rule) ->
                                        docs.add(buildFromRule(domainKey, typeKey, functionKey, ruleKey, rule)));
                            }
                        });
                    }
                });
            }
        });
        log.info("Built {} index documents from snapshot", docs.size());
        return docs;
    }

    public TBoxIndexDocument buildFromDomain(String domainKey, DomainDef domain) {
        String objectPath = generateObjectPath(domainKey);
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(TBoxObjectType.DOMAIN)
                .name(domain.getName())
                .description(domain.getDescription())
                .textForEmbedding(generateEmbeddingText(domain.getName(), domain.getDescription()))
                .keywords(generateKeywords(domain.getName(), domain.getDescription()))
                .domainKey(domainKey)
                .updatedTime(Instant.now())
                .build();
    }

    public TBoxIndexDocument buildFromType(String domainKey, String typeKey, TypeDef type) {
        String objectPath = generateObjectPath(domainKey, typeKey);
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(TBoxObjectType.TYPE)
                .name(type.getName())
                .description(type.getDescription())
                .textForEmbedding(generateEmbeddingText(type.getName(), type.getDescription(), type.getDisplayProperty()))
                .keywords(generateKeywords(type.getName(), type.getDescription(), type.getDisplayProperty()))
                .domainKey(domainKey)
                .typeKey(typeKey)
                .updatedTime(Instant.now())
                .build();
    }

    public TBoxIndexDocument buildFromProperty(String domainKey, String typeKey, String propertyKey, PropertyDef property) {
        String objectPath = generateObjectPath(domainKey, typeKey, "properties", propertyKey);
        Binding binding = property.getBinding();
        String bindingText = binding != null
                ? String.format("%s.%s.%s", binding.getSchema(), binding.getTable(), binding.getColumn())
                : null;
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(TBoxObjectType.PROPERTY)
                .name(property.getName())
                .description(property.getDescription())
                .textForEmbedding(generateEmbeddingText(property.getName(), property.getDescription(), property.getType(), bindingText))
                .keywords(generateKeywords(property.getName(), property.getDescription(), property.getType(), bindingText))
                .domainKey(domainKey)
                .typeKey(typeKey)
                .binding(binding)
                .updatedTime(Instant.now())
                .build();
    }

    public TBoxIndexDocument buildFromRelationship(String domainKey, String typeKey, String relationshipKey, RelationshipDef relationship) {
        String objectPath = generateObjectPath(domainKey, typeKey, "relationships", relationshipKey);
        String extras = relationship.getCardinality() != null ? relationship.getCardinality().name() : null;
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(TBoxObjectType.RELATIONSHIP)
                .name(relationship.getName())
                .description(relationship.getDescription())
                .textForEmbedding(generateEmbeddingText(relationship.getName(), relationship.getDescription(), extras))
                .keywords(generateKeywords(relationship.getName(), relationship.getDescription(), extras))
                .domainKey(domainKey)
                .typeKey(typeKey)
                .updatedTime(Instant.now())
                .build();
    }

    public TBoxIndexDocument buildFromFunction(String domainKey, String typeKey, String functionKey, FunctionDef function) {
        String objectPath = generateObjectPath(domainKey, typeKey, "functions", functionKey);
        String dimensions = function.getDimensions() != null ? String.join(", ", function.getDimensions()) : null;
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(TBoxObjectType.FUNCTION)
                .name(function.getName())
                .description(function.getDescription())
                .textForEmbedding(generateEmbeddingText(function.getName(), function.getDescription(), dimensions))
                .keywords(generateKeywords(function.getName(), function.getDescription(), dimensions))
                .domainKey(domainKey)
                .typeKey(typeKey)
                .functionKey(functionKey)
                .updatedTime(Instant.now())
                .build();
    }

    public TBoxIndexDocument buildFromRule(String domainKey, String typeKey, String functionKey, String ruleKey, RuleDef rule) {
        String objectPath = generateObjectPath(domainKey, typeKey, "functions", functionKey, "rules", ruleKey);
        String ruleType = rule.getType();
        String definition = rule.getDefinition();
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(TBoxObjectType.RULE)
                .name(rule.getName())
                .description(rule.getDescription())
                .textForEmbedding(generateEmbeddingText(rule.getName(), rule.getDescription(), ruleType, definition))
                .keywords(generateKeywords(rule.getName(), rule.getDescription(), ruleType, definition))
                .domainKey(domainKey)
                .typeKey(typeKey)
                .functionKey(functionKey)
                .ruleKey(ruleKey)
                .ruleType(ruleType)
                .definition(definition)
                .updatedTime(Instant.now())
                .build();
    }

    private String generateObjectPath(String... parts) {
        return String.join(".", parts);
    }

    private String generateEmbeddingText(String name, String description, String... extras) {
        StringBuilder sb = new StringBuilder();
        if (name != null) {
            sb.append(name).append(" ");
        }
        if (description != null) {
            sb.append(description).append(" ");
        }
        for (String extra : extras) {
            if (extra != null) {
                sb.append(extra).append(" ");
            }
        }
        return sb.toString().trim();
    }

    private List<String> generateKeywords(String name, String description, String... extras) {
        List<String> keywords = new ArrayList<>();
        if (name != null) {
            keywords.add(name);
        }
        if (description != null) {
            keywords.addAll(Arrays.asList(description.split("\\s+")));
        }
        for (String extra : extras) {
            if (extra != null) {
                keywords.add(extra);
            }
        }
        return keywords.stream()
                .filter(k -> k != null && !k.isBlank())
                .distinct()
                .collect(Collectors.toList());
    }
}
