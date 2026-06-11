# OaaS (Ontology-aware Retrieval as a Service) Java 开发文档

## 1. 项目概述

本文档描述基于 `docs/概要设计文档md.md` 重新开发的 OaaS 系统 Java 实现。

OaaS 是连接本体管理系统与 OAG 推理系统之间的 ABox 实体检索服务层，负责：
- 通过 Kafka 同步 TBox 与 ABox 数据
- 将数据写入图数据库（Neo4j）
- 构建 ABox Entity 检索索引
- 向 OAG 提供实体检索、详情、Schema 查询接口

## 2. 项目结构

```
to-service-java/src/main/java/com/onto/oaas/
├── aop/                          # AOP 监控与日志
│   ├── LoggingAspect.java        # Controller 请求/响应日志
│   └── MetricsAspect.java        # 方法执行时间监控
├── config/                       # 配置类
│   ├── KafkaConsumerConfig.java  # Kafka 消费者配置
│   └── OaaSProperties.java       # OaaS 业务配置属性
├── consumer/                     # Kafka 消费者
│   └── OaasKafkaConsumer.java    # 本体事件消费者
├── controller/                   # REST API 控制器
│   ├── EntityRetrievalController.java   # 实体检索接口
│   └── SchemaDiscoveryController.java   # Schema 发现接口
├── dto/                          # 请求/响应 DTO
│   ├── EntityRetrieveRequest.java
│   ├── EntityRetrieveResponse.java
│   ├── EntityDetailResponse.java
│   ├── EntityRelationsResponse.java
│   ├── EntityValidateRequest.java
│   ├── EntityValidateResponse.java
│   ├── SchemaDiscoveryResponse.java
│   └── ...
├── exception/                    # 异常处理
│   ├── OaaSException.java
│   └── OaaSGlobalExceptionHandler.java
├── metrics/                      # Micrometer 指标
│   └── OaaSMetrics.java
├── model/                        # 核心数据模型
│   ├── AboxEntity.java           # ABox 实体
│   ├── AboxRelation.java         # ABox 关系
│   ├── AboxState.java            # ABox 状态
│   ├── TBoxClass.java            # TBox 概念类
│   ├── TBoxRelation.java         # TBox 关系类型
│   ├── TBoxConstraint.java       # TBox 约束
│   ├── EntityIndexDocument.java  # 实体索引文档
│   ├── CurrentProjection.java    # 当前有效视图
│   ├── EventProcessRecord.java   # 事件处理记录
│   ├── EntityCandidate.java      # 检索候选实体
│   ├── RecallScore.java          # 召回得分
│   ├── EntityContext.java        # 实体上下文
│   ├── DlqRecord.java            # 死信记录
│   ├── RebuildTask.java          # 重建任务
│   ├── QueryIntent.java          # 查询意图
│   ├── enums/                    # 枚举类型
│   │   ├── EventType.java
│   │   ├── OperationType.java
│   │   ├── EntityStatus.java
│   │   ├── RelationStatus.java
│   │   ├── ProjectionType.java
│   │   ├── EventProcessStatus.java
│   │   ├── Direction.java
│   │   └── Cardinality.java
│   └── event/                    # Kafka 事件载荷
│       ├── KafkaEventEnvelope.java
│       ├── EntityPayload.java
│       ├── RelationPayload.java
│       ├── StatePayload.java
│       ├── TBoxRelationPayload.java
│       └── ControlPayload.java
├── repository/                   # 存储层
│   ├── GraphRepository.java              # 图数据库接口
│   ├── EntityIndexRepository.java        # 索引存储接口
│   ├── InMemoryEntityIndexRepository.java # 内存索引实现
│   ├── mybatis/
│   │   ├── EventProcessRecordMapper.java
│   │   └── CurrentProjectionMapper.java
│   └── neo4j/
│       └── Neo4jGraphRepository.java
├── service/                      # 业务服务层
│   ├── EntityIndexBuilder.java           # 索引构建器
│   ├── dlq/
│   │   └── DeadLetterQueueService.java   # 死信队列服务
│   ├── event/                    # 事件处理器
│   │   ├── EventHandler.java
│   │   ├── EventDispatcher.java
│   │   ├── EntityUpsertHandler.java
│   │   ├── EntityInvalidateHandler.java
│   │   ├── RelationAssertHandler.java
│   │   ├── RelationInvalidateHandler.java
│   │   ├── StateChangeHandler.java
│   │   ├── TBoxClassUpsertHandler.java
│   │   ├── TBoxRelationUpsertHandler.java
│   │   ├── TBoxConstraintUpsertHandler.java
│   │   └── ControlEventHandler.java
│   ├── health/
│   │   └── OaaSHealthIndicator.java      # 健康检查
│   ├── idempotent/
│   │   └── IdempotencyService.java       # 幂等处理
│   ├── projection/
│   │   └── CurrentProjectionService.java # 当前视图服务
│   ├── rebuild/                  # 索引重建
│   │   ├── IndexRebuildTask.java
│   │   └── IndexRebuildExecutor.java
│   └── retrieval/                # 检索服务
│       ├── QueryUnderstandingService.java
│       ├── EntityRetrievalService.java
│       └── EntityContextService.java
├── task/                         # 定时任务（预留）
└── util/                         # 工具类
    ├── TraceIdGenerator.java
    └── CosineSimilarity.java
```

