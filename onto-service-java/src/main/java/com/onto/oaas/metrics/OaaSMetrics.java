package com.onto.oaas.metrics;

import io.micrometer.core.instrument.*;
import org.springframework.stereotype.Component;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class OaaSMetrics {
    private final Counter fullSyncStarted;
    private final Counter fullSyncCompleted;
    private final Counter fullSyncFailed;
    private final Counter kafkaEventsConsumed;
    private final Counter kafkaEventsProcessed;
    private final Counter kafkaEventsFailed;
    private final Counter tboxIndexFailed;
    private final Counter dlqMessages;
    private final Counter retrieveEmpty;
    private final Timer fullSyncDuration;
    private final Timer graphWriteLatency;
    private final Timer tboxIndexLatency;
    private final Timer tboxRetrieveLatency;
    private final AtomicLong kafkaConsumerLag = new AtomicLong(0);

    public OaaSMetrics(MeterRegistry registry) {
        this.fullSyncStarted = Counter.builder("full_sync_started_total").description("Full sync started count").register(registry);
        this.fullSyncCompleted = Counter.builder("full_sync_completed_total").description("Full sync completed count").register(registry);
        this.fullSyncFailed = Counter.builder("full_sync_failed_total").description("Full sync failed count").register(registry);
        this.kafkaEventsConsumed = Counter.builder("kafka_events_consumed_total").description("Kafka events consumed").register(registry);
        this.kafkaEventsProcessed = Counter.builder("kafka_events_processed_total").description("Kafka events processed").register(registry);
        this.kafkaEventsFailed = Counter.builder("kafka_events_failed_total").description("Kafka events failed").register(registry);
        this.tboxIndexFailed = Counter.builder("tbox_index_failed_total").description("TBox index failed count").register(registry);
        this.dlqMessages = Counter.builder("dlq_messages_total").description("DLQ message count").register(registry);
        this.retrieveEmpty = Counter.builder("retrieve_empty_total").description("Empty retrieve result count").register(registry);
        this.fullSyncDuration = Timer.builder("full_sync_duration_seconds").description("Full sync duration").register(registry);
        this.graphWriteLatency = Timer.builder("graph_write_latency_seconds").description("Graph write latency").register(registry);
        this.tboxIndexLatency = Timer.builder("tbox_index_latency_seconds").description("TBox index latency").register(registry);
        this.tboxRetrieveLatency = Timer.builder("tbox_retrieve_latency_seconds").description("TBox retrieve latency").register(registry);
        Gauge.builder("kafka_consumer_lag", kafkaConsumerLag, AtomicLong::get).description("Kafka consumer lag").register(registry);
    }

    public void recordFullSyncStarted() { fullSyncStarted.increment(); }
    public void recordFullSyncCompleted(long durationMs) { fullSyncCompleted.increment(); fullSyncDuration.record(durationMs, TimeUnit.MILLISECONDS); }
    public void recordFullSyncFailed() { fullSyncFailed.increment(); }
    public void recordEventConsumed() { kafkaEventsConsumed.increment(); }
    public void recordEventProcessed() { kafkaEventsProcessed.increment(); }
    public void recordEventFailed() { kafkaEventsFailed.increment(); }
    public void recordGraphWrite(Runnable action) { graphWriteLatency.record(action); }
    public void recordIndexWrite(Runnable action) { tboxIndexLatency.record(action); }
    public void recordRetrieve(Runnable action) { tboxRetrieveLatency.record(action); }
    public void recordEmptyResult() { retrieveEmpty.increment(); }
    public void recordDlqMessage() { dlqMessages.increment(); }
    public void updateConsumerLag(long lag) { kafkaConsumerLag.set(lag); }
}
