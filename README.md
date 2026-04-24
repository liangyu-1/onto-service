# Ontology Service - 本体存储查询引擎

基于 **GoogleSQL / Semantic SQL** + **Apache Doris (ABOX)** + **Neo4j (TBOX)** 的工业场景本体存储与查询引擎原型（`neo4j-test` 分支）。

## 架构设计（neo4j-test）

```
┌─────────────────────────────────────────────────────────────┐
│                        LLM Agent                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Ontology Service                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   Semantic   │ │    Query     │ │    Action    │        │
│  │    Layer     │ │   Adapter    │ │   Gateway    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐                          │
│  │    Logic     │ │   Catalog    │                          │
│  │   Registry   │ │   Builder    │                          │
│  └──────────────┘ └──────────────┘                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│         Neo4j (TBOX) + Apache Doris (ABOX)                    │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

- **Java**: Spring Boot 3.2 + MyBatis Plus + JDBC
- **Python**: FastAPI + Sentence-Transformers + OpenAI
- **C++**: GoogleSQL/ZetaSQL 扩展 (Property Graph)
- **TBOX**: Neo4j (Cypher / Bolt)
- **ABOX**: Apache Doris (OLAP / MySQL protocol)
- **语法**: GoogleSQL / Semantic SQL（MVP：受限语义查询结构体 → Doris SQL）

## 快速开始

### 1. 克隆仓库

```bash
git clone --recursive git@github.com:liangyu-1/onto-service.git
cd onto-service
```

### 2. Docker Compose 启动

```bash
docker-compose up -d
```

服务启动后：
- Java API: http://localhost:8080
- Python API: http://localhost:5000
- Doris FE: http://localhost:8030
- Neo4j Browser: http://localhost:7474

### 3. 初始化数据库

```bash
# 先构建 Java 包（compose 会挂载 target 目录运行 jar）
cd onto-service-java
mvn -DskipTests package
cd ..

# 初始化 Doris ABOX schema + HAI demo 数据
bash scripts/init_doris.sh

# 初始化 Neo4j TBOX demo 图（PlantGraph/1.0.0 + HAI 映射）
bash scripts/seed_neo4j.sh
```

### 4. 打开前端控制台

- 打开 `http://localhost:8080/`
- 进入「查询测试」Tab，可执行语义查询（Neo4j TBOX → Doris SQL）。

## API 文档

### Domain 管理

```bash
# 创建本体域
POST /api/v1/domains
{
  "domainName": "PlantGraph",
  "ddlSql": "CREATE PROPERTY GRAPH PlantGraph ...",
  "createdBy": "admin"
}

# 发布新版本
POST /api/v1/domains/PlantGraph/versions
{
  "ddlSql": "...",
  "createdBy": "admin"
}
```

### Semantic Layer

```bash
# 创建对象类型
POST /api/v1/semantic/PlantGraph/1.0.0/object-types
{
  "labelName": "ICSProcess",
  "displayName": "工艺过程",
  "description": "工业控制过程"
}

# 创建属性
POST /api/v1/semantic/PlantGraph/1.0.0/properties
{
  "ownerLabel": "ICSProcess",
  "propertyName": "security_state",
  "valueType": "STRING",
  "semanticRole": "state"
}

# 创建关系
POST /api/v1/semantic/PlantGraph/1.0.0/relationships
{
  "labelName": "HAS_POINT",
  "sourceLabel": "ICSProcess",
  "targetLabel": "SCADAPoint",
  "outgoingName": "has_point",
  "cardinality": "one_to_many"
}
```

### 查询

