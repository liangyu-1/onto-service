# 工业级本体语义检索服务（OaaS）概要设计文档

## 1. 系统背景、定位与目标

### 1.1 建设背景

OAG 推理系统在执行推理前，需要先理解当前本体中有哪些领域、类型、属性、关系和可复用函数。例如，用户提出“统计高风险设备数量”时，OAG 需要先知道：

1. 是否存在设备相关的 Domain 和 Type。
2. 设备 Type 下有哪些属性可以展示或过滤。
3. 设备 Type 和其他 Type 之间有哪些 Relationship。
4. 是否存在用于统计、聚合、过滤或评分的 Function。
5. Function 下是否存在可执行或可参考的 SQL Rule。

本系统只负责检索这些 TBox 语义对象，不负责查询具体设备、具体工单、具体状态等 ABox 实例数据。

### 1.2 系统定位

```text
本体管理系统
  ├── 维护 TBox：Domain / Type / Property / Relationship / Function / Rule
  ├── 提供 TBox 全量获取接口
  └── 通过 Kafka 发布 TBox 增量变更事件

OaaS 本体语义检索服务
  ├── 调用本体管理系统接口全量获取 TBox
  ├── 消费 Kafka TBox 增量变更事件
  ├── 将 TBox 数据写入图数据库
  ├── 构建 TBox 关键词索引和向量索引
  └── 向 OAG 提供 TBox 检索、子图检索、bindings 查询、图节点类型和图边类型查询接口

OAG 推理系统
  ├── 调用 OaaS 检索 TBox 语义对象
  ├── 基于返回的 TBox 对象组织推理计划
  ├── 如需 ABox 数据，调用其他系统查询具体实例
  └── 生成最终推理结果
```

### 1.3 建设目标

| 目标          | 说明                                                                           |
| ----------- | ---------------------------------------------------------------------------- |
| TBox 全量同步   | 从本体管理系统获取完整 TBox 快照                                                          |
| Kafka 增量同步  | 通过 Kafka 消费 TBox 增量变更事件                                                      |
| 图存储         | 将 Domain、Type、Property、Relationship、Function、Rule 写入图数据库                     |
| 语义索引        | 构建关键词索引和向量索引                                                                 |
| Top-K 检索    | 根据自然语言查询返回候选 TBox 对象                                                         |
| Hop 子图检索    | 根据起点对象和 hop 层数返回 TBox 子图                                                     |
| bindings 查询 | 精准查询 Property 对应的数据源、库、表、列；查询 Relationship 的连接字段；查询 Function / Rule 的 SQL 定义 |
| 可重建         | 支持基于全量接口重建图数据和索引                                                             |

### 1.4 非目标边界

本版本系统不承担以下职责：

1. 不提供本体编辑能力。
2. 不负责 ABox 实例数据查询。
3. 不负责文档解析和文档证据检索。
4. 不建设权限、认证、审计相关能力。
5. 不处理独立的 Constraint 和全局 Rule；本版本的 Rule 仅指 Function 下的 SQL Rule。
6. 不负责 OAG 最终回答生成。


## 2. 总体架构设计

### 2.1 逻辑架构

