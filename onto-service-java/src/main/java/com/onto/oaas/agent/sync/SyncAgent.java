package com.onto.oaas.agent.sync;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.FullSyncCheckpoint;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.EventProcessStatus;
import com.onto.oaas.model.enums.EventType;
import com.onto.oaas.model.event.TBoxPayload;
import com.onto.oaas.service.TBoxIndexBuilder;
import com.onto.oaas.service.fullsync.FullSyncClient;
import com.onto.oaas.util.TraceIdGenerator;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 同步协调 Agent。
 *
 * <p>职责：协调全量同步和增量同步，分离图写入和索引写入，支持部分失败重试。</p>
 * <p>输入：{@link AgentMessageType#SYNC_FULL_REQUEST} / {@link AgentMessageType#SYNC_INCREMENTAL_EVENT}</p>
 * <p>输出：{@link AgentMessageType#SYNC_CHECKPOINT} / {@link AgentMessageType#GRAPH_WRITE} / {@link AgentMessageType#INDEX_UPDATE}</p>
 */
@Slf4j
@Component
public class SyncAgent extends AbstractAgent {

    private final FullSyncClient fullSyncClient;
    private final TBoxIndexBuilder indexBuilder;

    public SyncAgent(AgentBus agentBus, FullSyncClient fullSyncClient, TBoxIndexBuilder indexBuilder) {
        super(agentBus);
        this.fullSyncClient = fullSyncClient;
        this.indexBuilder = indexBuilder;
        subscribeTo(AgentMessageType.SYNC_FULL_REQUEST, AgentMessageType.SYNC_INCREMENTAL_EVENT);
    }

    @Override
    public String getName() {
        return "SyncAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        switch (message.getType()) {
            case SYNC_FULL_REQUEST -> handleFullSync(message);
            case SYNC_INCREMENTAL_EVENT -> handleIncrementalEvent(message);
            default -> log.warn("[{}] Unexpected message type: {}", getName(), message.getType());
        }
    }

    private void handleFullSync(AgentMessage message) {
        String ontologyId = message.getPayload("ontologyId", String.class);
        String ontologyVersion = message.getPayload("ontologyVersion", String.class);
        String correlationId = message.getCorrelationId();

        Instant startedTime = Instant.now();
        FullSyncCheckpoint checkpoint = FullSyncCheckpoint.builder()
                .checkpointId(TraceIdGenerator.generateTraceId())
                .timestamp(startedTime.toString())
                .status(EventProcessStatus.PENDING)
                .startedTime(startedTime)
                .build();

        try {
            log.info("[{}] Starting full sync: ontologyId={}, version={}, correlationId={}",
                    getName(), ontologyId, ontologyVersion, correlationId);

            // 1. Fetch snapshot
            TBoxSnapshot snapshot = fullSyncClient.fetchSnapshot(ontologyId, ontologyVersion);
            if (snapshot == null || snapshot.getDomains() == null) {
                throw new IllegalStateException("Fetched snapshot is null or has no domains");
            }

            // 2. Clear graph (via GraphAgent)
            AgentMessage clearMsg = AgentMessage.builder()
                    .correlationId(correlationId)
                    .type(AgentMessageType.GRAPH_WRITE)
                    .build();
            clearMsg.putPayload("operation", "clearAll");
            publish(clearMsg);

            // 3. Save snapshot to graph (via GraphAgent)
            AgentMessage saveMsg = AgentMessage.builder()
                    .correlationId(correlationId)
                    .type(AgentMessageType.GRAPH_WRITE)
                    .build();
            saveMsg.putPayload("operation", "saveSnapshot");
            saveMsg.putPayload("snapshot", snapshot);
            publish(saveMsg);

            // 4. Build index documents
            List<TBoxIndexDocument> docs = indexBuilder.buildFromSnapshot(snapshot);
            log.info("[{}] Built {} index documents, correlationId={}", getName(), docs.size(), correlationId);

            // 5. Save to index (via IndexAgent)
            AgentMessage indexMsg = AgentMessage.builder()
                    .correlationId(correlationId)
                    .type(AgentMessageType.INDEX_UPDATE)
                    .build();
            indexMsg.putPayload("operation", "saveBatch");
            indexMsg.putPayload("documents", docs);
            publish(indexMsg);

            // 6. Update checkpoint counts
            int[] counts = countSnapshotObjects(snapshot);
            checkpoint.setDomainCount(counts[0]);
            checkpoint.setTypeCount(counts[1]);
            checkpoint.setPropertyCount(counts[2]);
            checkpoint.setRelationshipCount(counts[3]);
            checkpoint.setFunctionCount(counts[4]);
            checkpoint.setRuleCount(counts[5]);
            checkpoint.setStatus(EventProcessStatus.SUCCESS);
            checkpoint.setCompletedTime(Instant.now());

            log.info("[{}] Full sync completed: checkpointId={}, correlationId={}",
                    getName(), checkpoint.getCheckpointId(), correlationId);

        } catch (Exception e) {
            log.error("[{}] Full sync failed: correlationId={}", getName(), correlationId, e);
            checkpoint.setStatus(EventProcessStatus.FAILED);
            checkpoint.setCompletedTime(Instant.now());
            checkpoint.setErrorMessage(e.getMessage());
        }

        publish(message.reply(AgentMessageType.SYNC_CHECKPOINT)
                .putPayload("checkpoint", checkpoint));
    }

    private void handleIncrementalEvent(AgentMessage message) {
        String eventId = message.getCorrelationId();
        String eventTypeStr = message.getPayload("eventType", String.class);
        TBoxPayload payload = message.getPayload("payload", TBoxPayload.class);

        log.info("[{}] Handling incremental event: eventId={}, type={}", getName(), eventId, eventTypeStr);

        boolean graphSuccess = false;
        boolean indexSuccess = false;
        String error = null;

        try {
            EventType eventType = EventType.valueOf(eventTypeStr);

            if (eventType == EventType.DELETE) {
                handleDeleteEvent(message, payload);
                graphSuccess = true;
                indexSuccess = true;
            } else if (payload != null && payload.getDomains() != null) {
                List<TBoxIndexDocument> indexDocs = new ArrayList<>();

                for (Map.Entry<String, DomainDef> domainEntry : payload.getDomains().entrySet()) {
                    String domainKey = domainEntry.getKey();
                    DomainDef domain = domainEntry.getValue();

                    // Write domain to graph
                    publishGraphWrite("saveDomain", domain, domainKey, null, null, null, null);
                    indexDocs.add(indexBuilder.buildFromDomain(domainKey, domain));

                    if (domain.getTypes() != null) {
                        for (Map.Entry<String, TypeDef> typeEntry : domain.getTypes().entrySet()) {
                            String typeKey = typeEntry.getKey();
                            TypeDef type = typeEntry.getValue();

                            publishGraphWrite("saveType", null, domainKey, type, typeKey, null, null);
                            indexDocs.add(indexBuilder.buildFromType(domainKey, typeKey, type));

                            // Handle properties
                            if (type.getProperties() != null) {
                                for (Map.Entry<String, PropertyDef> propEntry : type.getProperties().entrySet()) {
                                    String propKey = propEntry.getKey();
                                    PropertyDef prop = propEntry.getValue();
                                    publishGraphWrite("saveProperty", null, domainKey, null, typeKey, prop, propKey);
                                    indexDocs.add(indexBuilder.buildFromProperty(domainKey, typeKey, propKey, prop));
                                }
                            }

                            // Handle relationships
                            if (type.getRelationships() != null) {
                                for (Map.Entry<String, RelationshipDef> relEntry : type.getRelationships().entrySet()) {
                                    String relKey = relEntry.getKey();
                                    RelationshipDef rel = relEntry.getValue();
                                    publishGraphWrite("saveRelationship", null, domainKey, null, typeKey, rel, relKey);
                                    indexDocs.add(indexBuilder.buildFromRelationship(domainKey, typeKey, relKey, rel));
                                }
                            }

                            // Handle functions and rules
                            if (type.getFunctions() != null) {
                                for (Map.Entry<String, FunctionDef> funcEntry : type.getFunctions().entrySet()) {
                                    String funcKey = funcEntry.getKey();
                                    FunctionDef func = funcEntry.getValue();
                                    publishGraphWrite("saveFunction", null, domainKey, null, typeKey, func, funcKey);
                                    indexDocs.add(indexBuilder.buildFromFunction(domainKey, typeKey, funcKey, func));

                                    if (func.getRules() != null) {
                                        for (Map.Entry<String, RuleDef> ruleEntry : func.getRules().entrySet()) {
                                            String ruleKey = ruleEntry.getKey();
                                            RuleDef rule = ruleEntry.getValue();
                                            publishGraphWrite("saveRule", null, domainKey, null, typeKey, func, funcKey, rule, ruleKey);
                                            indexDocs.add(indexBuilder.buildFromRule(domainKey, typeKey, funcKey, ruleKey, rule));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Update index
                if (!indexDocs.isEmpty()) {
                    AgentMessage indexMsg = AgentMessage.builder()
                            .correlationId(eventId)
                            .type(AgentMessageType.INDEX_UPDATE)
                            .build();
                    indexMsg.putPayload("operation", "saveBatch");
                    indexMsg.putPayload("documents", indexDocs);
                    publish(indexMsg);
                }

                graphSuccess = true;
                indexSuccess = true;
            }

        } catch (Exception e) {
            log.error("[{}] Incremental event processing failed: eventId={}", getName(), eventId, e);
            error = e.getMessage();
            graphSuccess = false;
        }

        publish(message.reply(AgentMessageType.SYNC_CHECKPOINT)
                .putPayload("eventId", eventId)
                .putPayload("eventType", eventTypeStr)
                .putPayload("graphSuccess", graphSuccess)
                .putPayload("indexSuccess", indexSuccess)
                .putPayload("error", error));
    }

    @SuppressWarnings("unchecked")
    private void publishGraphWrite(String operation, Object... args) {
        AgentMessage msg = AgentMessage.builder()
                .type(AgentMessageType.GRAPH_WRITE)
                .build();
        msg.putPayload("operation", operation);

        switch (operation) {
            case "saveDomain" -> {
                msg.putPayload("domain", args[0]);
                msg.putPayload("domainKey", args[1]);
            }
            case "saveType" -> {
                msg.putPayload("type", args[2]);
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
            }
            case "saveProperty" -> {
                msg.putPayload("property", args[4]);
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
                msg.putPayload("propertyKey", args[5]);
            }
            case "saveRelationship" -> {
                msg.putPayload("relationship", args[4]);
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
                msg.putPayload("relationshipKey", args[5]);
            }
            case "saveFunction" -> {
                msg.putPayload("function", args[4]);
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
                msg.putPayload("functionKey", args[5]);
            }
            case "saveRule" -> {
                msg.putPayload("rule", args[6]);
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
                msg.putPayload("functionKey", args[5]);
                msg.putPayload("ruleKey", args[7]);
            }
            case "deleteDomain" -> msg.putPayload("domainKey", args[1]);
            case "deleteType" -> {
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
            }
            case "deleteProperty", "deleteRelationship", "deleteRule" ->
                msg.putPayload("objectPath", args[6]);
            case "deleteFunction" -> {
                msg.putPayload("domainKey", args[1]);
                msg.putPayload("typeKey", args[3]);
                msg.putPayload("functionKey", args[5]);
            }
        }
        publish(msg);
    }

    private void handleDeleteEvent(AgentMessage message, TBoxPayload payload) {
        if (payload == null || payload.getDomains() == null) {
            return;
        }
        for (Map.Entry<String, DomainDef> domainEntry : payload.getDomains().entrySet()) {
            String domainKey = domainEntry.getKey();
            DomainDef domain = domainEntry.getValue();

            // Check if this is a domain-level delete (no types)
            if (domain.getTypes() == null || domain.getTypes().isEmpty()) {
                publishGraphWrite("deleteDomain", null, domainKey, null, null, null, null);
                deleteIndexByPattern(domainKey);
                continue;
            }

            for (Map.Entry<String, TypeDef> typeEntry : domain.getTypes().entrySet()) {
                String typeKey = typeEntry.getKey();
                TypeDef type = typeEntry.getValue();

                // Check if this is a type-level delete (no properties/relationships/functions)
                boolean isTypeDelete = (type.getProperties() == null || type.getProperties().isEmpty())
                        && (type.getRelationships() == null || type.getRelationships().isEmpty())
                        && (type.getFunctions() == null || type.getFunctions().isEmpty());

                if (isTypeDelete) {
                    publishGraphWrite("deleteType", null, domainKey, null, typeKey, null, null);
                    deleteIndexByPattern(domainKey + "." + typeKey);
                    continue;
                }

                // Handle property deletes
                if (type.getProperties() != null) {
                    for (String propKey : type.getProperties().keySet()) {
                        String objectPath = domainKey + "." + typeKey + ".properties." + propKey;
                        publishGraphWrite("deleteProperty", null, null, null, null, null, null, objectPath);
                        deleteIndexByPattern(objectPath);
                    }
                }

                // Handle relationship deletes
                if (type.getRelationships() != null) {
                    for (String relKey : type.getRelationships().keySet()) {
                        String objectPath = domainKey + "." + typeKey + ".relationships." + relKey;
                        publishGraphWrite("deleteRelationship", null, null, null, null, null, null, objectPath);
                        deleteIndexByPattern(objectPath);
                    }
                }

                // Handle function deletes
                if (type.getFunctions() != null) {
                    for (Map.Entry<String, FunctionDef> funcEntry : type.getFunctions().entrySet()) {
                        String funcKey = funcEntry.getKey();
                        FunctionDef func = funcEntry.getValue();

                        // Check if this is a function-level delete (no rules)
                        if (func.getRules() == null || func.getRules().isEmpty()) {
                            publishGraphWrite("deleteFunction", null, domainKey, null, typeKey, null, funcKey, null);
                            deleteIndexByPattern(domainKey + "." + typeKey + ".functions." + funcKey);
                            continue;
                        }

                        // Handle rule deletes
                        for (String ruleKey : func.getRules().keySet()) {
                            String objectPath = domainKey + "." + typeKey + ".functions." + funcKey + ".rules." + ruleKey;
                            publishGraphWrite("deleteRule", null, null, null, null, null, null, objectPath);
                            deleteIndexByPattern(objectPath);
                        }
                    }
                }
            }
        }
    }

    private void deleteIndexByPattern(String objectPath) {
        AgentMessage indexMsg = AgentMessage.builder()
                .type(AgentMessageType.INDEX_UPDATE)
                .build();
        indexMsg.putPayload("operation", "deleteByObjectPath");
        indexMsg.putPayload("objectPath", objectPath);
        publish(indexMsg);
    }

    private int[] countSnapshotObjects(TBoxSnapshot snapshot) {
        int domainCount = 0, typeCount = 0, propertyCount = 0, relationshipCount = 0, functionCount = 0, ruleCount = 0;
        if (snapshot.getDomains() != null) {
            domainCount = snapshot.getDomains().size();
            for (var domain : snapshot.getDomains().values()) {
                if (domain.getTypes() != null) {
                    typeCount += domain.getTypes().size();
                    for (var type : domain.getTypes().values()) {
                        if (type.getProperties() != null) propertyCount += type.getProperties().size();
                        if (type.getRelationships() != null) relationshipCount += type.getRelationships().size();
                        if (type.getFunctions() != null) {
                            functionCount += type.getFunctions().size();
                            for (var function : type.getFunctions().values()) {
                                if (function.getRules() != null) ruleCount += function.getRules().size();
                            }
                        }
                    }
                }
            }
        }
        return new int[]{domainCount, typeCount, propertyCount, relationshipCount, functionCount, ruleCount};
    }
}
