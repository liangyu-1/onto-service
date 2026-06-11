# OaaS 本体语义检索服务 Helm Chart

OaaS (Ontology as a Service) 本体语义检索服务的 Kubernetes Helm Chart，包含 Java 检索服务、Python Embedding 服务、Neo4j 图数据库和 Kafka 消息队列。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         K8s Cluster                              │
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │ Java Service │◄────►│ Neo4j        │      │ Kafka        │   │
│  │ (检索 API)   │      │ (图数据库)    │      │ (消息队列)    │   │
│  │ 端口: 8080   │      │ Bolt: 7687   │      │ 端口: 9092   │   │
│  └──────┬───────┘      └──────────────┘      └──────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ Python Svc   │                                               │
│  │ (Embedding)  │  模型: bge-m3 (2.1GB, COPY 进镜像)             │
│  │ 端口: 5001   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 组件说明

| 组件 | 镜像 | 功能 | 资源限制 |
|------|------|------|----------|
| Java 服务 | `onto-service-java:latest` | TBox/ABox 检索 API、Kafka 消费 | 2CPU / 2Gi |
| Python 服务 | `onto-service-python:latest` | Embedding 生成、语义检索 | 2CPU / 4Gi |
| Neo4j | `neo4j:5.22-community` | 本体图存储 | 1CPU / 2Gi |
| Kafka | `bitnami/kafka:3.7.0` | 本体变更事件队列 | 1CPU / 2Gi |

## 快速开始

### 前置条件

- Kubernetes 1.24+
- Helm 3.12+
- Docker (构建镜像)

### 1. 构建镜像

```bash
# Java 服务
cd onto-service-java
mvn clean package -DskipTests
docker build -t onto-service-java:latest .

# Python 服务（模型已 COPY 进镜像，无需运行时下载）
cd onto-service-python
docker build -f Dockerfile.python -t onto-service-python:latest .
```

### 2. 安装 Chart

```bash
# 添加依赖仓库
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 安装依赖
cd charts/onto-service
helm dependency build

# 安装到集群
helm install onto-service . \
  --namespace onto-service \
  --create-namespace \
  --set java.image.repository=your-registry/onto-service-java \
  --set java.image.tag=v1.0.0 \
  --set python.image.repository=your-registry/onto-service-python \
  --set python.image.tag=v1.0.0
```

### 3. 验证安装

```bash
# 查看 Pod 状态
kubectl get pods -n onto-service

# 查看服务
kubectl get svc -n onto-service

# 测试 Java 服务健康检查
curl http://onto-service-java:8080/actuator/health

# 测试 Python 服务健康检查
curl http://onto-service-python:5001/health
```

### 4. 创建 Kafka Topics

Chart 中禁用了自动 provisioning（避免 helm install 超时），部署后需手动创建 topics：

```bash
# 进入 Kafka pod
kubectl exec -it -n onto-service $(kubectl get pod -n onto-service -l app.kubernetes.io/name=kafka -o jsonpath='{.items[0].metadata.name}') -- bash

# 创建 topics
kafka-topics.sh --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic ontology_events \
  --partitions 3 \
  --replication-factor 1

kafka-topics.sh --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic ontology-dlq \
  --partitions 1 \
  --replication-factor 1

# 验证
kafka-topics.sh --bootstrap-server localhost:9092 --list
```

> 或者依赖 Kafka 的 `auto.create.topics.enable=true`，首次发送消息时自动创建 topic（ partitions 默认为 1）。

## 配置参数

### Java 服务

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `java.enabled` | `true` | 是否启用 Java 服务 |
| `java.replicaCount` | `2` | 副本数 |
| `java.image.repository` | `onto-service-java` | 镜像仓库 |
| `java.image.tag` | `latest` | 镜像标签 |
| `java.resources.limits.cpu` | `2000m` | CPU 限制 |
| `java.resources.limits.memory` | `2Gi` | 内存限制 |
| `java.autoscaling.enabled` | `true` | 是否启用 HPA |
| `java.autoscaling.minReplicas` | `2` | 最小副本数 |
| `java.autoscaling.maxReplicas` | `5` | 最大副本数 |
| `java.config.neo4j.uri` | `bolt://neo4j:7687` | Neo4j 连接地址 |
| `java.config.kafka.bootstrapServers` | `kafka:9092` | Kafka 地址 |
| `java.env.PYTHON_SERVICE_URL` | `http://onto-service-python:5001` | Python 服务地址 |

### Python 服务

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `python.enabled` | `true` | 是否启用 Python 服务 |
| `python.replicaCount` | `1` | 副本数（模型加载内存大，建议单副本） |
| `python.image.repository` | `onto-service-python` | 镜像仓库 |
| `python.image.tag` | `latest` | 镜像标签 |
| `python.resources.limits.cpu` | `2000m` | CPU 限制 |
| `python.resources.limits.memory` | `4Gi` | 内存限制（模型加载需要） |
| `python.env.TRANSFORMERS_OFFLINE` | `1` | 离线模式，禁止下载模型 |
| `python.env.HF_HOME` | `/app/models` | 模型文件路径 |

### Neo4j

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `neo4j.enabled` | `true` | 是否启用 Neo4j |
| `neo4j.neo4j.password` | `neo4jpass` | 管理员密码 |
| `neo4j.volumes.data.dynamic.requests.storage` | `10Gi` | 数据存储大小 |

### Kafka

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `kafka.enabled` | `true` | 是否启用 Kafka |
| `kafka.replicaCount` | `1` | 副本数 |
| `kafka.persistence.size` | `10Gi` | 持久化存储大小 |
| `kafka.topics[0].name` | `ontology_events` | 本体事件 Topic |
| `kafka.topics[1].name` | `ontology-dlq` | 死信队列 Topic |

## 自定义配置示例

```yaml
# custom-values.yaml
java:
  replicaCount: 3
  image:
    repository: registry.example.com/onto-service-java
    tag: v2.1.0
  autoscaling:
    enabled: true
    maxReplicas: 10
  config:
    neo4j:
      uri: "bolt://external-neo4j:7687"
      password: "secure-password"
    kafka:
      bootstrapServers: "external-kafka:9092"

python:
  image:
    repository: registry.example.com/onto-service-python
    tag: v2.1.0
  resources:
    limits:
      memory: 8Gi

neo4j:
  enabled: false  # 使用外部 Neo4j

kafka:
  enabled: false  # 使用外部 Kafka
```

安装时指定自定义配置：

```bash
helm install onto-service . -f custom-values.yaml
```

## 模型文件说明

Python Embedding 服务使用 `bge-m3` 模型（2.1GB）。为避免容器启动时从 HuggingFace 下载（网络带宽限制），模型文件已通过以下方式处理：

1. **本地缓存**: `~/.cache/huggingface/hub/models--BAAI--bge-m3/` (4.3GB，含符号链接)
2. **解引用复制**: `cp -L` 复制到 `onto-service-python/models/bge-m3/` (2.1GB)
3. **Docker COPY**: `Dockerfile.python` 中 `COPY models/ /app/models/`
4. **离线加载**: 设置 `TRANSFORMERS_OFFLINE=1` 和 `HF_HOME=/app/models`

## 升级与回滚

```bash
# 升级
helm upgrade onto-service . --namespace onto-service

# 回滚
helm rollback onto-service 1 --namespace onto-service
```

## 卸载

```bash
helm uninstall onto-service --namespace onto-service
```

> ⚠️ 卸载时 Neo4j 和 Kafka 的 PVC 不会被自动删除，如需清理数据请手动删除。