```text
+------------------------------------------------------------------+
|                         OAG 推理系统                              |
|  - 调用 Top-K 检索获取候选 TBox 对象                               |
|  - 调用 Hop 子图检索获取 TBox 结构上下文                            |
|  - 调用 bindings 点查询获取数据源、库表列和 SQL 定义                 |
|  - 如需 ABox 数据，调用其他系统查询实例                             |
+------------------------------------------------------------------+
                              |
                              | HTTP/gRPC
                              v
+------------------------------------------------------------------+
|                     OaaS 本体语义检索服务                          |
|                                                                  |
|  +------------------+  +------------------+  +----------------+  |
|  | TBox 检索 API 层  |  | 子图检索层         |  | bindings 查询层 |  |
|  +------------------+  +------------------+  +----------------+  |
|                                                                  |
|  +------------------+  +------------------+  +----------------+  |
|  | 查询理解模块       |  | 多路召回模块       |  | 语义对象重排模块 |  |
|  +------------------+  +------------------+  +----------------+  |
+------------------------------------------------------------------+
            |                         |                         |
            v                         v                         v
+----------------------+  +----------------------+  +----------------------+
| 图数据库              |  | 向量索引              |  | 关键词索引            |
| - Domain             |  | - TBox Object Vector  |  | - 名称/描述/路径       |
| - Type               |  | - Function Vector     |  | - 属性/关系/函数       |
| - Property           |  | - Rule Vector         |  | - 数据绑定字段/SQL     |
| - Relationship       |  |                      |  |                        |
| - Function/Rule      |  |                      |  |                        |
+----------------------+  +----------------------+  +----------------------+
            ^                         ^                         ^
            |                         |                         |
+------------------------------------------------------------------+
|                     TBox 同步与索引构建层                           |
|  - Full Sync Client                                                |
|  - Kafka Consumer                                                  |
|  - 图写入                                                           |
|  - TBox Index Document 生成                                         |
|  - 索引更新                                                         |
|  - Checkpoint 与失败重试                                            |
+------------------------------------------------------------------+
                              ^
                              |
             +----------------+----------------+
             |                                 |
             | HTTP Full Sync                  | Kafka Incremental Events
             |                                 |
+------------------------------------------------------------------+
|                         本体管理系统                                |
|  - TBox 管理                                                        |
|  - TBox 全量获取接口                                                 |
|  - TBox 增量事件发布                                                 |
+------------------------------------------------------------------+
```

### 2.2 核心数据流

#### 2.2.1 本体管理系统同步链路

```text
全量同步：
OaaS 调用全量接口
  ↓
本体管理系统返回 timestamp + domains + code + message
  ↓
OaaS 解析 domains 下的 domain / type / property / relationship / function / rule
  ↓
写入图数据库
  ↓
生成 TBox Index Document
  ↓
写入关键词索引和向量索引
  ↓
记录 full_sync_checkpoint

Kafka 增量同步：
本体管理系统发布 Kafka 事件
  ↓
OaaS Consumer 消费事件
  ↓
解析 payload.timestamp / payload.domains / payload.code / payload.message
  ↓
更新图数据库
  ↓
更新关键词索引和向量索引
  ↓
记录事件处理状态
  ↓
提交 Kafka Offset
```

#### 2.2.2 OAG 检索链路

```text
OAG 提交查询
  ↓
Top-K 检索：返回候选 TBox 对象
  或
Hop 子图检索：返回指定起点对象周边子图
  或
bindings 点查询：返回数据源、库、表、列和 SQL 定义
```

---

## 3. 与本体管理系统对接设计

### 3.1 全量获取接口

#### Endpoint

```http
GET /api/v1/ontologies/{ontology_id}/tbox/snapshot
```

#### Query Parameters

| 参数               | 说明               |
| ---------------- | ---------------- |
| ontology_version | 指定本体版本，默认 latest |

#### Response

```json
{
  "timestamp": "2026-05-20T09:00:00.123456789Z",
  "domains": {
    "equipment_domain": {
      "name": "设备域",
      "description": "描述设备、部件、故障等对象的领域",
      "types": {
        "equipment": {
          "name": "设备",
          "description": "工业现场中的物理设备",
          "display_property": "equipment_name",
          "properties": {
            "equipment_id": {
              "name": "设备ID",
              "type": "string",
              "description": "设备唯一标识",
              "binding": {
                "datasource": "iot_ds",
                "schema": "public",
                "database": "iot_db",
                "table": "dim_equipment",
                "column": "equipment_id"
              },
              "pk_column": true
            },
            "equipment_name": {
              "name": "设备名称",
              "type": "string",
              "description": "设备名称",
              "binding": {
                "datasource": "iot_ds",
                "schema": "public",
                "database": "iot_db",
                "table": "dim_equipment",
                "column": "equipment_name"
              },
              "pk_column": false
            }
          },
          "relationships": {
            "has_fault": {
              "name": "发生故障",
              "description": "设备与故障记录之间的关联关系",
              "link_properties": [
                {
                  "equipment_domain.equipment.equipment_id": "fault_domain.fault.equipment_id"
                }
              ],
              "cardinality": "one2many",
              "type": "left_join"
            }
          },
          "functions": {
            "equipment_fault_stat": {
              "name": "设备故障统计",
              "description": "按设备维度统计故障次数",
              "dimensions": [
                "equipment_domain.equipment.equipment_id",
                "equipment_domain.equipment.equipment_name"
              ],
              "rules": {
                "fault_count_rule": {
                  "name": "故障次数统计规则",
                  "description": "按设备统计故障数量",
                  "type": "sql",
                  "defination": "select equipment_id, count(fault_id) as fault_count from fact_fault where status = 'active' group by equipment_id;"
                }
              }
            }
          }
        }
      }
    }
  },
  "code": "0",
  "message": "success"
}
```

