# Ontology Service API 文档

> 基础地址: `http://localhost:8080` (Java) / `http://localhost:5001` (Python)

---

## 一、Java 后端 API (`:8080`)

### 1. 域管理 `POST /api/v1/domains`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/domains` | 创建域 |
| `POST` | `/api/v1/domains/{domainName}/versions` | 发布新版本 |
| `GET` | `/api/v1/domains/{domainName}/versions` | 列出所有版本 |
| `GET` | `/api/v1/domains/{domainName}/versions/{version}` | 获取指定版本 |
| `GET` | `/api/v1/domains/{domainName}/latest` | 获取最新版本 |

**创建域请求体:**
```json
{
  "domainName": "PlantGraph",
  "ddlSql": "CREATE PROPERTY GRAPH ...",
  "status": "draft",
  "createdBy": "admin"
}
```

---

### 2. 语义层 (TBOX) `POST /api/v1/semantic/{domain}/{version}`

#### 2.1 对象类型

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/{domain}/{version}/object-types` | 创建对象类型 |
| `GET` | `/{domain}/{version}/object-types` | 列出所有对象类型 |
| `GET` | `/{domain}/{version}/object-types/{labelName}` | 获取指定类型 |
| `GET` | `/{domain}/{version}/object-types/{labelName}/children` | 获取子类型 |

**创建对象类型请求体:**
```json
{
  "labelName": "Equipment",
  "parentLabel": "Asset",
  "displayName": "设备",
  "description": "工业设备",
  "aiContext": "aliases: 机器,装置"
}
```

#### 2.2 属性

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/{domain}/{version}/properties` | 创建属性 |
| `GET` | `/{domain}/{version}/object-types/{ownerLabel}/properties` | 列出类型的属性 |

**创建属性请求体:**
```json
{
  "propertyName": "temperature",
  "ownerLabel": "Equipment",
  "valueType": "DOUBLE",
  "columnName": "temp_col",
  "expressionSql": "",
  "isMeasure": false,
  "semanticRole": "metric",
  "semanticAliases": ["温度", "气温"],
  "hidden": false,
  "description": "设备温度"
}
```

#### 2.3 关系

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/{domain}/{version}/relationships` | 创建关系 |
| `GET` | `/{domain}/{version}/relationships` | 列出所有关系 |
| `GET` | `/{domain}/{version}/object-types/{sourceLabel}/outgoing-relationships` | 列出源类型的出边 |

**创建关系请求体:**
```json
{
  "labelName": "HAS_POINT",
  "sourceLabel": "Equipment",
  "targetLabel": "SCADAPoint",
  "sourceKey": "equipment_id",
  "targetKey": "point_id",
  "edgeTable": "edge_equipment_point",
  "cardinality": "one_to_many",
  "outgoingName": "points",
  "incomingName": "equipment"
}
```

---

### 3. TBOX/ABOX 映射 `POST /api/v1/abox-mappings/{domain}/{version}` ⭐ **新增**

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/{domain}/{version}` | 创建映射 |
| `GET` | `/{domain}/{version}` | 列出所有映射 |
| `GET` | `/{domain}/{version}/{className}` | 获取指定类映射 |
| `PUT` | `/{domain}/{version}/{className}` | 更新映射 |
| `DELETE` | `/{domain}/{version}/{className}` | 删除映射 |

**创建映射请求体:**
```json
{
  "className": "Equipment",
  "parentClass": "Asset",
  "mappingStrategy": "class_table",
  "objectSourceName": "doris_table_equipment",
  "sourceKind": "physical_table",
  "primaryKey": "equipment_id",
  "discriminatorColumn": "",
  "typeFilterSql": "",
  "propertyProjectionJson": "{\"temperature\": \"temp_col\"}",
  "viewSql": "",
  "materializationStrategy": "virtual",
  "aiContext": "设备数据来自MES系统"
}
```

---

### 4. 推理规则 `POST /api/v1/logic/{domain}/{version}`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/{domain}/{version}` | 创建规则 |
| `GET` | `/{domain}/{version}` | 列出规则（支持 logicKind/targetType 过滤） |
| `GET` | `/{domain}/{version}/{logicName}` | 获取指定规则 |
| `GET` | `/{domain}/{version}/{logicName}/dependencies` | 获取规则依赖 |
| `GET` | `/{domain}/{version}/topo-order` | 获取拓扑排序 |
| `POST` | `/{domain}/{version}/{logicName}/execute` | 执行规则 |
| `GET` | `/{domain}/{version}/{logicName}/explanation` | 获取规则解释 |
| `POST` | `/{domain}/{version}/{logicName}/explain` | 生成规则解释 |

---

### 5. Action 管理 `POST /api/v1/actions` ⭐ **完整补全**

#### 5.1 Action 定义 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/definitions/{domainName}/{version}` | 创建 Action 定义 |
| `GET` | `/definitions/{domainName}/{version}` | 列出 Action 定义 |
| `GET` | `/definitions/{domainName}/{version}/{actionName}` | 获取 Action 定义 |
| `PUT` | `/definitions/{domainName}/{version}/{actionName}` | 更新 Action 定义 |
| `DELETE` | `/definitions/{domainName}/{version}/{actionName}` | 删除 Action 定义 |

