# 本体管理平台openApi文档

**接口前缀**：`/ontology/api/open`
**基础地址**：示例 `http://172.16.21.216:8888`

---

## 通用响应与错误处理

所有接口均使用相同的外层响应结构：

| 字段        | 类型     | 说明                                          |
| --------- | ------ | ------------------------------------------- |
| code      | int    | 枚举：`200`（成功）、`其他`（失败）                       |
| message   | string | 成功为 `"success"`，失败为具体错误描述                   |
| timestamp | long   | 响应时间戳（毫秒 Unix）                              |
| —         | —      | 业务数据，字段名按接口不同（`domains` 或 `datasource`），见下文 |

---

## 1. 获取全部已发布域数据

```
GET /ontology/api/open/domains
```

返回所有已发布域下的完整本体模型（域 → 类型 → 属性 → 绑定 → 关系 → 映射 → 规则）。

### 响应结构

```
{
  "code": 200,
  "message": "success",
  "timestamp": 1780390228853,
  "domains": {                   // map<long, Domain>
    "{domainId}": {
      "name": "string",          // 域编码
      "displayName": "string",   // 域显示名称
      "description": "string",   // 域描述
      "types": {                 // map<long, Type> 该域下的类型
        "{typeId}": {
          "name": "string",          // 类型编码
          "displayName": "string",   // 类型显示名称
          "description": "string",   // 类型描述
          "displayProperty": "string|null",  // 作为展示名称的属性名
          "properties": {            // map<long, Property> 该类型的属性
            "{propertyId}": {
              "name": "string",          // 属性名
              "type": "string",          // 枚举：STRING | INTEGER | DECIMAL | DATE | BOOLEAN | TEXT | TIMESTAMP
              "displayName": "string",   // 属性显示名称
              "description": "string",   // 属性描述
              "pkColumn": "boolean",     // 是否主键
              "binding": "object|null"   // 字段绑定，无则为 null
            }
          },
          "relationships": {        // map<long, Relation> 该类型参与的关系
            "{relationId}": {
              "name": "string",          // 关系名
              "displayName": "string",   // 关系显示名称
              "description": "string",   // 关系描述
              "cardinality": "string",   // 枚举：one2one | one2many | many2one | many2many
              "type": "string",          // 枚举：left_join | inner_join | right_join | full_join
              "linkProperties": "array"  // [{"srcDomainId.srcObjectId.srcPropertyId": "tgtDomainId.tgtObjectId.tgtPropertyId"}, ...]
            }
          },
          "functions": "object|null"  // 规则集，无则为 null
        }
      }
    }
  }
}
```

### binding （属性中的内嵌类型）

| 字段         | 类型           | 说明       |
| ---------- | ------------ | -------- |
| datasource | long         | 数据源 ID   |
| schema     | string\|null | Schema 名 |
| database   | string       | 数据库名     |
| table      | string       | 表名       |
| column     | string       | 字段名      |

### functions （functions 非 null 时）

| 字段    | 类型            | 说明            |
| ----- | ------------- | ------------- |
| rules | map\<long, \> | 规则集，key=规则 ID |

### rules.{ruleId}

| 字段          | 类型           | 说明                            |
| ----------- | ------------ | ----------------------------- |
| name        | string       | 规则名                           |
| displayName | string       | 规则显示名称                        |
| description | string       | 规则描述                          |
| type        | string       | 逻辑类型，枚举：`SQL` \| `EXPRESSION` |
| definition  | string\|null | 规则定义内容（SQL 或表达式）              |

### 示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": 1780390228853,
  "domains": {
    "1": {
      "name": "user_domain",
      "displayName": "用户域",
      "description": "用户相关数据",
      "types": {
        "2": {
          "name": "user_info",
          "displayName": "用户信息",
          "description": "用户基本信息",
          "displayProperty": "user_name",
          "properties": {
            "3": {
              "name": "user_id",
              "type": "INTEGER",
              "displayName": "用户ID",
              "description": null,
              "pkColumn": true,
              "binding": {
                "datasource": 10,
                "schema": null,
                "database": "user_db",
                "table": "t_user",
                "column": "id"
              }
            }
          },
          "relationships": {
            "5": {
              "name": "user_order",
              "displayName": "用户订单",
              "description": "用户与订单的一对多关系",
              "cardinality": "one2many",
              "type": "left_join",
              "linkProperties": [
                {"1.2.3": "2.6.8"}
              ]
            }
          },
          "functions": {
            "rules": {
              "7": {
                "name": "active_users",
                "displayName": "活跃用户过滤",
                "description": "过滤最近活跃用户",
                "type": "SQL",
                "definition": "SELECT * FROM t_user WHERE last_login > DATE_SUB(NOW(), INTERVAL 30 DAY)"
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 2. 获取指定已发布域数据

```
GET /ontology/api/open/domains/{domainId}
```

### 路径参数

| 参数       | 类型   | 必填  | 说明   |
| -------- | ---- | --- | ---- |
| domainId | long | 是   | 域 ID |

### 响应

同接口 1，`domains` 仅包含指定 domainId 的域。域不存在时 `domains` 为 `{}`。

---

## 3. 获取指定数据源详细信息

```
GET /ontology/api/open/datasources/{datasourceId}
```

### 路径参数

| 参数           | 类型   | 必填  | 说明     |
| ------------ | ---- | --- | ------ |
| datasourceId | long | 是   | 数据源 ID |

### 响应结构

```
{
  "code": 200,
  "message": "success",
  "timestamp": 1780390228853,
  "datasource": {
    "id": "long",                    // 数据源 ID
    "tenantId": "long",              // 租户 ID
    "datasourceName": "string",      // 数据源名称
    "datasourceType": "string",      // 枚举：mysql | oracle | postgresql | sqlserver | kingbasees | dameng | doris
    "host": "string",                // 主机地址
    "port": "int",                   // 端口号
    "databaseName": "string",        // 数据库名称
    "databaseSchema": "string",      // Schema（无则为空串）
    "databaseVersion": "string",     // 版本，如 8.0、19c
    "connectionUrl": "string|null",  // 连接 URL，HOST_PORT 模式为 null
    "connectionMode": "string",      // 枚举：URL | HOST_PORT
    "username": "string",            // 用户名
    "password": "string",            // 密码（加密）
    "description": "string"          // 描述
  }
}
```

---

## 4. MQ 连接信息

| 配置项       | 值               |
| --------- | --------------- |
| IP        | 172.16.21.72    |
| Port      | 9092            |
| 队列（Topic） | ontology_events |