### 3.2 Kafka 增量事件

#### Topic

| Topic                        | 说明             |
| ---------------------------- | -------------- |
| ontology_tbox_events         | TBox 对象增量变更事件  |
| ontology_tbox_control_events | 全量重建、索引重建等控制事件 |
| ontology_tbox_dlq            | 消费失败或无法解析的死信事件 |

#### 事件类型

| 事件类型                | 说明                                               |
| ------------------- | ------------------------------------------------ |
| DOMAIN_UPSERT       | 新增或修改 Domain                                     |
| TYPE_UPSERT         | 新增或修改 Type                                       |
| PROPERTY_UPSERT     | 新增或修改 Property                                   |
| RELATIONSHIP_UPSERT | 新增或修改 Relationship                               |
| FUNCTION_UPSERT     | 新增或修改 Function                                   |
| RULE_UPSERT         | 新增或修改 Function 下的 Rule                           |
| DELETE              | 删除或失效任意 TBox 对象，具体对象类型由 payload.domains 中的层级路径确定 |
| REBUILD_INDEX       | 触发 TBox 索引重建                                     |
| FULL_SYNC_REQUIRED  | 要求 OaaS 重新执行全量同步                                 |

#### Kafka 消息结构

Kafka 增量事件固定包含四个字段：`event_id`、`event_sequence`、`event_type`、`payload`。

`payload` 内部结构与全量接口 Response 保持一致，包含 `timestamp`、`domains`、`code`、`message`。

```json
{
  "event_id": "evt_20260520_0001",
  "event_sequence": 102401,
  "event_type": "RULE_UPSERT",
  "payload": {
    "timestamp": "2026-05-20T09:00:00.123456789Z",
    "domains": {
      "equipment_domain": {
        "name": "设备域",
        "description": "描述设备、部件、故障等对象的领域",
        "types": {
          "equipment": {
            "name": "设备",
            "description": "工业现场中的物理设备",
            "display_property": "equipment_name",
            "properties": {},
            "relationships": {},
            "functions": {
              "equipment_fault_stat": {
                "name": "设备故障统计",
                "description": "按设备维度统计故障次数",
                "dimensions": [
                  "equipment_domain.equipment.equipment_id",
                  "equipment_domain.equipment.equipment_name"
                ],
                "rules": {
                  "fault_count_rule": {
                    "name": "故障次数统计规则",
                    "description": "按设备统计故障数量",
                    "type": "sql",
                    "defination": "select equipment_id, count(fault_id) as fault_count from fact_fault where status = 'active' group by equipment_id;"
                  }
                }
              }
            }
          }
        }
      }
    },
    "code": "0",
    "message": "success"
  }
}
```

#### 字段说明

| 字段                | 是否必填 | 说明                             |
| ----------------- | ---- | ------------------------------ |
| event_id          | 是    | Kafka 事件唯一 ID，用于幂等去重           |
| event_sequence    | 是    | Kafka 事件序号，用于判断增量事件顺序          |
| event_type        | 是    | 事件类型                           |
| payload.timestamp | 是    | 本体管理系统服务端开始执行的时间戳，纳秒级          |
| payload.domains   | 是    | 本次变更涉及的领域结构，结构与全量接口 domains 一致 |
| payload.code      | 是    | 处理结果编码                         |
| payload.message   | 是    | 处理结果描述                         |

