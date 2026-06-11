# OaaS TBox 语义检索服务 Java 开发文档

## 1. 项目概述

本文档描述基于 `docs/概要设计文档md.md` 重新开发的 OaaS TBox 语义检索系统 Java 实现。

**系统定位**：连接本体管理系统与 OAG 推理系统之间的 **TBox 语义检索服务层**。

**核心职责**：
- 通过 HTTP 接口从本体管理系统 **全量同步** TBox 数据
- 通过 Kafka 消费 TBox **增量变更事件**
- 将 TBox 五类对象写入图数据库（Neo4j）
- 构建 TBox 关键词索引和向量索引
- 向 OAG 提供 **Top-K 候选检索** 和 **Hop 子图检索**

**重要边界**：
- ✅ 只处理 TBox（Entity、Relation、Constraint、Function、Rule）
- ❌ 不处理 ABox 实例数据
- ❌ 不负责 OAG 最终推理生成

## 2. 项目结构

```
onto-service-java/src/main/java/com/onto/oaas/
├── aop/                              # AOP 监控与日志
│   ├── LoggingAspect.java            # Controller 请求/响应日志
│   └── MetricsAspect.java            # 方法执行时间监控
├── config/                           # 配置类
│   ├── KafkaConsumerConfig.java      # Kafka 消费者配置
│   └── OaaSProperties.java           # OaaS 业务配置属性
├── consumer/                         # Kafka 消费者
│   └── TBoxKafkaConsumer.java        # TBox 增量事件消费者
├── controller/                       # REST API 控制器
│   ├── TBoxRetrievalController.java  # TBox 检索接口
│   └── SchemaDiscoveryController.java # Schema 发现接口
├── dto/                              # 请求/响应 DTO
│   ├── request/                      # 请求 DTO
│   │   ├── TBoxRetrieveRequest.java
│   │   ├── TBoxSubgraphRequest.java
│   │   ├── TBoxRetrieveWithSubgraphRequest.java
│   │   └── TBoxValidateRequest.java
│   └── response/                     # 响应 DTO
│       ├── TBoxRetrieveResponse.java
│       ├── TBoxSubgraphResponse.java
│       ├── TBoxRetrieveWithSubgraphResponse.java
│       ├── TBoxObjectDetailResponse.java
│       ├── TBoxRelationsResponse.java
│       ├── SchemaDiscoveryResponse.java
│       ├── TBoxValidateResponse.java
│       └── ... (各类 Detail/Summary DTO)
├── exception/                        # 异常处理
│   ├── OaaSException.java
│   └── OaaSGlobalExceptionHandler.java
├── metrics/                          # Micrometer 指标
│   └── OaaSMetrics.java
├── model/                            # 核心数据模型
│   ├── TBoxEntity.java               # TBox 实体类型
│   ├── TBoxRelation.java             # TBox 关系类型
│   ├── TBoxConstraint.java           # TBox 约束
│   ├── TBoxFunction.java             # TBox 业务函数
│   ├── TBoxRule.java                 # TBox 规则
│   ├── TBoxObject.java               # TBox 对象公共接口
│   ├── TBoxIndexDocument.java        # 统一索引文档
│   ├── TBoxSnapshotResponse.java     # 全量同步响应
│   ├── FullSyncCheckpoint.java       # 全量同步检查点
│   ├── EventProcessRecord.java       # 事件处理记录
│   ├── RebuildTask.java              # 重建任务
│   ├── DlqRecord.java                # 死信记录
│   ├── TBoxCandidate.java            # 检索候选对象
│   ├── RecallScore.java              # 召回得分
│   ├── SubgraphNode.java             # 子图节点
│   ├── SubgraphEdge.java             # 子图边
│   ├── QueryIntent.java              # 查询意图
│   ├── PropertyDef.java              # 属性定义
│   ├── InputObject.java              # 输入对象引用
│   ├── FilterDef.java                # 过滤条件定义
│   ├── RelatedObjectRef.java         # 相关对象引用
│   ├── enums/                        # 枚举类型
│   │   ├── TBoxObjectType.java       # ENTITY, RELATION, CONSTRAINT, FUNCTION, RULE
│   │   ├── EventType.java            # 13 种事件类型
│   │   ├── OperationType.java
│   │   ├── ObjectStatus.java         # ACTIVE, DEPRECATED
│   │   ├── Direction.java
│   │   ├── Cardinality.java
│   │   ├── EventProcessStatus.java
│   │   ├── ConstraintType.java
│   │   ├── FunctionType.java
│   │   ├── RuleType.java
│   │   ├── RebuildScope.java
│   │   ├── RebuildStatus.java
│   │   └── Severity.java
│   └── event/                        # Kafka 事件载荷
│       ├── KafkaEventEnvelope.java
│       ├── EntityPayload.java
│       ├── RelationPayload.java
│       ├── ConstraintPayload.java
│       ├── FunctionPayload.java
│       ├── RulePayload.java
│       └── ControlPayload.java
├── repository/                       # 存储层
│   ├── TBoxGraphRepository.java      # 图数据库接口
│   ├── TBoxIndexRepository.java      # 索引存储接口
│   ├── InMemoryTBoxIndexRepository.java # 内存索引实现
│   ├── mybatis/
│   │   ├── EventProcessRecordMapper.java
│   │   ├── FullSyncCheckpointMapper.java
│   │   └── RebuildTaskMapper.java
│   └── neo4j/
│       └── Neo4jTBoxGraphRepository.java
├── service/                          # 业务服务层
│   ├── TBoxIndexBuilder.java         # 索引构建器
│   ├── fullsync/                     # 全量同步
│   │   ├── FullSyncClient.java       # HTTP 客户端
│   │   └── FullSyncService.java      # 全量同步服务
│   ├── event/                        # 事件处理器（10 个 Handler + Dispatcher）
│   │   ├── EventHandler.java
│   │   ├── EventDispatcher.java
│   │   ├── EntityUpsertHandler.java
│   │   ├── EntityDeprecateHandler.java
│   │   ├── RelationUpsertHandler.java
│   │   ├── RelationDeprecateHandler.java
│   │   ├── ConstraintUpsertHandler.java
│   │   ├── ConstraintDeprecateHandler.java
│   │   ├── FunctionUpsertHandler.java
│   │   ├── FunctionDeprecateHandler.java
│   │   ├── RuleUpsertHandler.java
│   │   ├── RuleDeprecateHandler.java
│   │   └── ControlEventHandler.java
│   ├── idempotent/
│   │   └── IdempotencyService.java   # 幂等处理
│   ├── dlq/
│   │   └── DeadLetterQueueService.java # 死信队列
│   ├── rebuild/                      # 索引重建
│   │   ├── IndexRebuildTaskService.java
│   │   └── IndexRebuildExecutor.java
│   ├── health/
│   │   └── OaaSHealthIndicator.java  # 健康检查
│   └── retrieval/                    # 检索服务
│       ├── QueryUnderstandingService.java
│       ├── TBoxRetrievalService.java
│       ├── SubgraphService.java
│       └── TBoxContextService.java
├── task/                             # 定时任务（预留）
└── util/                             # 工具类
    ├── TraceIdGenerator.java
    └── CosineSimilarity.java
```

