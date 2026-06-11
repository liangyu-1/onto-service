package com.onto.oaas.agent.core;

/**
 * Agent 抽象接口。所有智能体必须实现此接口，通过 AgentBus 注册并接收消息。
 */
public interface Agent {

    /**
     * Agent 唯一名称。
     */
    String getName();

    /**
     * 判断当前 Agent 是否能处理该消息。
     * AgentBus 根据此方法决定将消息路由给哪个 Agent。
     */
    boolean canHandle(AgentMessage message);

    /**
     * 处理消息。AgentBus 在 canHandle 返回 true 时调用此方法。
     * 处理完成后，Agent 应通过 AgentBus 发布后续消息（而非直接返回）。
     */
    void handle(AgentMessage message);
}