#### Kafka Message Key

| 事件类型                | Kafka Message Key                                                                                                                                                                                     |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DOMAIN_UPSERT       | domain_key                                                                                                                                                                                            |
| TYPE_UPSERT         | domain_key.type_key                                                                                                                                                                                   |
| PROPERTY_UPSERT     | domain_key.type_key.property_key                                                                                                                                                                      |
| RELATIONSHIP_UPSERT | domain_key.type_key.relationship_key                                                                                                                                                                  |
| FUNCTION_UPSERT     | domain_key.type_key.function_key                                                                                                                                                                      |
| RULE_UPSERT         | domain_key.type_key.function_key.rule_key                                                                                                                                                             |
| DELETE              | 被删除对象的 object_path，例如 domain_key、domain_key.type_key、domain_key.type_key.property_key、domain_key.type_key.relationship_key、domain_key.type_key.function_key、domain_key.type_key.function_key.rule_key |

#### DELETE 事件示例

Function 删除示例：

```json
{
  "event_id": "evt_delete_20260520_0001",
  "event_sequence": 102502,
  "event_type": "DELETE",
  "payload": {
    "timestamp": "2026-05-20T10:01:00.123456789Z",
    "domains": {
      "equipment_domain": {
        "types": {
          "equipment": {
            "functions": {
              "equipment_fault_stat": {}
            }
          }
        }
      }
    },
    "code": "0",
    "message": "success"
  }
}
```

对应 Kafka Message Key：

```text
Kafka Message Key = equipment_domain.equipment.functions.equipment_fault_stat
```

Rule 删除示例：

```json
{
  "event_id": "evt_delete_20260520_0002",
  "event_sequence": 102503,
  "event_type": "DELETE",
  "payload": {
    "timestamp": "2026-05-20T10:02:00.123456789Z",
    "domains": {
      "equipment_domain": {
        "types": {
          "equipment": {
            "functions": {
              "equipment_fault_stat": {
                "rules": {
                  "fault_count_rule": {}
                }
              }
            }
          }
        }
      }
    },
    "code": "0",
    "message": "success"
  }
}
```

对应 Kafka Message Key：

```text
Kafka Message Key = equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule
```

#### REBUILD_INDEX 事件示例

触发 TBox 索引重建，适用于本体管理系统完成批量变更后要求 OaaS 重建索引的场景：

```json
{
  "event_id": "evt_rebuild_20260520_0001",
  "event_sequence": 102601,
  "event_type": "REBUILD_INDEX",
  "payload": {
    "timestamp": "2026-05-20T11:00:00.123456789Z",
    "domains": {
      "equipment_domain": {}
    },
    "code": "0",
    "message": "success"
  }
}
```


#### FULL_SYNC_REQUIRED 事件示例

要求 OaaS 重新执行全量同步，适用于本体管理系统数据修复、版本升级或强制对齐场景：

```json
{
  "event_id": "evt_fullsync_20260520_0001",
  "event_sequence": 102701,
  "event_type": "FULL_SYNC_REQUIRED",
  "payload": {
    "timestamp": "2026-05-20T12:00:00.123456789Z",
    "domains": {},
    "code": "0",
    "message": "success"
  }
}
```


### 3.3 同步处理流程

#### 全量同步流程

```text
调用本体管理系统 TBox Snapshot 接口
  ↓
读取 timestamp / domains / code / message
  ↓
遍历 domains
  ↓
解析 domain.types
  ↓
解析 type.properties / type.relationships / type.functions
  ↓
解析 function.rules
  ↓
写入图数据库
  ↓
生成 TBox Index Document
  ↓
写入关键词索引和向量索引
  ↓
记录 full_sync_checkpoint：timestamp
```

#### Kafka 消费流程