## 3. API 接口清单

### 3.1 Top-K 候选对象检索
```
POST /v1/tbox/retrieve
```
支持多路召回（精确匹配 + 关键词召回 + 向量召回 + 依赖关系召回），返回排序后的 TBox 对象列表。

### 3.2 Hop 子图检索
```
POST /v1/tbox/subgraph
```
根据起点对象和 hop 层数返回 TBox 子图（nodes + edges）。

### 3.3 组合检索
```
POST /v1/tbox/retrieve-with-subgraph
```
先 Top-K 召回，再对每个候选展开子图。

### 3.4 TBox 对象详情
```
GET /v1/tbox/objects/{objectType}/{objectId}
```

### 3.5 TBox 对象关系查询
```
GET /v1/tbox/objects/{objectType}/{objectId}/relations
```

### 3.6 TBox 对象校验
```
POST /v1/tbox/objects/validate
```

### 3.7 Schema 发现
```
GET /v1/tbox/schema
```

## 4. 同步机制

### 4.1 全量同步
```
OaaS -> HTTP GET /api/v1/ontologies/{ontology_id}/tbox/snapshot
  -> 分页拉取 Entity / Relation / Constraint / Function / Rule
  -> 校验 snapshot_id 一致性
  -> 写入图数据库
  -> 批量构建索引
  -> 记录 full_sync_checkpoint（snapshot_id + event_sequence）
```

