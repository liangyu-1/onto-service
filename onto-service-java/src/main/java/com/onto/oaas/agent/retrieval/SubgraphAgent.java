package com.onto.oaas.agent.retrieval;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.dto.SubgraphEdgeDto;
import com.onto.oaas.dto.SubgraphNodeDto;
import com.onto.oaas.model.GraphEdge;
import com.onto.oaas.model.SubgraphEdge;
import com.onto.oaas.model.SubgraphNode;
import com.onto.oaas.model.SubgraphResult;
import com.onto.oaas.model.enums.Direction;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.util.ObjectPathUtil;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Hop 子图扩展 Agent。
 *
 * <p>职责：基于真实图数据库查询，执行 BFS 子图扩展，返回指定 hop 内的 nodes 和 edges。</p>
 * <p>输入：{@link AgentMessageType#SUBGRAPH_EXPAND}，payload 包含 "startObjectPath" (String)、"hops" (int)、"direction" (Direction)、"relationTypes" (List&lt;String&gt;)、"objectTypes" (List&lt;TBoxObjectType&gt;)、"maxNodes" (int)、"maxEdges" (int)</p>
 * <p>输出：{@link AgentMessageType#SUBGRAPH_RESULT}，payload 包含 "subgraphResult" ({@link SubgraphResult})</p>
 */
@Slf4j
@Component
public class SubgraphAgent extends AbstractAgent {

    private final TBoxGraphRepository graphRepository;

    public SubgraphAgent(AgentBus agentBus, TBoxGraphRepository graphRepository) {
        super(agentBus);
        this.graphRepository = graphRepository;
        subscribeTo(AgentMessageType.SUBGRAPH_EXPAND);
    }

    @Override
    public String getName() {
        return "SubgraphAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        String startObjectPath = message.getPayload("startObjectPath", String.class);
        Integer hops = message.getPayload("hops", Integer.class);
        Direction direction = message.getPayload("direction", Direction.class);
        List<String> relationTypes = message.getPayload("relationTypes", List.class);
        List<TBoxObjectType> objectTypes = message.getPayload("objectTypes", List.class);
        Integer maxNodes = message.getPayload("maxNodes", Integer.class);
        Integer maxEdges = message.getPayload("maxEdges", Integer.class);

        if (startObjectPath == null || startObjectPath.isBlank()) {
            log.warn("[{}] Empty startObjectPath, correlationId={}", getName(), message.getCorrelationId());
            publishEmptyResult(message, startObjectPath, hops != null ? hops : 0);
            return;
        }

        if (!graphRepository.exists(startObjectPath)) {
            log.warn("[{}] Start object not found: {}, correlationId={}",
                    getName(), startObjectPath, message.getCorrelationId());
            publishEmptyResult(message, startObjectPath, hops != null ? hops : 0);
            return;
        }

        int actualHops = hops != null ? hops : 2;
        int actualMaxNodes = maxNodes != null ? maxNodes : 100;
        int actualMaxEdges = maxEdges != null ? maxEdges : 200;
        Direction actualDirection = direction != null ? direction : Direction.BOTH;

        log.info("[{}] Expanding subgraph: start={}, hops={}, direction={}, maxNodes={}, maxEdges={}, correlationId={}",
                getName(), startObjectPath, actualHops, actualDirection, actualMaxNodes, actualMaxEdges, message.getCorrelationId());

        SubgraphResult result = expandSubgraph(startObjectPath, actualHops, actualDirection,
                relationTypes, objectTypes, actualMaxNodes, actualMaxEdges);

        publish(message.reply(AgentMessageType.SUBGRAPH_RESULT)
                .putPayload("subgraphResult", result));
    }

    /**
     * 核心子图扩展逻辑：基于真实图数据库的 BFS。
     */
    public SubgraphResult expandSubgraph(String startObjectPath, int hops, Direction direction,
                                          List<String> relationTypes, List<TBoxObjectType> objectTypes,
                                          int maxNodes, int maxEdges) {
        Set<String> visited = new HashSet<>();
        List<SubgraphNode> nodes = new ArrayList<>();
        List<SubgraphEdge> edges = new ArrayList<>();
        Map<String, Integer> hopMap = new HashMap<>();

        // Seed
        visited.add(startObjectPath);
        hopMap.put(startObjectPath, 0);
        nodes.add(buildSubgraphNode(startObjectPath, 0));

        LinkedList<String> queue = new LinkedList<>();
        queue.add(startObjectPath);

        while (!queue.isEmpty()) {
            String current = queue.poll();
            int currentHop = hopMap.getOrDefault(current, 0);
            if (currentHop >= hops) {
                continue;
            }

            List<GraphEdge> neighbors = graphRepository.findNeighbors(current, direction, relationTypes);
            for (GraphEdge edge : neighbors) {
                String neighborPath = current.equals(edge.getSourcePath())
                        ? edge.getTargetPath()
                        : edge.getSourcePath();

                if (!visited.contains(neighborPath)) {
                    if (nodes.size() >= maxNodes) {
                        return buildResult(startObjectPath, hops, nodes, edges, true);
                    }
                    visited.add(neighborPath);
                    hopMap.put(neighborPath, currentHop + 1);
                    if (objectTypes == null || objectTypes.isEmpty()
                            || matchesObjectType(neighborPath, objectTypes)) {
                        nodes.add(buildSubgraphNode(neighborPath, currentHop + 1));
                    }
                    queue.add(neighborPath);
                }

                if (edges.size() >= maxEdges) {
                    return buildResult(startObjectPath, hops, nodes, edges, true);
                }
                edges.add(SubgraphEdge.builder()
                        .source(edge.getSourcePath())
                        .relationType(edge.getRelationType())
                        .target(edge.getTargetPath())
                        .build());
            }
        }

        return buildResult(startObjectPath, hops, nodes, edges, false);
    }

    private void publishEmptyResult(AgentMessage original, String startPath, int hops) {
        SubgraphResult empty = SubgraphResult.builder()
                .startObjectPath(startPath)
                .hops(hops)
                .nodes(Collections.emptyList())
                .edges(Collections.emptyList())
                .truncated(false)
                .build();
        publish(original.reply(AgentMessageType.SUBGRAPH_RESULT)
                .putPayload("subgraphResult", empty));
    }

    private SubgraphNode buildSubgraphNode(String objectPath, int hopDistance) {
        TBoxObjectType type = ObjectPathUtil.getObjectTypeFromPath(objectPath);
        String name = resolveNodeName(objectPath, type);
        return SubgraphNode.builder()
                .objectPath(objectPath)
                .objectType(type)
                .name(name != null ? name : objectPath)
                .hopDistance(hopDistance)
                .build();
    }

    private String resolveNodeName(String objectPath, TBoxObjectType type) {
        try {
            Optional<Object> nodeOpt = graphRepository.findByObjectPath(objectPath);
            if (nodeOpt.isPresent()) {
                Object node = nodeOpt.get();
                return switch (type) {
                    case DOMAIN -> ((com.onto.oaas.model.DomainDef) node).getName();
                    case TYPE -> ((com.onto.oaas.model.TypeDef) node).getName();
                    case PROPERTY -> ((com.onto.oaas.model.PropertyDef) node).getName();
                    default -> objectPath;
                };
            }
        } catch (Exception e) {
            log.debug("[{}] Failed to resolve name for {}: {}", getName(), objectPath, e.getMessage());
        }
        return objectPath;
    }

    private boolean matchesObjectType(String objectPath, List<TBoxObjectType> objectTypes) {
        TBoxObjectType type = ObjectPathUtil.getObjectTypeFromPath(objectPath);
        return objectTypes.contains(type);
    }

    private SubgraphResult buildResult(String startObjectPath, int hops,
                                        List<SubgraphNode> nodes, List<SubgraphEdge> edges, boolean truncated) {
        return SubgraphResult.builder()
                .startObjectPath(startObjectPath)
                .hops(hops)
                .nodes(nodes)
                .edges(edges)
                .truncated(truncated)
                .build();
    }
}