```text
接收 Kafka 消息
  ↓
根据 event_id 执行幂等校验
  ↓
解析 payload.timestamp / payload.domains
  ↓
遍历 domains 下的变更结构
  ↓
根据 event_type 判断执行 UPSERT 或 DELETE
  ↓
当 event_type = DELETE 时，根据 payload.domains 的层级路径和 Kafka Message Key 定位被删除对象
  ↓
更新图数据库中的 TBox 对象
  ↓
生成或更新 TBox Index Document
  ↓
写入关键词索引与向量索引
  ↓
记录事件处理状态
  ↓
提交 Kafka Offset
```

### 3.4 幂等与一致性

#### 事件处理状态表

| 字段                | 说明                                                                 |
| ----------------- | ------------------------------------------------------------------ |
| event_id          | 事件唯一 ID                                                            |
| event_sequence    | 事件序号                                                               |
| event_type        | 事件类型                                                               |
| object_path       | 对象路径，如 `equipment_domain.equipment.functions.equipment_fault_stat` |
| graph_status      | 图写入状态：PENDING / SUCCESS / FAILED                                   |
| tbox_index_status | 索引状态：PENDING / SUCCESS / FAILED                                    |
| retry_count       | 重试次数                                                               |
| last_error        | 最近一次错误信息                                                           |
| kafka_topic       | Kafka Topic                                                        |
| kafka_partition   | Kafka 分区                                                           |
| kafka_offset      | Kafka Offset                                                       |
| created_time      | 创建时间                                                               |
| updated_time      | 更新时间                                                               |

#### 图与索引一致性

| 场景                 | 处理方式                                                                                                                                                |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 图写入成功，索引写入失败       | 记录索引失败状态，进入重试队列                                                                                                                                     |
| 索引写入成功，图写入失败       | 不提交 Kafka Offset，事件重放时按 event_id 幂等处理                                                                                                               |
| Property 绑定变化      | 更新图数据库并重建该 Property 所在 Type 的索引                                                                                                                     |
| Relationship 变化    | 更新图数据库并重建该 Relationship 及相关 Type 的索引                                                                                                                |
| Function / Rule 变化 | 更新图数据库并重建 Function 和 Rule 索引                                                                                                                        |
| DELETE 事件          | 根据 Kafka Message Key 和 payload.domains 层级路径定位对象；若删除 Domain / Type，则同时删除或失效下级对象及相关索引；若删除 Property / Relationship / Function / Rule，则删除或失效对应对象并重建相关索引 |
| 本体管理系统要求重建         | 按 REBUILD_INDEX 或 FULL_SYNC_REQUIRED 事件执行                                                                                                           |

---

## 4. 图存储与索引构建设计

### 4.1 图节点类型

| 节点标签         | 说明                 |
| ------------ | ------------------ |
| Domain       | 领域                 |
| Type         | 类型                 |
| Property     | 属性                 |
| Relationship | 关系                 |
| Function     | 函数                 |
| Rule         | Function 下的 SQL 规则 |

### 4.2 图关系类型

| 关系               | 起点           | 终点           | 说明       |
| ---------------- | ------------ | ------------ | -------- |
| HAS_TYPE         | Domain       | Type         | 领域包含类型   |
| HAS_PROPERTY     | Type         | Property     | 类型包含属性   |
| HAS_RELATIONSHIP | Type         | Relationship | 类型包含关系   |
| HAS_FUNCTION     | Type         | Function     | 类型包含函数   |
| HAS_RULE         | Function     | Rule         | 函数包含规则   |
| LINK_TO          | Relationship | Property     | 关系连接到属性  |
| USES_DIMENSION   | Function     | Property     | 函数使用维度属性 |

### 4.3 TBox Index Document