### 4.2 Kafka 增量同步
```
Kafka Message -> JSON解析 -> Schema校验 -> 幂等检查
  -> event_sequence > checkpoint 校验 -> EventDispatcher -> Handler处理
  -> 图写入 -> 索引更新 -> ACK
```

### 4.3 支持的 EventType
| 事件类型 | Handler | 说明 |
|---------|---------|------|
| TBOX_ENTITY_UPSERT | EntityUpsertHandler | 同步 Entity |
| TBOX_ENTITY_DEPRECATE | EntityDeprecateHandler | 废弃 Entity |
| TBOX_RELATION_UPSERT | RelationUpsertHandler | 同步 Relation |
| TBOX_RELATION_DEPRECATE | RelationDeprecateHandler | 废弃 Relation |
| TBOX_CONSTRAINT_UPSERT | ConstraintUpsertHandler | 同步 Constraint |
| TBOX_CONSTRAINT_DEPRECATE | ConstraintDeprecateHandler | 废弃 Constraint |
| TBOX_FUNCTION_UPSERT | FunctionUpsertHandler | 同步 Function |
| TBOX_FUNCTION_DEPRECATE | FunctionDeprecateHandler | 废弃 Function |
| TBOX_RULE_UPSERT | RuleUpsertHandler | 同步 Rule |
| TBOX_RULE_DEPRECATE | RuleDeprecateHandler | 废弃 Rule |
| TBOX_VERSION_PUBLISHED | ControlEventHandler | 版本发布 |
| REBUILD_TBOX_INDEX | ControlEventHandler | 触发索引重建 |
| FULL_SYNC_REQUIRED | ControlEventHandler | 触发全量同步 |

## 5. 检索流程

### 5.1 Top-K 检索
```
用户查询 -> QueryUnderstanding(识别对象类型/实体/关系/函数/约束/规则意图)
  -> 多路召回: exactMatch > keywordRecall > vectorRecall > dependencyRecall
  -> 合并去重 -> 归一重排(加权打分) -> 按需获取上下文 -> 返回结果
```

打分公式：
```
final_score = exact_score * 0.35 + keyword_score * 0.25 + vector_score * 0.2
            + object_type_match_score * 0.1 + dependency_score * 0.05 + status_score * 0.05
```

### 5.2 Hop 子图检索
```
起点对象 + hops -> 校验起点 -> 图数据库邻域扩展
  -> 按 relation_types/object_types/direction 过滤
  -> 按 max_nodes/max_edges 裁剪 -> 返回 nodes + edges
```

## 6. 图数据库设计

### 6.1 节点标签
| 标签 | 说明 |
|------|------|
| Ontology | 本体定义 |
| Entity | TBox 实体类型 |
| Relation | TBox 关系类型 |
| Constraint | TBox 约束 |
| Function | TBox 业务语义函数 |
| Rule | TBox 规则 |

### 6.2 关系类型
| 关系 | 说明 |
|------|------|
| DEFINES_ENTITY | Ontology -> Entity |
| DEFINES_RELATION | Ontology -> Relation |
| DEFINES_CONSTRAINT | Ontology -> Constraint |
| DEFINES_FUNCTION | Ontology -> Function |
| DEFINES_RULE | Ontology -> Rule |
| SOURCE_OF | Entity -> Relation |
| TARGET_OF | Entity -> Relation |
| HAS_CONSTRAINT | Entity/Relation/Function/Rule -> Constraint |
| USES_ENTITY | Function/Rule -> Entity |
| USES_RELATION | Function/Rule -> Relation |
| USES_FUNCTION | Function/Rule -> Function |
| PRODUCES | Function/Rule -> Entity/Relation/Function |
| EXTENDS | 继承或扩展关系 |

## 7. 数据库表结构

| 表名 | 说明 |
|------|------|
| tbox_event_process_record | 事件处理状态（幂等追踪） |
| full_sync_checkpoint | 全量同步检查点 |
| tbox_rebuild_task | 索引重建任务 |
| dlq_record | 死信队列记录（内存实现，可选持久化） |

