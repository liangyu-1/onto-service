package com.onto.oaas.service.fullsync;

import com.onto.oaas.model.FullSyncCheckpoint;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.enums.EventProcessStatus;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.service.TBoxIndexBuilder;
import com.onto.oaas.service.embedding.EmbeddingIndexService;
import com.onto.oaas.util.TraceIdGenerator;
import java.time.Instant;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class FullSyncService {

    private final FullSyncClient fullSyncClient;
    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;
    private final EmbeddingIndexService embeddingIndexService;

    private static final String ACTIVE_BUFFER = "active";
    private static final String STAGING_BUFFER = "staging";

    /**
     * 执行双缓冲全量同步。
     *
     * <p>流程：</p>
     * <ol>
     *   <li>清空 staging buffer（幂等）</li>
     *   <li>拉取 snapshot → 写入 staging</li>
     *   <li>构建索引 + embedding → 写入 staging</li>
     *   <li>切换：删除旧 active，staging → active</li>
     * </ol>
     *
     * <p>同步期间 active buffer 的数据始终可用，查询不中断。</p>
     */
    public FullSyncCheckpoint executeFullSync(String ontologyId, String ontologyVersion) {
        Instant startedTime = Instant.now();
        FullSyncCheckpoint checkpoint = FullSyncCheckpoint.builder()
                .checkpointId(TraceIdGenerator.generateTraceId())
                .timestamp(startedTime.toString())
                .status(EventProcessStatus.PENDING)
                .startedTime(startedTime)
                .build();

        try {
            log.info("[DoubleBuffer] Starting full sync for ontologyId={}, version={}", ontologyId, ontologyVersion);

            // 1. 清空 staging（幂等，防止上次残留）
            log.info("[DoubleBuffer] Clearing staging buffer...");
            graphRepository.clearBuffer(STAGING_BUFFER);
            indexRepository.clearBuffer(STAGING_BUFFER);

            // 2. 拉取 snapshot
            TBoxSnapshot snapshot = fullSyncClient.fetchSnapshot(ontologyId, ontologyVersion);
            if (snapshot == null || snapshot.getDomains() == null) {
                throw new IllegalStateException("Fetched snapshot is null or has no domains");
            }
            log.info("[DoubleBuffer] Fetched snapshot with {} domains", snapshot.getDomains().size());

            // 3. 写入 staging graph
            graphRepository.saveSnapshot(snapshot, STAGING_BUFFER);
            log.info("[DoubleBuffer] Saved snapshot to staging graph");

            // 4. 构建索引文档
            List<TBoxIndexDocument> docs = indexBuilder.buildFromSnapshot(snapshot);
            log.info("[DoubleBuffer] Built {} index documents", docs.size());

            // 5. 计算 embedding → 写入 staging index
            docs = embeddingIndexService.enrichEmbeddings(docs);
            indexRepository.saveBatch(docs, STAGING_BUFFER);
            log.info("[DoubleBuffer] Saved {} index documents to staging", docs.size());

            // 6. 原子切换：staging → active
            log.info("[DoubleBuffer] Promoting staging -> active...");
            graphRepository.promoteBuffer(STAGING_BUFFER, ACTIVE_BUFFER);
            indexRepository.promoteBuffer(STAGING_BUFFER, ACTIVE_BUFFER);
            log.info("[DoubleBuffer] Buffer promotion completed");

            // 7. 统计
            int domainCount = snapshot.getDomains().size();
            int typeCount = 0;
            int propertyCount = 0;
            int relationshipCount = 0;
            int functionCount = 0;
            int ruleCount = 0;

            for (var domain : snapshot.getDomains().values()) {
                if (domain.getTypes() != null) {
                    typeCount += domain.getTypes().size();
                    for (var type : domain.getTypes().values()) {
                        if (type.getProperties() != null) {
                            propertyCount += type.getProperties().size();
                        }
                        if (type.getRelationships() != null) {
                            relationshipCount += type.getRelationships().size();
                        }
                        if (type.getFunctions() != null) {
                            functionCount += type.getFunctions().size();
                            for (var function : type.getFunctions().values()) {
                                if (function.getRules() != null) {
                                    ruleCount += function.getRules().size();
                                }
                            }
                        }
                    }
                }
            }

            checkpoint.setDomainCount(domainCount);
            checkpoint.setTypeCount(typeCount);
            checkpoint.setPropertyCount(propertyCount);
            checkpoint.setRelationshipCount(relationshipCount);
            checkpoint.setFunctionCount(functionCount);
            checkpoint.setRuleCount(ruleCount);
            checkpoint.setStatus(EventProcessStatus.SUCCESS);
            checkpoint.setCompletedTime(Instant.now());

            log.info("[DoubleBuffer] Full sync completed successfully: {}", checkpoint.getCheckpointId());
        } catch (Exception e) {
            log.error("[DoubleBuffer] Full sync failed, cleaning up staging buffer", e);
            // 失败时清理 staging，不影响 active
            try {
                graphRepository.clearBuffer(STAGING_BUFFER);
                indexRepository.clearBuffer(STAGING_BUFFER);
            } catch (Exception cleanupEx) {
                log.warn("[DoubleBuffer] Failed to cleanup staging buffer: {}", cleanupEx.getMessage());
            }
            checkpoint.setStatus(EventProcessStatus.FAILED);
            checkpoint.setCompletedTime(Instant.now());
            checkpoint.setErrorMessage(e.getMessage());
        }

        return checkpoint;
    }
}