```json
{
  "object_path": "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule",
  "object_type": "Rule",
  "name": "故障次数统计规则",
  "description": "按设备统计故障数量",
  "text_for_embedding": "设备域 设备 设备故障统计 故障次数统计规则 SQL 统计设备关联的故障数量 group by equipment_id",
  "keywords": ["设备", "故障", "统计", "SQL", "group by"],
  "domain_key": "equipment_domain",
  "type_key": "equipment",
  "function_key": "equipment_fault_stat",
  "rule_key": "fault_count_rule",
  "rule_type": "sql",
  "defination": "select equipment_id, count(fault_id) as fault_count from fact_fault where status = 'active' group by equipment_id;",
  "updated_time": "2026-05-20T09:00:00.123456789Z"
}
```

### 4.4 索引对象范围

| 对象类型         | object_path 示例                                                                     |
| ------------ | ---------------------------------------------------------------------------------- |
| Domain       | `equipment_domain`                                                                 |
| Type         | `equipment_domain.equipment`                                                       |
| Property     | `equipment_domain.equipment.properties.equipment_name`                             |
| Relationship | `equipment_domain.equipment.relationships.has_fault`                               |
| Function     | `equipment_domain.equipment.functions.equipment_fault_stat`                        |
| Rule         | `equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule` |

---

## 5. 与 OAG 系统对接设计

OAG 对接能力包括：Top-K 候选对象检索、Hop 子图检索、bindings 点查询、本体图节点类型查询、本体图边类型查询、Schema Discovery。

### 5.1 Top-K 候选对象检索接口

#### Endpoint

```http
POST /v1/tbox/retrieve
```

#### Request

```json
{
  "query": "统计设备故障次数",
  "top_k": 10,
  "filters": {
    "object_types": ["Function", "Rule", "Type"]
  },
  "options": {
    "enable_keyword_recall": true,
    "enable_vector_recall": true,
    "include_context": true
  }
}
```

#### Response

```json
{
  "query_id": "q_20260520_0001",
  "mode": "top_k",
  "objects": [
    {
      "object_path": "equipment_domain.equipment.functions.equipment_fault_stat",
      "object_type": "Function",
      "name": "设备故障统计",
      "description": "按设备维度统计故障次数",
      "score": 0.94,
      "matched_fields": ["name", "description"],
      "context": {
        "domain_key": "equipment_domain",
        "type_key": "equipment",
        "dimensions": [
          "equipment_domain.equipment.equipment_id",
          "equipment_domain.equipment.equipment_name"
        ],
        "rules": [
          "fault_count_rule"
        ]
      }
    },
    {
      "object_path": "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule",
      "object_type": "Rule",
      "name": "故障次数统计规则",
      "description": "按设备统计故障数量",
      "score": 0.91,
      "matched_fields": ["name", "description", "defination"]
    }
  ]
}
```

### 5.2 Hop 子图检索接口

#### Endpoint

```http
POST /v1/tbox/subgraph
```

#### Request

```json
{
  "start_object_path": "equipment_domain.equipment.functions.equipment_fault_stat",
  "hops": 2,
  "direction": "BOTH",
  "filters": {
    "object_types": ["Domain", "Type", "Property", "Relationship", "Function", "Rule"],
    "relation_types": ["HAS_FUNCTION", "HAS_RULE", "USES_DIMENSION"]
  },
  "options": {
    "max_nodes": 50,
    "max_edges": 100,
    "include_node_detail": true
  }
}
```

#### Response

```json
{
  "query_id": "q_20260520_0002",
  "mode": "subgraph",
  "start_object_path": "equipment_domain.equipment.functions.equipment_fault_stat",
  "hops": 2,
  "nodes": [
    {
      "object_path": "equipment_domain.equipment.functions.equipment_fault_stat",
      "object_type": "Function",
      "name": "设备故障统计",
      "description": "按设备维度统计故障次数",
      "hop_distance": 0
    },
    {
      "object_path": "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule",
      "object_type": "Rule",
      "name": "故障次数统计规则",
      "description": "按设备统计故障数量",
      "hop_distance": 1
    }
  ],
  "edges": [
    {
      "source": "equipment_domain.equipment.functions.equipment_fault_stat",
      "relation_type": "HAS_RULE",
      "target": "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule"
    }
  ],
  "truncated": false
}
```