## 3. API 接口清单

### 3.1 实体检索
```
POST /v1/entities/retrieve
```
支持多路召回（精确匹配 + 关键词召回 + 向量召回），返回候选实体列表。

### 3.2 实体详情
```
GET /v1/entities/{entityId}?ontology_id=xxx&include_states=true&include_relations=true
```

### 3.3 实体关系查询
```
GET /v1/entities/{entityId}/relations?relation_types=has_component&direction=BOTH&limit=20
```

### 3.4 实体校验
```
POST /v1/entities/validate
```

### 3.5 Schema 发现
```
GET /v1/schema?ontology_id=xxx&include_constraints=true
```

## 4. Kafka 事件处理

### 4.1 支持的 EventType
| 事件类型 | Handler | 说明 |
|---------|---------|------|
| TBOX_CLASS_UPSERT | TBoxClassUpsertHandler | 同步概念类到图数据库 |
| TBOX_RELATION_UPSERT | TBoxRelationUpsertHandler | 同步关系类型到图数据库 |
| TBOX_CONSTRAINT_UPSERT | TBoxConstraintUpsertHandler | 同步约束规则 |
| ABOX_ENTITY_UPSERT | EntityUpsertHandler | 写入实体+构建索引+更新投影 |
| ABOX_ENTITY_INVALIDATE | EntityInvalidateHandler | 失效实体 |
| ABOX_RELATION_ASSERT | RelationAssertHandler | 写入关系+更新投影 |
| ABOX_RELATION_INVALIDATE | RelationInvalidateHandler | 失效关系 |
| ABOX_STATE_CHANGE | StateChangeHandler | 状态变更+投影更新 |
| REBUILD_ENTITY_INDEX | ControlEventHandler | 触发索引重建 |

### 4.2 消费流程
```
Kafka Message -> JSON解析 -> Schema校验 -> 幂等检查 -> EventDispatcher -> Handler处理 -> 图写入 -> 索引更新 -> 投影更新 -> ACK
```

## 5. 检索流程

```
用户查询 -> QueryUnderstanding(识别名称/编码/别名/类型) -> 
多路召回(精确匹配 > 关键词召回 > 向量召回) -> 
合并去重 -> 归一重排(加权打分) -> 按需获取上下文 -> 返回结果
```

打分公式：
```
final_score = exact_score * 0.4 + keyword_score * 0.25 + vector_score * 0.2 + type_match_score * 0.1 + status_score * 0.05
```

## 6. 数据库表结构

| 表名 | 说明 |
|------|------|
| event_process_record | 事件处理状态（幂等追踪） |
| current_projection | 当前有效视图快照 |
| dlq_record | 死信队列记录 |
| rebuild_task | 索引重建任务 |

Flyway 迁移脚本位于 `src/main/resources/db/migration/V3~V6`。

## 7. 配置说明

```yaml
oaas:
  kafka:
    topic: ontology-events              # Kafka Topic
    consumer:
      group-id: oaas-consumer-group     # 消费者组
    dlq:
      topic: ontology-dlq               # 死信队列Topic
  index:
    rebuild:
      batch-size: 100                   # 重建批次大小
      thread-pool-size: 4               # 重建线程数
  retrieval:
    max-top-k: 100                      # 最大返回数
    default-top-k: 10                   # 默认返回数
  idempotency:
    max-retries: 3                      # 最大重试次数
    retry-interval-ms: 5000             # 重试间隔
```

## 8. 监控指标

通过 Actuator `/actuator/prometheus` 暴露：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| kafka_events_consumed_total | Counter | Kafka事件消费数 |
| kafka_events_processed_total | Counter | 成功处理数 |
| kafka_events_failed_total | Counter | 处理失败数 |
| graph_write_latency_seconds | Timer | 图写入延迟 |
| entity_index_latency_seconds | Timer | 索引写入延迟 |
| entity_retrieve_latency_seconds | Timer | 检索延迟 |
| dlq_messages_total | Counter | DLQ消息数 |

## 9. 测试

```bash
# 编译
cd onto-service-java && mvn compile

# 运行 OaaS 相关测试
mvn test -Dtest="com.onto.oaas.**"
```

当前测试覆盖：
- 模型序列化/反序列化 (7 tests)
- 查询理解服务 (12 tests)
- 内存索引仓库 (21 tests)
- 余弦相似度计算 (17 tests)

## 10. 后续扩展建议

1. **向量索引替换**：当前使用内存实现，生产环境建议替换为 Milvus / Elasticsearch
2. **Kafka 配置完善**：配置消费者并发数、重试策略、DLQ 自动转发
3. **Embedding 服务**：接入 LLM Embedding 服务生成实体语义向量
4. **缓存层**：对高频查询的实体详情增加 Redis 缓存
5. **多跳关系**：扩展 EntityContextService 支持 2-3 跳关系查询
6. **权限控制**：增加 API 认证与权限校验
