# OaaS 本体语义检索服务 - Kafka 增量事件消费联调测试报告

**日期**: 2026-06-04

---

## 1. 环境

| 组件 | 地址 | 状态 |
|------|------|------|
| OaaS Java 服务 | localhost:8080 | ✅ |
| Kafka | 172.16.21.72:9092, topic `ontology_events` | ✅ 46 条消息 |
| Neo4j | localhost:7687 (5.22) | ✅ |
| 本体管理平台 API | http://172.16.21.216:8888 | ✅ |
| Embedding 服务 | localhost:5000 | ❌ 403 |

---

## 2. 本次核心变更：Measure → Rule 模型重构

本体管理平台实际格式为 `functions.rules`，与设计文档对齐，全面替换旧版 Measure 模型：

- `MeasureDef` → `RuleDef`（字段：name, displayName, description, type, definition）
- `EventType.MEASURE_UPSERT` → `RULE_UPSERT`
- `TBoxObjectType.MEASURE` → `RULE`
- Neo4j 节点标签 `:Measure` → `:Rule`，关系 `HAS_MEASURE` → `HAS_RULE`
- `FunctionDef.measures` → `FunctionDef.rules`

---

## 3. 问题修复记录

| # | 问题 | 现象 | 修复 |
|---|------|------|------|
| 1 | Topic 名称 | 消费不到消息 | `ontology-events` → `ontology_events` |
| 2 | Jackson 字段映射 | 驼峰/snake_case 不匹配 | `@JsonAlias` + `ACCEPT_CASE_INSENSITIVE_ENUMS` |
| 3 | `@JsonAnySetter` | domain 为 null | 改用标准 `@JsonProperty` |
| 4 | `Map.ofEntries()` NPE | 字段为 null 时崩溃 | `HashMap<>()` |
| 5 | DELETE 参数越界 | `ArrayIndexOutOfBoundsException` | `args[8]` → `args[6]` |
| 6 | Doris 依赖启动失败 | 无数据库时启动失败 | 排除 `DataSourceAutoConfiguration`，`@ConditionalOnBean` |
| 7 | `.type()` 编译错误 | Dto 字段名为 `ruleType` | `.type()` → `.ruleType()` |
| 8 | `findByObjectPath` 缺失 | 未实现抽象方法 | 添加实现（含 `findRuleByPath`） |
| 9 | Bindings notFound | ruleKey(ID) ≠ name | 改用 `findByObjectPath` 直接查找 |

---

## 4. Kafka 消费验证

消费组：`oaas-consumer-group-rule-test-v2`（全新组，从头消费）

| 事件类型 | 数量 | 结果 |
|---------|------|------|
| TYPE_UPSERT | 22 | ✅ |
| DELETE | 11 | ✅ |
| DOMAIN_UPSERT | 5 | ✅ |
| RELATIONSHIP_UPSERT | 4 | ✅ |
| FUNCTION_UPSERT | 3 | ✅ |
| FULL_SYNC_REQUIRED | 1 | ✅ |
| **总计** | **46** | **✅ 0 失败** |

---

## 5. Neo4j 数据验证

```cypher
MATCH (n) RETURN labels(n)[0], count(n)
```

| 标签 | 数量 |
|------|------|
| TBoxIndex | 172 |
| Property | 98 |
| Relationship | 30 |
| Type | 28 |
| Domain | 9 |
| Function | 3 |
| **Rule** | **2** |

Rule 节点验证：
```cypher
MATCH (r:Rule) RETURN r.name, r.type, r.definition
-- "exist_metrics", "SQL", "select count(1) from expos_metrics.t_metrics"
-- "推送规则名称", "SQL", "select ...metrics_name from..."
```

HAS_RULE 关系验证：
```cypher
MATCH (f:Function)-[:HAS_RULE]->(r:Rule) RETURN count(*)
-- 2
```

---

## 6. API 验证

### 6.1 Bindings API（Rule 查询）

```bash
POST /v1/tbox/bindings/query
{"objectPaths": ["...functions.rules.rules.2062352789650472962"]}
```

```json
{
  "bindings": [{
    "objectType": "RULE",
    "name": "exist_metrics",
    "ruleType": "SQL",
    "definition": "select count(1) from expos_metrics.t_metrics"
  }],
  "notFound": []
}
```
✅ **通过**

### 6.2 全量同步

```bash
POST /v1/tbox/sync/full
```

```json
{"status": "SUCCESS", "domainCount": 5, "typeCount": 20, "propertyCount": 79}
```
✅ **通过**

### 6.3 其他接口

| 接口 | 状态 | 说明 |
|------|------|------|
| `/actuator/health` | ✅ | Neo4j UP |
| `/v1/tbox/schema` | ⚠️ | typeCount=0（findAllDomains 未加载关联） |
| `/v1/tbox/retrieve` | ⚠️ | embedding 服务不可用 |

---

## 7. 修改文件清单

**新增**: `RuleDef.java`, `RuleUpsertHandler.java`
**删除**: `MeasureDef.java`, `MeasureUpsertHandler.java`
**修改**: `FunctionDef.java`, `EventType.java`, `TBoxObjectType.java`, `TBoxIndexDocument.java`, `TBoxGraphRepository.java`, `Neo4jTBoxGraphRepository.java`, `InMemoryTBoxGraphRepository.java`, `TBoxIndexBuilder.java`, `TBoxBindingsController.java`, `SchemaDiscoveryController.java`, `SyncAgent.java`, `EventAgent.java`, `GraphAgent.java`, `OntologyMgmtSnapshotAdapter.java`, `ExternalSnapshotAdapter.java`, `ObjectPathUtil.java`, `application.yml`

---

## 8. 结论

✅ Kafka 消费链路正常（46/46，0 失败）  
✅ Rule 模型重构完成，数据写入和查询正常  
✅ 编译零错误，应用启动正常