### 5.3 bindings 点查询接口

该接口用于根据一个或多个 TBox 对象路径，精准查询其对应的数据绑定信息或 SQL 定义。主要服务于 OAG 在生成查询计划前获取数据源、库、表、列和 SQL 信息。

#### Endpoint

```http
POST /v1/tbox/bindings/query
```

#### Request

```json
{
  "object_paths": [
    "equipment_domain.equipment.properties.equipment_id",
    "equipment_domain.equipment.properties.equipment_name",
    "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule"
  ]
}
```

#### Response

```json
{
  "query_id": "q_20260520_0003",
  "bindings": [
    {
      "object_path": "equipment_domain.equipment.properties.equipment_id",
      "object_type": "Property",
      "name": "设备ID",
      "data_type": "string",
      "binding": {
        "datasource": "iot_ds",
        "schema": "public",
        "database": "iot_db",
        "table": "dim_equipment",
        "column": "equipment_id"
      },
      "pk_column": true
    },
    {
      "object_path": "equipment_domain.equipment.properties.equipment_name",
      "object_type": "Property",
      "name": "设备名称",
      "data_type": "string",
      "binding": {
        "datasource": "iot_ds",
        "schema": "public",
        "database": "iot_db",
        "table": "dim_equipment",
        "column": "equipment_name"
      },
      "pk_column": false
    },
    {
      "object_path": "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count_rule",
      "object_type": "Rule",
      "name": "故障次数统计规则",
      "type": "sql",
      "defination": "select equipment_id, count(fault_id) as fault_count from fact_fault where status = 'active' group by equipment_id;"
    }
  ],
  "not_found": []
}
```

### 5.4 获取本体图节点类型接口

#### Endpoint

```http
GET /v1/tbox/graph/node-types
```

#### Response

```json
{
  "node_types": [
    {"type": "Domain", "description": "领域节点"},
    {"type": "Type", "description": "类型节点"},
    {"type": "Property", "description": "属性节点"},
    {"type": "Relationship", "description": "关系节点"},
    {"type": "Function", "description": "函数节点"},
    {"type": "Rule", "description": "Function 下的 SQL 规则节点"}
  ]
}
```

### 5.5 获取本体图边类型接口

#### Endpoint

```http
GET /v1/tbox/graph/edge-types
```

#### Response

```json
{
  "edge_types": [
    {"type": "HAS_TYPE", "source": "Domain", "target": "Type", "description": "领域包含类型"},
    {"type": "HAS_PROPERTY", "source": "Type", "target": "Property", "description": "类型包含属性"},
    {"type": "HAS_RELATIONSHIP", "source": "Type", "target": "Relationship", "description": "类型包含关系"},
    {"type": "HAS_FUNCTION", "source": "Type", "target": "Function", "description": "类型包含函数"},
    {"type": "HAS_RULE", "source": "Function", "target": "Rule", "description": "函数包含规则"},
    {"type": "LINK_TO", "source": "Relationship", "target": "Property", "description": "关系连接属性"},
    {"type": "USES_DIMENSION", "source": "Function", "target": "Property", "description": "函数使用维度属性"}
  ]
}
```

### 5.6 Schema Discovery 接口

#### Endpoint

```http
GET /v1/tbox/schema
```

#### Response

```json
{
  "timestamp": "2026-05-20T09:00:00.123456789Z",
  "domains": {},
  "code": "0",
  "message": "success"
}
```

---

## 6. 运行保障、部署与测试

### 6.1 运行监控指标

| 指标                     | 说明               |
| ---------------------- | ---------------- |
| full_sync_duration     | 全量同步耗时           |
| full_sync_domain_count | 全量同步 Domain 数量   |
| full_sync_type_count   | 全量同步 Type 数量     |
| kafka_consumer_lag     | Kafka 消费延迟       |
| event_process_qps      | 事件处理 QPS         |
| graph_write_latency    | 图数据库写入延迟         |
| tbox_index_latency     | TBox 索引写入延迟      |
| tbox_retrieve_p95      | TBox 检索接口 P95 延迟 |
| tbox_retrieve_p99      | TBox 检索接口 P99 延迟 |
| empty_result_rate      | 空结果比例            |

