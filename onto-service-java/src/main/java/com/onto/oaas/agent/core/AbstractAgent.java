package com.onto.oaas.agent.core;

import java.util.Set;
import lombok.extern.slf4j.Slf4j;

/**
 * Agent 抽象基类，简化 Agent 实现。
 *
 * <p>子类只需：</p>
 * <ol>
 *   <li>实现 {@link #getName()} 返回 Agent 名称</li>
 *   <li>在构造器中调用 {@link #subscribeTo(AgentMessageType...)} 声明感兴趣的消息类型</li>
 *   <li>实现 {@link #onMessage(AgentMessage)} 处理消息</li>
 * </ol>
 */
@Slf4j
public abstract class AbstractAgent implements Agent {

    private final AgentBus agentBus;
    private final Set<AgentMessageType> subscribedTypes = java.util.concurrent.ConcurrentHashMap.newKeySet();

    protected AbstractAgent(AgentBus agentBus) {
        this.agentBus = agentBus;
        agentBus.register(this);
    }

    /**
     * 订阅指定的消息类型。应在子类构造器中调用。
     */
    protected void subscribeTo(AgentMessageType... types) {
        for (AgentMessageType type : types) {
            subscribedTypes.add(type);
        }
    }

    @Override
    public boolean canHandle(AgentMessage message) {
        return message != null && subscribedTypes.contains(message.getType());
    }

    @Override
    public void handle(AgentMessage message) {
        log.debug("[{}] Handling message: type={}, correlationId={}",
                getName(), message.getType(), message.getCorrelationId());
        try {
            onMessage(message);
        } catch (Exception e) {
            log.error("[{}] Failed to handle message: type={}, correlationId={}",
                    getName(), message.getType(), message.getCorrelationId(), e);
            onError(message, e);
        }
    }

    /**
     * 子类实现：处理消息的核心逻辑。
     */
    protected abstract void onMessage(AgentMessage message);

    /**
     * 子类可选重写：处理异常。
     */
    protected void onError(AgentMessage message, Exception e) {
        // 默认不做任何处理，子类可重写
    }

    /**
     * 向总线发布消息。
     */
    protected void publish(AgentMessage message) {
        if (message.getFromAgent() == null) {
            message.setFromAgent(getName());
        }
        agentBus.publish(message);
    }

    /**
     * 向指定 Agent 发送消息。
     */
    protected void sendTo(String agentName, AgentMessage message) {
        if (message.getFromAgent() == null) {
            message.setFromAgent(getName());
        }
        agentBus.sendTo(agentName, message);
    }
}
