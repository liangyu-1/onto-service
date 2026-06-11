package com.onto.oaas.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "oaas")
public class OaaSProperties {

    private KafkaProperties kafka;
    private FullSyncProperties fullSync;
    private IndexProperties index;
    private RetrievalProperties retrieval;
    private IdempotencyProperties idempotency;

    @Data
    public static class KafkaProperties {
        private String topic;
        private ConsumerProperties consumer;
        private String dlqTopic;
    }

    @Data
    public static class ConsumerProperties {
        private String groupId;
    }

    @Data
    public static class FullSyncProperties {
        private String baseUrl;
    }

    @Data
    public static class IndexProperties {
        private RebuildProperties rebuild;
    }

    @Data
    public static class RebuildProperties {
        private int batchSize;
        private int threadPoolSize;
    }

    @Data
    public static class RetrievalProperties {
        private int maxTopK;
        private int defaultTopK;
    }

    @Data
    public static class IdempotencyProperties {
        private int maxRetries;
    }
}
