package com.onto.oaas.service.retrieval;

import com.onto.oaas.dto.TBoxObjectDetailResponse;
import com.onto.oaas.exception.OaaSException;
import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.util.ObjectPathUtil;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class TBoxContextService {

    private final TBoxGraphRepository graphRepository;

    public TBoxObjectDetailResponse getObjectDetail(String objectPath) {
        TBoxObjectType objectType = ObjectPathUtil.getObjectTypeFromPath(objectPath);
        String domainKey = ObjectPathUtil.getDomainKey(objectPath);
        String typeKey = ObjectPathUtil.getTypeKey(objectPath);

        Map<String, Object> context = new HashMap<>();
        String name = null;
        String description = null;

        switch (objectType) {
            case DOMAIN -> {
                Optional<DomainDef> domainOpt = graphRepository.findDomainByKey(domainKey);
                if (domainOpt.isPresent()) {
                    DomainDef d = domainOpt.get();
                    name = d.getName();
                    description = d.getDescription();
                    context.put("typeCount", d.getTypes() != null ? d.getTypes().size() : 0);
                }
            }
            case TYPE -> {
                Optional<TypeDef> typeOpt = graphRepository.findTypeByPath(objectPath);
                if (typeOpt.isPresent()) {
                    TypeDef t = typeOpt.get();
                    name = t.getName();
                    description = t.getDescription();
                    context.put("propertyCount", t.getProperties() != null ? t.getProperties().size() : 0);
                    context.put("relationshipCount", t.getRelationships() != null ? t.getRelationships().size() : 0);
                    context.put("functionCount", t.getFunctions() != null ? t.getFunctions().size() : 0);
                }
            }
            case PROPERTY -> {
                Optional<PropertyDef> propOpt = graphRepository.findPropertyByPath(objectPath);
                if (propOpt.isPresent()) {
                    PropertyDef p = propOpt.get();
                    name = p.getName();
                    description = p.getDescription();
                    if (p.getBinding() != null) {
                        context.put("binding", p.getBinding());
                    }
                }
            }
            case RELATIONSHIP -> {
                if (domainKey != null && typeKey != null) {
                    String relKey = ObjectPathUtil.getRelationshipKey(objectPath);
                    List<RelationshipDef> rels = graphRepository.findRelationshipsByType(domainKey, typeKey);
                    Optional<RelationshipDef> relOpt = rels.stream()
                            .filter(r -> r != null && relKey != null && relKey.equals(r.getName()))
                            .findFirst();
                    if (relOpt.isPresent()) {
                        RelationshipDef r = relOpt.get();
                        name = r.getName();
                        description = r.getDescription();
                        context.put("cardinality", r.getCardinality());
                        context.put("joinType", r.getType());
                    }
                }
            }
            case FUNCTION -> {
                if (domainKey != null && typeKey != null) {
                    String funcKey = ObjectPathUtil.getFunctionKey(objectPath);
                    List<FunctionDef> funcs = graphRepository.findFunctionsByType(domainKey, typeKey);
                    Optional<FunctionDef> funcOpt = funcs.stream()
                            .filter(f -> f != null && funcKey != null && funcKey.equals(f.getName()))
                            .findFirst();
                    if (funcOpt.isPresent()) {
                        FunctionDef f = funcOpt.get();
                        name = f.getName();
                        description = f.getDescription();
                        context.put("dimensions", f.getDimensions());
                        context.put("ruleCount", f.getRules() != null ? f.getRules().size() : 0);
                    }
                }
            }
            case RULE -> {
                if (domainKey != null && typeKey != null) {
                    String funcKey = ObjectPathUtil.getFunctionKey(objectPath);
                    String ruleKey = ObjectPathUtil.getRuleKey(objectPath);
                    if (funcKey != null) {
                        List<RuleDef> rules = graphRepository.findRulesByFunction(domainKey, typeKey, funcKey);
                        Optional<RuleDef> ruleOpt = rules.stream()
                                .filter(r -> r != null && ruleKey != null && ruleKey.equals(r.getName()))
                                .findFirst();
                        if (ruleOpt.isPresent()) {
                            RuleDef r = ruleOpt.get();
                            name = r.getName();
                            description = r.getDescription();
                            context.put("type", r.getType());
                            context.put("definition", r.getDefinition());
                        }
                    }
                }
            }
            default -> throw new OaaSException("UNSUPPORTED_TYPE", "Unsupported object type: " + objectType);
        }

        if (name == null) {
            throw new OaaSException("OBJECT_NOT_FOUND", "Object not found for path: " + objectPath);
        }

        return TBoxObjectDetailResponse.builder()
                .objectPath(objectPath)
                .objectType(objectType)
                .name(name)
                .description(description)
                .context(context)
                .build();
    }
}
