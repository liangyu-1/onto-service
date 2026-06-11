package com.onto.oaas.agent.storage;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.Direction;
import com.onto.oaas.repository.TBoxGraphRepository;
import java.util.List;
import java.util.Optional;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 图存储 Agent。
 *
 * <p>职责：代理所有图数据库操作（CRUD + 邻域查询），为其他 Agent 提供统一的图数据访问接口。</p>
 * <p>输入：{@link AgentMessageType#GRAPH_READ} / {@link AgentMessageType#GRAPH_WRITE}</p>
 * <p>输出：{@link AgentMessageType#GRAPH_RESULT}</p>
 */
@Slf4j
@Component
public class GraphAgent extends AbstractAgent {

    private final TBoxGraphRepository graphRepository;

    public GraphAgent(AgentBus agentBus, TBoxGraphRepository graphRepository) {
        super(agentBus);
        this.graphRepository = graphRepository;
        subscribeTo(AgentMessageType.GRAPH_READ, AgentMessageType.GRAPH_WRITE);
    }

    @Override
    public String getName() {
        return "GraphAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        switch (message.getType()) {
            case GRAPH_READ -> handleRead(message);
            case GRAPH_WRITE -> handleWrite(message);
            default -> log.warn("[{}] Unexpected message type: {}", getName(), message.getType());
        }
    }

    @SuppressWarnings("unchecked")
    private void handleRead(AgentMessage message) {
        String operation = message.getPayload("operation", String.class);
        Object result = null;

        switch (operation) {
            case "findDomain" -> {
                String domainKey = message.getPayload("domainKey", String.class);
                result = graphRepository.findDomainByKey(domainKey);
            }
            case "findType" -> {
                String typePath = message.getPayload("typePath", String.class);
                result = graphRepository.findTypeByPath(typePath);
            }
            case "findProperty" -> {
                String propertyPath = message.getPayload("propertyPath", String.class);
                result = graphRepository.findPropertyByPath(propertyPath);
            }
            case "findAllDomains" -> result = graphRepository.findAllDomains();
            case "findTypesByDomain" -> {
                String domainKey = message.getPayload("domainKey", String.class);
                result = graphRepository.findTypesByDomain(domainKey);
            }
            case "findNeighbors" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                Direction direction = message.getPayload("direction", Direction.class);
                List<String> relationTypes = message.getPayload("relationTypes", List.class);
                result = graphRepository.findNeighbors(objectPath, direction, relationTypes);
            }
            case "exists" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                result = graphRepository.exists(objectPath);
            }
            case "countObjects" -> result = graphRepository.countObjects();
            default -> log.warn("[{}] Unknown read operation: {}", getName(), operation);
        }

        publish(message.reply(AgentMessageType.GRAPH_RESULT)
                .putPayload("operation", operation)
                .putPayload("result", result));
    }

    @SuppressWarnings("unchecked")
    private void handleWrite(AgentMessage message) {
        String operation = message.getPayload("operation", String.class);

        switch (operation) {
            case "saveSnapshot" -> {
                TBoxSnapshot snapshot = message.getPayload("snapshot", TBoxSnapshot.class);
                graphRepository.saveSnapshot(snapshot);
            }
            case "saveDomain" -> {
                DomainDef domain = message.getPayload("domain", DomainDef.class);
                String domainKey = message.getPayload("domainKey", String.class);
                graphRepository.saveDomain(domain, domainKey);
            }
            case "saveType" -> {
                TypeDef type = message.getPayload("type", TypeDef.class);
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                graphRepository.saveType(type, domainKey, typeKey);
            }
            case "saveProperty" -> {
                PropertyDef property = message.getPayload("property", PropertyDef.class);
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                String propertyKey = message.getPayload("propertyKey", String.class);
                graphRepository.saveProperty(property, domainKey, typeKey, propertyKey);
            }
            case "saveRelationship" -> {
                RelationshipDef relationship = message.getPayload("relationship", RelationshipDef.class);
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                String relationshipKey = message.getPayload("relationshipKey", String.class);
                graphRepository.saveRelationship(relationship, domainKey, typeKey, relationshipKey);
            }
            case "saveFunction" -> {
                FunctionDef function = message.getPayload("function", FunctionDef.class);
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                String functionKey = message.getPayload("functionKey", String.class);
                graphRepository.saveFunction(function, domainKey, typeKey, functionKey);
            }
            case "saveRule" -> {
                RuleDef rule = message.getPayload("rule", RuleDef.class);
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                String functionKey = message.getPayload("functionKey", String.class);
                String ruleKey = message.getPayload("ruleKey", String.class);
                graphRepository.saveRule(rule, domainKey, typeKey, functionKey, ruleKey);
            }
            case "clearAll" -> graphRepository.clearAll();
            case "deleteDomain" -> {
                String domainKey = message.getPayload("domainKey", String.class);
                graphRepository.deleteDomain(domainKey);
            }
            case "deleteType" -> {
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                graphRepository.deleteType(domainKey, typeKey);
            }
            case "deleteProperty" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                graphRepository.deleteProperty(objectPath);
            }
            case "deleteRelationship" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                graphRepository.deleteRelationship(objectPath);
            }
            case "deleteFunction" -> {
                String domainKey = message.getPayload("domainKey", String.class);
                String typeKey = message.getPayload("typeKey", String.class);
                String functionKey = message.getPayload("functionKey", String.class);
                graphRepository.deleteFunction(domainKey, typeKey, functionKey);
            }
            case "deleteRule" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                graphRepository.deleteRule(objectPath);
            }
            default -> log.warn("[{}] Unknown write operation: {}", getName(), operation);
        }

        publish(message.reply(AgentMessageType.GRAPH_RESULT)
                .putPayload("operation", operation)
                .putPayload("success", true));
    }
}