```bash
# 语义查询
POST /api/v1/query/semantic/PlantGraph/1.0.0
{
  "intent": "select",
  "targetType": "ICSProcess",
  "selectProperties": ["process_id", "security_state"],
  "filters": {"process_id": "P1"},
  "limit": 100
}

# 图查询
POST /api/v1/query/graph/PlantGraph/1.0.0
{
  "matchPattern": "(p:ICSProcess)-[:HAS_POINT]->(pt:SCADAPoint)",
  "whereClause": "p.process_id = 'P1'",
  "returnExpressions": ["p.process_id", "pt.point_tag"]
}

# 逻辑查询 (推理事实)
POST /api/v1/query/logic/PlantGraph/1.0.0
{
  "logicName": "ICSProcess.security_state",
  "targetType": "ICSProcess",
  "targetObjectId": "P1"
}
```

### Logic Registry

```bash
# 创建规则
POST /api/v1/logic/PlantGraph/1.0.0
{
  "logicName": "ICSProcess.security_state",
  "targetType": "ICSProcess",
  "targetProperty": "security_state",
  "logicKind": "semantic_property",
  "implementationType": "sql",
  "expressionSql": "SELECT ...",
  "deterministic": true
}

# 执行规则
POST /api/v1/logic/PlantGraph/1.0.0/ICSProcess.security_state/execute

# 获取依赖拓扑排序
GET /api/v1/logic/PlantGraph/1.0.0/topo-order
```

### Action Gateway

```bash
# 列出可用工具
GET /api/v1/actions/tools/PlantGraph/1.0.0

# Dry-run
POST /api/v1/actions/dry-run
{
  "domainName": "PlantGraph",
  "version": "1.0.0",
  "actionName": "CreateIncidentTicket",
  "targetType": "AttackWindow",
  "targetObjectId": "AW001",
  "input": {"severity": "high"},
  "requestedBy": "user001"
}

# 提交动作
POST /api/v1/actions/submit
{
  "domainName": "PlantGraph",
  "version": "1.0.0",
  "actionName": "CreateIncidentTicket",
  "targetObjectId": "AW001",
  "dryRun": false,
  "requestedBy": "user001"
}
```

## 项目结构

```
onto-service/
├── onto-service-java/          # Java Spring Boot 服务
│   ├── src/main/java/com/onto/service/
│   │   ├── api/                # REST Controllers
│   │   ├── catalog/            # GoogleSQL Catalog 集成
│   │   ├── config/             # 配置类
│   │   ├── entity/             # 实体类 (14个)
│   │   ├── exception/          # 异常处理
│   │   ├── logic/              # Logic Registry
│   │   ├── mapper/             # MyBatis Mappers
│   │   ├── query/              # Query Adapter
│   │   ├── semantic/           # Semantic Layer
│   │   └── action/             # Action Gateway
│   └── src/test/               # 单元测试
├── onto-service-python/        # Python FastAPI 服务
│   └── onto_service/
│       ├── embedding/          # 语义嵌入
│       ├── grounding/          # LLM Grounding
│       └── llm/                # LLM 客户端
├── onto-service-cpp/           # C++ GoogleSQL 扩展
│   ├── include/onto/service/   # 头文件
│   └── src/                    # 实现
├── sql/                        # Doris DDL
│   ├── 01_tbox_schema.sql      # TBOX 11张表
│   └── 02_abox_schema.sql      # ABOX 4张表
└── googlesql/                  # GoogleSQL 子模块 (git submodule)
```

## 核心概念

### TBOX (Terminology Box)
- **Ontology Domain**: 本体域定义和版本管理
- **Object Type**: 业务对象类型 (如 ICSProcess, SCADAPoint)
- **Property**: 属性定义 (语义属性到物理列的映射)
- **Relationship**: 关系定义 (源类型、目标类型、基数)
- **ABOX Mapping**: 语义类型到 Doris 表/视图的映射策略

### ABOX (Assertion Box)
- **Semantic Fact**: 推理事实 (Derived Facts)
- **Logic Run**: 规则运行记录
- **Action Instance**: 动作执行实例

### Logic Registry
- **Logic**: 规则定义 (SQL/UDF/Python/NLP/External)
- **Dependency**: 规则依赖关系
- **Execution Binding**: 外部平台任务绑定
- **Explanation**: 解释模板 (多语言)

## License

Apache License 2.0
