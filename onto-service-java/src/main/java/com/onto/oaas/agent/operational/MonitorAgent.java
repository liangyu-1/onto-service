package com.onto.oaas.agent.operational;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 监控指标 Agent。
 *
 * <p>职责：统一收集和记录系统指标（计数器、计时器、 gauges），统一日志格式。</p>
 * <p>输入：{@link AgentMessageType#METRICS_RECORD} / {@link AgentMessageType#LOG_RECORD}</p>
 * <p>输出：无（写入 Micrometer + SLF4J）</p>
 */
@Slf4j
@Component
public class MonitorAgent extends AbstractAgent {

    private final MeterRegistry meterRegistry;
    private final Map<String, Counter> counterCache = new ConcurrentHashMap<>();
    private final Map<String, Timer> timerCache = new ConcurrentHashMap<>();

    public MonitorAgent(AgentBus agentBus, MeterRegistry meterRegistry) {
        super(agentBus);
        this.meterRegistry = meterRegistry;
        subscribeTo(AgentMessageType.METRICS_RECORD, AgentMessageType.LOG_RECORD);
    }

    @Override
    public String getName() {
        return "MonitorAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        switch (message.getType()) {
            case METRICS_RECORD -> handleMetrics(message);
            case LOG_RECORD -> handleLog(message);
            default -> log.warn("[{}] Unexpected message type: {}", getName(), message.getType());
        }
    }

    private void handleMetrics(AgentMessage message) {
        String metricType = message.getPayload("metricType", String.class);
        String metricName = message.getPayload("metricName", String.class);
        Double value = message.getPayload("value", Double.class);
        String[] tags = message.getPayload("tags", String[].class);

        if (metricName == null) {
            return;
        }

        switch (metricType != null ? metricType : "counter") {
            case "counter" -> {
                Counter counter = counterCache.computeIfAbsent(metricName,
                        k -> Counter.builder(k).tags(tags != null ? tags : new String[0]).register(meterRegistry));
                counter.increment(value != null ? value : 1.0);
            }
            case "timer" -> {
                Timer timer = timerCache.computeIfAbsent(metricName,
                        k -> Timer.builder(k).tags(tags != null ? tags : new String[0]).register(meterRegistry));
                if (value != null) {
                    timer.record(Duration.ofMillis(value.longValue()));
                }
            }
            case "gauge" -> {
                if (value != null) {
                    meterRegistry.gauge(metricName, value);
                }
            }
            default -> log.warn("[{}] Unknown metric type: {}", getName(), metricType);
        }
    }

    private void handleLog(AgentMessage message) {
        String level = message.getPayload("level", String.class);
        String traceId = message.getCorrelationId();
        String queryId = message.getPayload("queryId", String.class);
        String eventId = message.getPayload("eventId", String.class);
        String objectPath = message.getPayload("objectPath", String.class);
        String objectType = message.getPayload("objectType", String.class);
        Long costMs = message.getPayload("costMs", Long.class);
        String status = message.getPayload("status", String.class);
        String errorCode = message.getPayload("errorCode", String.class);
        String errorMessage = message.getPayload("errorMessage", String.class);

        String logLine = String.format(
                "trace_id=%s query_id=%s event_id=%s object_path=%s object_type=%s cost_ms=%s status=%s error_code=%s error_message=%s",
                traceId != null ? traceId : "-",
                queryId != null ? queryId : "-",
                eventId != null ? eventId : "-",
                objectPath != null ? objectPath : "-",
                objectType != null ? objectType : "-",
                costMs != null ? costMs : "-",
                status != null ? status : "-",
                errorCode != null ? errorCode : "-",
                errorMessage != null ? errorMessage : "-"
        );

        switch (level != null ? level : "info") {
            case "error" -> log.error("[MONITOR] {}", logLine);
            case "warn" -> log.warn("[MONITOR] {}", logLine);
            case "debug" -> log.debug("[MONITOR] {}", logLine);
            default -> log.info("[MONITOR] {}", logLine);
        }
    }
}
