package com.onto.oaas.agent.storage;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.service.embedding.EmbeddingIndexService;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 索引管理 Agent。
 *
 * <p>职责：代理所有索引操作（搜索、保存、删除、重建），为其他 Agent 提供统一的索引访问接口。</p>
 * <p>输入：{@link AgentMessageType#INDEX_SEARCH} / {@link AgentMessageType#INDEX_UPDATE} / {@link AgentMessageType#INDEX_REBUILD}</p>
 * <p>输出：{@link AgentMessageType#INDEX_RESULT}</p>
 */
@Slf4j
@Component
public class IndexAgent extends AbstractAgent {

    private final TBoxIndexRepository indexRepository;
    private final EmbeddingIndexService embeddingIndexService;

    public IndexAgent(AgentBus agentBus, TBoxIndexRepository indexRepository,
                      EmbeddingIndexService embeddingIndexService) {
        super(agentBus);
        this.indexRepository = indexRepository;
        this.embeddingIndexService = embeddingIndexService;
        subscribeTo(AgentMessageType.INDEX_SEARCH, AgentMessageType.INDEX_UPDATE, AgentMessageType.INDEX_REBUILD);
    }

    @Override
    public String getName() {
        return "IndexAgent";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void onMessage(AgentMessage message) {
        switch (message.getType()) {
            case INDEX_SEARCH -> handleSearch(message);
            case INDEX_UPDATE -> handleUpdate(message);
            case INDEX_REBUILD -> handleRebuild(message);
            default -> log.warn("[{}] Unexpected message type: {}", getName(), message.getType());
        }
    }

    @SuppressWarnings("unchecked")
    private void handleSearch(AgentMessage message) {
        String operation = message.getPayload("operation", String.class);
        Object result = null;

        switch (operation) {
            case "searchByKeyword" -> {
                String query = message.getPayload("query", String.class);
                List<TBoxObjectType> objectTypes = message.getPayload("objectTypes", List.class);
                Integer limit = message.getPayload("limit", Integer.class);
                result = indexRepository.searchByKeyword(query, objectTypes, limit != null ? limit : 100);
            }
            case "exactMatchByPath" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                result = indexRepository.exactMatchByPath(objectPath);
            }
            case "findByObjectPath" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                result = indexRepository.findByObjectPath(objectPath).orElse(null);
            }
            case "searchByDomain" -> {
                String domainKey = message.getPayload("domainKey", String.class);
                result = indexRepository.searchByDomain(domainKey);
            }
            default -> log.warn("[{}] Unknown search operation: {}", getName(), operation);
        }

        publish(message.reply(AgentMessageType.INDEX_RESULT)
                .putPayload("operation", operation)
                .putPayload("result", result));
    }

    private void handleUpdate(AgentMessage message) {
        String operation = message.getPayload("operation", String.class);

        switch (operation) {
            case "save" -> {
                TBoxIndexDocument doc = message.getPayload("document", TBoxIndexDocument.class);
                embeddingIndexService.enrichEmbedding(doc);
                indexRepository.save(doc);
            }
            case "saveBatch" -> {
                @SuppressWarnings("unchecked")
                List<TBoxIndexDocument> docs = message.getPayload("documents", List.class);
                embeddingIndexService.enrichEmbeddings(docs);
                indexRepository.saveBatch(docs);
            }
            case "deleteByObjectPath" -> {
                String objectPath = message.getPayload("objectPath", String.class);
                indexRepository.deleteByObjectPath(objectPath);
            }
            default -> log.warn("[{}] Unknown update operation: {}", getName(), operation);
        }

        publish(message.reply(AgentMessageType.INDEX_RESULT)
                .putPayload("operation", operation)
                .putPayload("success", true));
    }

    private void handleRebuild(AgentMessage message) {
        log.info("[{}] Rebuilding index, correlationId={}", getName(), message.getCorrelationId());
        indexRepository.rebuildIndex();
        publish(message.reply(AgentMessageType.INDEX_RESULT)
                .putPayload("operation", "rebuild")
                .putPayload("success", true));
    }
}