### 6.2 日志字段

```text
trace_id
query_id / event_id
timestamp
object_path
object_type
cost_ms
status
error_code
error_message
```

### 6.3 异常处理与恢复

| 失败类型         | 处理方式          |
| ------------ | ------------- |
| 全量接口调用失败     | 重试，超过阈值告警     |
| Kafka 消息格式错误 | 进入 DLQ        |
| 图写入失败        | 重试            |
| TBox 索引写入失败  | 记录失败状态，异步补偿重试 |
| API 查询超时     | 返回明确错误码       |

数据恢复优先级：

```text
本体管理系统 TBox 全量快照 + Kafka 增量事件 > 图数据库备份 > TBox 索引备份
```

### 6.4 部署组件

| 组件             | 部署方式      | 说明                     |
| -------------- | --------- | ---------------------- |
| oaas-api       | 多副本无状态部署  | 提供 TBox 检索 API         |
| oaas-full-sync | 独立部署或定时任务 | 调用本体管理系统全量接口           |
| oaas-consumer  | 多副本部署     | 消费 Kafka，写图和索引         |
| oaas-indexer   | 独立部署      | 执行 TBox 索引重建           |
| graph-db       | 集群或主从     | 存储 TBox 图数据            |
| vector-index   | 集群        | 存储 TBox 向量索引           |
| keyword-index  | 集群        | 存储 TBox 关键词索引          |
| metadata-db    | 主从        | 存储事件状态、checkpoint、任务状态 |
| kafka          | 集群        | TBox 增量事件通道            |

### 6.5 测试验证项

| 测试项             | 说明                                                                      |
| --------------- | ----------------------------------------------------------------------- |
| 全量同步            | 是否能完整解析 timestamp、domains、code、message                                  |
| Domain 解析       | 是否能正确解析 domains 下的领域对象                                                  |
| Type 解析         | 是否能正确解析 domain.types                                                    |
| Property 解析     | 是否能正确解析 type.properties 和 binding                                       |
| Relationship 解析 | 是否能正确解析 type.relationships 和 link_properties                            |
| Function 解析     | 是否能正确解析 type.functions                                                  |
| Rule 解析         | 是否能正确解析 function.rules 下的 type 和 defination                             |
| Kafka 增量同步      | payload 是否严格遵从全量接口结构                                                    |
| DELETE 事件       | 是否能根据 Kafka Message Key 和 payload 层级路径删除或失效对象                           |
| Top-K 检索        | 是否能召回正确的 TBox 对象                                                        |
| Hop 子图检索        | 是否能返回正确的 nodes 和 edges                                                  |
| bindings 点查询    | 是否能根据 object_path 返回正确的数据源、库、表、列和 SQL 定义                                |
| 图节点类型查询         | 是否能返回 Domain、Type、Property、Relationship、Function、Rule                   |
| 图边类型查询          | 是否能返回 HAS_TYPE、HAS_PROPERTY、HAS_RELATIONSHIP、HAS_FUNCTION、HAS_RULE 等边类型 |

---

## 7. 总结

本版本 OaaS 只处理 TBox，不处理 ABox。TBox 数据结构以本体管理系统全量接口为准，顶层包含：

```text
timestamp
domains
code
message
```

其中 `domains` 下包含 Domain、Type、Property、Relationship、Function、Rule 等语义对象。

Function 下不再包含 `measures`，改为包含 `rules`。Rule 用于存储 SQL 类型规则，核心字段为：

```text
name
description
type
defination
```

Kafka 增量事件保留事件 envelope，但 `payload` 内部结构与全量接口 Response 保持一致，即：

```text
payload.timestamp
payload.domains
payload.code
payload.message
```

系统基于该结构完成图存储、索引构建、Top-K 候选检索、Hop 子图检索、bindings 点查询、图节点类型查询和图边类型查询。