Flyway 迁移脚本位于 `src/main/resources/db/migration/V7~V9`。

## 8. 配置说明

```yaml
oaas:
  kafka:
    topic: tbox-events
    consumer:
      group-id: oaas-consumer-group
    dlq:
      topic: tbox-dlq
  full-sync:
    base-url: ${ONTOLOGY_MGMT_URL:http://localhost:8081}
    page-size: 100
  index:
    rebuild:
      batch-size: 100
      thread-pool-size: 4
  retrieval:
    max-top-k: 100
    default-top-k: 10
  idempotency:
    max-retries: 3
    retry-interval-ms: 5000
```

## 9. 监控指标

通过 Actuator `/actuator/prometheus` 暴露：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| full_sync_started_total | Counter | 全量同步开始数 |
| full_sync_completed_total | Counter | 全量同步完成数 |
| full_sync_failed_total | Counter | 全量同步失败数 |
| kafka_events_consumed_total | Counter | Kafka 事件消费数 |
| kafka_events_processed_total | Counter | 成功处理数 |
| kafka_events_failed_total | Counter | 处理失败数 |
| tbox_index_failed_total | Counter | 索引失败数 |
| dlq_messages_total | Counter | DLQ 消息数 |
| retrieve_empty_total | Counter | 空结果数 |
| full_sync_duration_seconds | Timer | 全量同步耗时 |
| graph_write_latency_seconds | Timer | 图写入延迟 |
| tbox_index_latency_seconds | Timer | 索引写入延迟 |
| tbox_retrieve_latency_seconds | Timer | 检索延迟 |

## 10. 测试

```bash
# 编译
cd onto-service-java && mvn compile

# 运行所有 OaaS 测试
mvn test -Dtest="com.onto.oaas.**"

# 只运行单元测试（不启动 Spring 上下文）
mvn test -Dtest="com.onto.oaas.model.*,com.onto.oaas.util.*,com.onto.oaas.repository.*,com.onto.oaas.service.retrieval.*,com.onto.oaas.service.event.*,com.onto.oaas.service.fullsync.*"

# 只运行 Controller 测试
mvn test -Dtest="com.onto.oaas.controller.*"

# 运行单个测试类
mvn test -Dtest="com.onto.oaas.model.ModelSerializationTest"

# 运行单个测试方法
mvn test -Dtest="com.onto.oaas.model.ModelSerializationTest#shouldSerializeAndDeserializeTBoxEntity"
```

当前测试覆盖：

| 测试类 | 测试数 | 说明 |
|--------|--------|------|
| ModelSerializationTest | 8 | TBox 五类对象 + Kafka 事件 + 索引文档序列化 |
| QueryUnderstandingServiceTest | 6 | 查询意图识别（规则/函数/实体/关系/约束） |
| InMemoryTBoxIndexRepositoryTest | 20 | 内存索引 CRUD、关键词搜索、向量搜索、重建 |
| CosineSimilarityTest | 13 | 余弦相似度计算及边界情况 |
| FullSyncClientTest | 3 | HTTP 分页拉取、对象类型过滤 |
| TBoxRetrievalControllerTest | 5 | Top-K/子图/组合/详情/校验 API |
| SchemaDiscoveryControllerTest | 1 | Schema 发现 API |
| TBoxRetrievalServiceTest | 5 | 精确匹配、关键词召回、合并去重、重排、topK |
| SubgraphServiceTest | 4 | 0跳/1跳扩展、maxNodes/maxEdges 裁剪 |
| EventDispatcherTest | 3 | 事件分发、幂等跳过、未知事件 |
| OaaSApplicationContextTest | 1 | Spring Boot 上下文加载 |

**总计：69 tests, 全部通过**

## 11. 后续扩展建议

1. **向量索引替换**：当前使用内存实现，生产环境建议替换为 Milvus / Elasticsearch
2. **Embedding 服务**：接入 LLM Embedding 服务生成 TBox 对象语义向量
3. **缓存层**：对高频查询的 Schema 和对象详情增加 Redis 缓存
4. **全量同步断点续传**：支持分页断点记录，失败后从断点继续
5. **权限控制**：增加 API 认证与权限校验
6. **TBox 对象推荐**：基于依赖关系自动推荐相关对象
