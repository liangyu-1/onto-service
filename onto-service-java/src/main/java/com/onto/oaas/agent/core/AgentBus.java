package com.onto.oaas.agent.core;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * Agent 消息总线。
 *
 * <p>基于 Spring ApplicationEvent 实现，支持两种通信模式：</p>
 * <ul>
 *   <li><b>发布-订阅</b>：publish() 广播消息，所有 canHandle=true 的 Agent 都会收到</li>
 *   <li><b>点对点</b>：sendTo() 指定目标 Agent，只有目标 Agent 收到</li>
 * </ul>
 *
 * <p>Agent 通过 {@link #register(Agent)} 注册到总线，通过 {@link #publish(AgentMessage)}
 * 或 {@link #sendTo(String, AgentMessage)} 发送消息。收到消息后，总线自动路由到
 * 合适的 Agent 并调用其 handle() 方法。</p>
 */
@Slf4j
@Component
public class AgentBus {

    private final ApplicationEventPublisher eventPublisher;
    private final List<Agent> agents = new CopyOnWriteArrayList<>();
    private final Map<String, Agent> agentMap = new ConcurrentHashMap<>();

    public AgentBus(ApplicationEventPublisher eventPublisher) {
        this.eventPublisher = eventPublisher;
    }

    /**
     * 注册 Agent 到总线。应在 Agent 构造完成后调用。
     */
    public void register(Agent agent) {
        if (agent == null || agent.getName() == null) {
            throw new IllegalArgumentException("Agent and agent name must not be null");
        }
        agents.add(agent);
        agentMap.put(agent.getName(), agent);
        log.info("Agent registered: {}", agent.getName());
    }

    /**
     * 广播消息。所有 canHandle=true 的 Agent 都会收到。
     */
    public void publish(AgentMessage message) {
        if (message == null) {
            return;
        }
        log.debug("Publishing message: type={}, correlationId={}, from={}",
                message.getType(), message.getCorrelationId(), message.getFromAgent());
        eventPublisher.publishEvent(new AgentBusEvent(this, message));
    }

    /**
     * 点对点发送消息到指定 Agent。
     */
    public void sendTo(String agentName, AgentMessage message) {
        Agent target = agentMap.get(agentName);
        if (target == null) {
            log.warn("Target agent not found: {}", agentName);
            return;
        }
        if (target.canHandle(message)) {
            try {
                target.handle(message);
            } catch (Exception e) {
                log.error("Agent {} failed to handle message: type={}, correlationId={}",
                        agentName, message.getType(), message.getCorrelationId(), e);
            }
        } else {
            log.warn("Agent {} cannot handle message type: {}", agentName, message.getType());
        }
    }

    /**
     * 内部事件监听器。接收 Spring ApplicationEvent 并路由到合适的 Agent。
     */
    @EventListener
    public void onAgentBusEvent(AgentBusEvent event) {
        AgentMessage message = event.getMessage();
        if (message.getToAgent() != null && !message.getToAgent().isBlank()) {
            // 点对点模式
            sendTo(message.getToAgent(), message);
            return;
        }
        // 广播模式
        for (Agent agent : agents) {
            if (agent.canHandle(message)) {
                try {
                    agent.handle(message);
                } catch (Exception e) {
                    log.error("Agent {} failed to handle message: type={}, correlationId={}",
                            agent.getName(), message.getType(), message.getCorrelationId(), e);
                }
            }
        }
    }

    /**
     * 获取已注册的 Agent 列表（用于监控）。
     */
    public List<String> listRegisteredAgents() {
        return List.copyOf(agentMap.keySet());
    }

    /**
     * AgentBus 内部事件包装类。
     */
    public static class AgentBusEvent extends org.springframework.context.ApplicationEvent {
        private final AgentMessage message;

        public AgentBusEvent(Object source, AgentMessage message) {
            super(source);
            this.message = message;
        }

        public AgentMessage getMessage() {
            return message;
        }
    }
}
