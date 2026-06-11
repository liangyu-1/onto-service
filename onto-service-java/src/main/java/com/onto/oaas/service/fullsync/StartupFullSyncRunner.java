package com.onto.oaas.service.fullsync;

import com.onto.oaas.model.FullSyncCheckpoint;
import com.onto.oaas.model.enums.EventProcessStatus;
import com.onto.oaas.repository.mybatis.EventProcessRecordMapper;
import com.onto.oaas.repository.neo4j.Neo4jTBoxIndexRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.Ordered;
import org.springframework.kafka.config.KafkaListenerEndpointRegistry;
import org.springframework.stereotype.Component;

/**
 * 启动时自动全量同步 Runner。
 *
 * <p>职责：在 Spring Boot 启动后检查 active buffer 是否为空，如果为空则触发全量同步。
 * 全量同步完成后清空幂等记录表，并启动 Kafka 消费者。</p>
 *
 * <p>注意：本 Runner 不强制依赖 {@link EventProcessRecordMapper}（Doris 不可用时 MyBatis
 * mapper 可能无法创建），此时跳过清空幂等表，不影响全量同步本身。</p>
 */
@Slf4j
@Component
public class StartupFullSyncRunner implements ApplicationRunner, Ordered {

    private static final int BUFFER_CHECK_MAX_RETRIES = 5;
    private static final long BUFFER_CHECK_RETRY_DELAY_MS = 2000;

    private final FullSyncService fullSyncService;
    private final Neo4jTBoxIndexRepository indexRepository;
    private final KafkaListenerEndpointRegistry kafkaListenerEndpointRegistry;
    private EventProcessRecordMapper eventProcessRecordMapper;

    @Value("${oaas.full-sync.auto-on-startup:false}")
    private boolean autoOnStartup;

    public StartupFullSyncRunner(FullSyncService fullSyncService,
                                  Neo4jTBoxIndexRepository indexRepository,
                                  KafkaListenerEndpointRegistry kafkaListenerEndpointRegistry) {
        this.fullSyncService = fullSyncService;
        this.indexRepository = indexRepository;
        this.kafkaListenerEndpointRegistry = kafkaListenerEndpointRegistry;
    }

    @Override
    public int getOrder() {
        // 确保在 Neo4jTBoxIndexRepository 的 @PostConstruct 初始化之后执行
        return Ordered.LOWEST_PRECEDENCE - 100;
    }

    @Autowired(required = false)
    public void setEventProcessRecordMapper(EventProcessRecordMapper eventProcessRecordMapper) {
        this.eventProcessRecordMapper = eventProcessRecordMapper;
    }

    @Override
    public void run(ApplicationArguments args) {
        log.info("[StartupSync] Runner started. autoOnStartup={}", autoOnStartup);

        if (!autoOnStartup) {
            log.info("[StartupSync] Auto full sync on startup is disabled");
            startKafkaConsumers();
            return;
        }

        // 等待 Neo4j schema 初始化完成
        waitForSchemaInitialization();

        // 检查 active buffer（带重试）
        Long activeCount = checkActiveBufferWithRetry();
        if (activeCount == null) {
            log.error("[StartupSync] Failed to check active buffer after retries, skipping auto full sync");
            startKafkaConsumers();
            return;
        }

        if (activeCount > 0) {
            log.info("[StartupSync] Active buffer already has {} nodes, skipping auto full sync", activeCount);
            startKafkaConsumers();
            return;
        }

        log.info("[StartupSync] Active buffer is empty, triggering auto full sync...");
        try {
            FullSyncCheckpoint checkpoint = fullSyncService.executeFullSync("default", "latest");
            if (checkpoint.getStatus() == EventProcessStatus.SUCCESS) {
                log.info("[StartupSync] Auto full sync completed successfully: domains={}, types={}, properties={}",
                        checkpoint.getDomainCount(), checkpoint.getTypeCount(), checkpoint.getPropertyCount());
                clearIdempotencyRecords();
            } else {
                log.error("[StartupSync] Auto full sync failed: {}", checkpoint.getErrorMessage());
            }
        } catch (Exception e) {
            log.error("[StartupSync] Auto full sync failed", e);
        } finally {
            startKafkaConsumers();
        }
    }

    private void waitForSchemaInitialization() {
        for (int i = 0; i < 30; i++) {
            if (indexRepository.isSchemaInitialized()) {
                log.info("[StartupSync] Neo4j schema is initialized");
                return;
            }
            log.warn("[StartupSync] Waiting for Neo4j schema initialization... {}/30", i + 1);
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
        log.warn("[StartupSync] Neo4j schema initialization not confirmed, proceeding anyway");
    }

    private Long checkActiveBufferWithRetry() {
        for (int attempt = 1; attempt <= BUFFER_CHECK_MAX_RETRIES; attempt++) {
            try {
                long count = indexRepository.countByBuffer(indexRepository.activeBuffer());
                log.info("[StartupSync] Active buffer count: {} (attempt {})", count, attempt);
                return count;
            } catch (Exception e) {
                log.warn("[StartupSync] Failed to check active buffer (attempt {}/{}): {}",
                        attempt, BUFFER_CHECK_MAX_RETRIES, e.getMessage());
                if (attempt < BUFFER_CHECK_MAX_RETRIES) {
                    try {
                        Thread.sleep(BUFFER_CHECK_RETRY_DELAY_MS);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        return null;
                    }
                }
            }
        }
        return null;
    }

    private void clearIdempotencyRecords() {
        if (eventProcessRecordMapper == null) {
            log.warn("[StartupSync] EventProcessRecordMapper not available, skipping idempotency cleanup");
            return;
        }
        try {
            eventProcessRecordMapper.truncateAll();
            log.info("[StartupSync] Cleared event_process_record table");
        } catch (Exception e) {
            log.warn("[StartupSync] Failed to clear event_process_record table: {}", e.getMessage());
        }
    }

    private void startKafkaConsumers() {
        try {
            kafkaListenerEndpointRegistry.start();
            log.info("[StartupSync] Kafka consumers started");
        } catch (Exception e) {
            log.error("[StartupSync] Failed to start Kafka consumers: {}", e.getMessage());
        }
    }
}
