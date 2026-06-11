package com.onto.oaas.agent.core;

/**
 * Agent 间消息类型枚举。定义了检索、存储、同步、运维四大类消息。
 */
public enum AgentMessageType {
    // ========== Retrieval Pipeline ==========
    /** 查询分析请求 */
    QUERY_ANALYZE,
    /** 查询分析完成 */
    QUERY_ANALYZED,
    /** 语义查询分析请求 (V2) */
    QUERY_ANALYZE_V2,
    /** 语义查询分析完成 (V2) */
    QUERY_ANALYZED_V2,
    /** 召回请求 */
    RECALL_REQUEST,
    /** 召回结果 */
    RECALL_RESULT,
    /** 结构感知召回请求 */
    STRUCTURE_RECALL_REQUEST,
    /** 结构感知召回结果 */
    STRUCTURE_RECALL_RESULT,
    /** 混合检索请求 */
    HYBRID_SEARCH_REQUEST,
    /** 混合检索结果 */
    HYBRID_SEARCH_RESULT,
    /** 重排请求 */
    RERANK_REQUEST,
    /** 重排结果 */
    RERANK_RESULT,
    /** 上下文增强请求 */
    CONTEXT_ENRICH,
    /** 上下文增强完成 */
    CONTEXT_ENRICHED,
    /** 子图扩展请求 */
    SUBGRAPH_EXPAND,
    /** 子图扩展结果 */
    SUBGRAPH_RESULT,
    /** 检索规划请求 */
    RETRIEVAL_PLAN_REQUEST,
    /** 检索规划结果 */
    RETRIEVAL_PLAN_RESULT,

    // ========== Storage ==========
    /** 图数据读取 */
    GRAPH_READ,
    /** 图数据写入 */
    GRAPH_WRITE,
    /** 图操作结果 */
    GRAPH_RESULT,
    /** 索引搜索 */
    INDEX_SEARCH,
    /** 索引更新 */
    INDEX_UPDATE,
    /** 索引重建 */
    INDEX_REBUILD,
    /** 索引操作结果 */
    INDEX_RESULT,

    // ========== Sync ==========
    /** 全量同步请求 */
    SYNC_FULL_REQUEST,
    /** 增量事件处理 */
    SYNC_INCREMENTAL_EVENT,
    /** 同步检查点 */
    SYNC_CHECKPOINT,
    /** 索引重建触发 */
    SYNC_REBUILD_INDEX,

    // ========== Operational ==========
    /** 指标记录 */
    METRICS_RECORD,
    /** 日志记录 */
    LOG_RECORD,
    /** 死信存储 */
    DLQ_STORE,
    /** 健康检查 */
    HEALTH_CHECK,
    /** 用户反馈记录 */
    FEEDBACK_RECORD,
    /** LTR 模型更新 */
    LTR_MODEL_UPDATE
}