**创建 Action 请求体:**
```json
{
  "actionName": "CreateIncidentTicket",
  "toolName": "create_incident_ticket",
  "targetType": "AttackWindow",
  "inputSchemaJson": "{\"type\":\"object\",\"properties\":{\"severity\":{\"type\":\"string\"}}}",
  "outputSchemaJson": "{\"type\":\"object\",\"properties\":{\"incident_id\":{\"type\":\"string\"}}}",
  "preconditionSql": "SELECT status != 'Closed' AS precondition_met FROM attack_window WHERE id = {target_object_id}",
  "preconditionLogic": "AttackWindow.security_state",
  "externalPlatform": "FoundryLikePlatform",
  "externalActionRef": "workflow://incident/create",
  "invocationMode": "submit_request",
  "dryRunRequired": true,
  "aiContext": "创建事件工单，仅在攻击窗口未关闭时调用"
}
```

#### 5.2 Action 绑定

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/bindings/{domainName}/{version}` | 创建 Action 绑定 |
| `GET` | `/bindings/{domainName}/{version}` | 列出 Action 绑定 |
| `GET` | `/bindings/{domainName}/{version}/{actionName}` | 获取 Action 绑定 |
| `PUT` | `/bindings/{domainName}/{version}/{actionName}/{platformName}` | 更新绑定 |
| `DELETE` | `/bindings/{domainName}/{version}/{actionName}/{platformName}` | 删除绑定 |

**创建绑定请求体:**
```json
{
  "actionName": "CreateIncidentTicket",
  "platformName": "FoundryLikePlatform",
  "platformActionRef": "https://api.platform.com/actions/create",
  "dryRunRef": "https://api.platform.com/actions/preview",
  "resultRef": "https://api.platform.com/actions/result",
  "observabilityRef": "https://logs.platform.com/actions",
  "enabled": true
}
```

#### 5.3 Action 执行

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/tools/{domainName}/{version}` | 列出可用 tools |
| `POST` | `/dry-run` | Dry-run 校验 |
| `POST` | `/submit` | 提交执行 |
| `GET` | `/{actionId}/status` | 查询状态 |
| `POST` | `/{actionId}/cancel` | 取消执行 |
| `GET` | `/instances/{domainName}` | 列出执行实例 |

**Dry-run / Submit 请求体:**
```json
{
  "domainName": "PlantGraph",
  "version": "1.0.0",
  "actionName": "CreateIncidentTicket",
  "toolName": "create_incident_ticket",
  "targetType": "AttackWindow",
  "targetObjectId": "AW-001",
  "input": {"severity": "high", "description": "异常检测"},
  "dryRun": false,
  "requestedBy": "admin",
  "requestedByAgent": "llm-agent"
}
```

---

### 6. 查询 `POST /api/v1/query`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/semantic/{domainName}/{version}` | 语义查询 |
| `POST` | `/graph/{domainName}/{version}` | 图查询 |
| `POST` | `/logic/{domainName}/{version}` | 逻辑查询 |
| `POST` | `/explain/{domainName}/{version}` | 查询解释 |

---

### 7. Catalog `POST /api/v1/catalog`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/build/{domainName}/{version}` | 构建 Catalog |
| `POST` | `/refresh/{domainName}/{version}` | 刷新 Catalog |

---

## 二、Python 后端 API (`:5001`)

### 1. 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 服务健康状态 |

### 2. Grounding 语义接地

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/grounding/ground` | 单条自然语言接地 |
| `POST` | `/api/v1/grounding/batch-ground` | 批量接地 |
| `GET` | `/api/v1/grounding/entities/{domain_name}/{version}` | 列出语义实体 |

**Grounding 请求体:**
```json
{
  "domain_name": "PlantGraph",
  "version": "1.0.0",
  "query": "查询所有温度超过80度的设备",
  "context": {}
}
```

### 3. Embedding 向量

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/embedding/embed` | 文本向量化 |
| `POST` | `/api/v1/embedding/similarity` | 相似度计算 |

---

## 三、数据表总览

### TBOX (术语层) — 11 张表

| 表名 | 说明 |
|------|------|
| `ontology_domain` | 域定义与版本管理 |
| `ontology_object_type` | 对象类型/节点类别 |
| `ontology_object_abox_mapping` | **TBOX → ABOX 映射** |
| `ontology_property` | 属性定义 |
| `ontology_relationship` | 关系/边定义 |
| `ontology_logic` | 推理规则定义 |
| `ontology_logic_dependency` | 规则依赖关系 |
| `ontology_logic_execution_binding` | 规则执行绑定 |
| `ontology_logic_explanation` | 规则解释模板 |
| `ontology_action` | Action 定义 |
| `ontology_action_binding` | Action 外部平台绑定 |

### ABOX (实例层) — 4 张表

| 表名 | 说明 |
|------|------|
| `semantic_fact` | 推理产生的事实 |
| `semantic_logic_run` | 规则执行记录 |
| `semantic_action_instance` | Action 执行实例 |
| `semantic_query_log` | 查询日志 |
