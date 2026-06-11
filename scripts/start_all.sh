#!/bin/bash
#===============================================================================
# Ontology Service 一键启动脚本
# 支持：基础设施启动、Java 服务启动、Python 服务启动、全链路健康检查
#===============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 默认配置
JAVA_PORT=${SERVER_PORT:-8080}
PYTHON_PORT=${PYTHON_PORT:-5001}
NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-neo4jpass}
KAFKA_BOOTSTRAP=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}
PYTHON_SERVICE_URL=${PYTHON_SERVICE_URL:-http://localhost:5000}

# 模式选择
MODE="${1:-all}"  # all | infra | java | python | dev

#===============================================================================
# 工具函数
#===============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i :"$port" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 等待服务就绪
wait_for_service() {
    local name=$1
    local url=$2
    local max_wait=${3:-60}
    local interval=${4:-2}
    
    log_info "Waiting for $name at $url ..."
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "200\|401\|403"; then
            log_ok "$name is ready"
            return 0
        fi
        sleep $interval
        waited=$((waited + interval))
        echo -n "."
    done
    echo
    log_err "$name failed to start within ${max_wait}s"
    return 1
}

# 等待端口监听
wait_for_port() {
    local name=$1
    local port=$2
    local max_wait=${3:-60}
    local interval=${4:-2}
    
    log_info "Waiting for $name on port $port ..."
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if check_port "$port"; then
            log_ok "$name is listening on port $port"
            return 0
        fi
        sleep $interval
        waited=$((waited + interval))
        echo -n "."
    done
    echo
    log_err "$name failed to start on port $port within ${max_wait}s"
    return 1
}

#===============================================================================
# 基础设施启动
#===============================================================================

start_infra() {
    log_info "Starting infrastructure services (Neo4j + Kafka)..."
    
    # 检查 Docker 是否运行
    if ! docker info >/dev/null 2>&1; then
        log_err "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # 检查是否已有 Neo4j 容器在运行（可能是之前实验的）
    local existing_neo4j=$(docker ps --filter "ancestor=neo4j" --format "{{.Names}}" | head -1)
    if [ -n "$existing_neo4j" ] && [ "$existing_neo4j" != "onto-neo4j" ]; then
        log_warn "Found existing Neo4j container: $existing_neo4j"
        log_warn "Port 7474/7687 may be occupied. Stopping existing container..."
        docker stop "$existing_neo4j" 2>/dev/null || true
        sleep 3
    fi
    
    # 启动 Neo4j 和 Kafka（不启动 Doris，开发环境用内存模式）
    docker compose up -d neo4j kafka
    
    # 等待 Neo4j 就绪
    wait_for_port "Neo4j" 7687 60
    
    # 等待 Kafka 就绪
    wait_for_port "Kafka" 9092 60
    
    # 创建 Kafka topic（如果不存在）
    log_info "Creating Kafka topics..."
    docker exec onto-kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic ontology-events --if-not-exists --partitions 1 --replication-factor 1 2>/dev/null || true
    docker exec onto-kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic ontology-dlq --if-not-exists --partitions 1 --replication-factor 1 2>/dev/null || true
    
    log_ok "Infrastructure services started"
}

#===============================================================================
# Java 服务启动
#===============================================================================

start_java() {
    log_info "Starting Java service..."
    
    # 检查端口占用
    if check_port "$JAVA_PORT"; then
        log_warn "Port $JAVA_PORT is already in use. Killing existing process..."
        kill $(lsof -t -i :"$JAVA_PORT") 2>/dev/null || true
        sleep 2
    fi
    
    # 编译
    log_info "Building Java service..."
    cd "$PROJECT_ROOT/onto-service-java"
    mvn compile -q
    
    # 启动（后台）
    log_info "Starting Java service on port $JAVA_PORT..."
    log_info "(This may take 60-120 seconds for first startup)"
    cd "$PROJECT_ROOT/onto-service-java"
    nohup mvn spring-boot:run \
        -Dspring-boot.run.jvmArguments="-Dserver.port=$JAVA_PORT" \
        -Dspring.kafka.bootstrap-servers="$KAFKA_BOOTSTRAP" \
        -Dspring.neo4j.uri="$NEO4J_URI" \
        -Dspring.neo4j.authentication.username="$NEO4J_USER" \
        -Dspring.neo4j.authentication.password="$NEO4J_PASSWORD" \
        -Donto.grounding.python-service-url="$PYTHON_SERVICE_URL" \
        > "$PROJECT_ROOT/logs/java-service.log" 2>&1 &
    
    local java_pid=$!
    log_info "Java process started with PID: $java_pid"
    
    # 等待就绪（Maven 首次启动可能需要 2 分钟）
    wait_for_service "Java Service" "http://localhost:$JAVA_PORT/actuator/health" 180
    
    log_ok "Java service started at http://localhost:$JAVA_PORT"
}

#===============================================================================
# Python 服务启动
#===============================================================================

start_python() {
    log_info "Starting Python service..."
    
    # 检查 Python 环境
    if ! command -v python3 >/dev/null 2>&1; then
        log_err "python3 not found. Please install Python 3."
        exit 1
    fi
    
    # 检查端口占用
    if check_port "$PYTHON_PORT"; then
        log_warn "Port $PYTHON_PORT is already in use. Killing existing process..."
        kill $(lsof -t -i :"$PYTHON_PORT") 2>/dev/null || true
        sleep 2
    fi
    
    cd "$PROJECT_ROOT/onto-service-python"
    
    # 检查虚拟环境
    if [ ! -d "$PROJECT_ROOT/onto-service-python/.venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # 激活虚拟环境
    source .venv/bin/activate
    
    # 安装依赖
    log_info "Installing Python dependencies..."
    pip install -q -r requirements.txt 2>/dev/null || {
        log_warn "Some dependencies failed to install, continuing..."
    }
    
    # 启动
    log_info "Starting Python service on port $PYTHON_PORT..."
    nohup uvicorn onto_service.main:app \
        --host 0.0.0.0 \
        --port "$PYTHON_PORT" \
        > "$PROJECT_ROOT/logs/python-service.log" 2>&1 &
    
    local py_pid=$!
    log_info "Python process started with PID: $py_pid"
    
    # 等待就绪
    wait_for_service "Python Service" "http://localhost:$PYTHON_PORT/health" 60
    
    log_ok "Python service started at http://localhost:$PYTHON_PORT"
}

#===============================================================================
# 开发模式启动（内存模式，不依赖外部数据库）
#===============================================================================

start_dev() {
    log_info "Starting in DEVELOPMENT mode (in-memory, no external DB required)..."
    
    # 检查端口占用
    if check_port "$JAVA_PORT"; then
        log_warn "Port $JAVA_PORT is already in use. Killing existing process..."
        kill $(lsof -t -i :"$JAVA_PORT") 2>/dev/null || true
        sleep 2
    fi
    if check_port "$PYTHON_PORT"; then
        log_warn "Port $PYTHON_PORT is already in use. Killing existing process..."
        kill $(lsof -t -i :"$PYTHON_PORT") 2>/dev/null || true
        sleep 2
    fi
    
    # 启动 Python 服务
    cd "$PROJECT_ROOT/onto-service-python"
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    log_info "Starting Python service on port $PYTHON_PORT..."
    nohup uvicorn onto_service.main:app \
        --host 0.0.0.0 \
        --port "$PYTHON_PORT" \
        > "$PROJECT_ROOT/logs/python-service.log" 2>&1 &
    
    wait_for_service "Python Service" "http://localhost:$PYTHON_PORT/health" 60
    
    # 启动 Java 服务（内存模式）
    log_info "Building Java service..."
    cd "$PROJECT_ROOT/onto-service-java"
    mvn compile -q
    
    log_info "Starting Java service on port $JAVA_PORT (in-memory mode)..."
    nohup mvn spring-boot:run \
        -Dspring-boot.run.jvmArguments="-Dserver.port=$JAVA_PORT" \
        -Dspring.profiles.active=dev \
        -Donto.grounding.python-service-url="$PYTHON_SERVICE_URL" \
        > "$PROJECT_ROOT/logs/java-service.log" 2>&1 &
    
    wait_for_service "Java Service" "http://localhost:$JAVA_PORT/actuator/health" 120
    
    log_ok "Development mode started!"
    log_info "Java API: http://localhost:$JAVA_PORT"
    log_info "Python API: http://localhost:$PYTHON_PORT"
    log_info "API Docs: http://localhost:$JAVA_PORT/swagger-ui.html"
}

#===============================================================================
# 停止所有服务
#===============================================================================

stop_all() {
    log_info "Stopping all services..."
    
    # 停止 Java
    if check_port "$JAVA_PORT"; then
        log_info "Stopping Java service..."
        kill $(lsof -t -i :"$JAVA_PORT") 2>/dev/null || true
    fi
    
    # 停止 Python
    if check_port "$PYTHON_PORT"; then
        log_info "Stopping Python service..."
        kill $(lsof -t -i :"$PYTHON_PORT") 2>/dev/null || true
    fi
    
    # 停止 Docker 容器
    docker compose down 2>/dev/null || true
    
    log_ok "All services stopped"
}

#===============================================================================
# 健康检查
#===============================================================================

check_health() {
    log_info "Running health checks..."
    
    local all_ok=true
    
    # Java (允许 Doris DOWN，因为开发环境使用内存模式)
    local java_status=$(curl -s http://localhost:$JAVA_PORT/actuator/health 2>/dev/null)
    if echo "$java_status" | grep -q '"status":"UP"\|"status":"DOWN"'; then
        if echo "$java_status" | grep -q '"neo4j":{\"status\":\"UP\"'; then
            log_ok "Java service: HEALTHY (Neo4j connected)"
        else
            log_warn "Java service: RUNNING but Neo4j not connected"
        fi
    else
        log_err "Java service: UNHEALTHY"
        all_ok=false
    fi
    
    # Python
    if curl -s http://localhost:$PYTHON_PORT/health >/dev/null 2>&1; then
        log_ok "Python service: HEALTHY"
    else
        log_err "Python service: UNHEALTHY"
        all_ok=false
    fi
    
    # Neo4j
    if curl -s -u "$NEO4J_USER:$NEO4J_PASSWORD" http://localhost:7474/db/data/ >/dev/null 2>&1 || \
       python3 -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://localhost:7687', auth=('$NEO4J_USER', '$NEO4J_PASSWORD')).verify_connectivity()" 2>/dev/null; then
        log_ok "Neo4j: HEALTHY"
    else
        log_warn "Neo4j: UNHEALTHY (optional for dev mode)"
    fi
    
    # Kafka
    if nc -z localhost 9092 2>/dev/null; then
        log_ok "Kafka: HEALTHY"
    else
        log_warn "Kafka: UNHEALTHY (optional for dev mode)"
    fi
    
    if $all_ok; then
        log_ok "All core services are healthy!"
        log_info "Note: Doris DB shows DOWN in dev mode (expected, using in-memory fallback)"
        return 0
    else
        log_err "Some services are unhealthy"
        return 1
    fi
}

#===============================================================================
# 查看日志
#===============================================================================

show_logs() {
    local service="${1:-all}"
    case "$service" in
        java)
            tail -f "$PROJECT_ROOT/logs/java-service.log"
            ;;
        python)
            tail -f "$PROJECT_ROOT/logs/python-service.log"
            ;;
        all|*)
            tail -f "$PROJECT_ROOT/logs/java-service.log" "$PROJECT_ROOT/logs/python-service.log" 2>/dev/null
            ;;
    esac
}

#===============================================================================
# 主入口
#===============================================================================

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

case "$MODE" in
    all)
        start_infra
        start_python
        start_java
        sleep 3
        check_health
        log_ok "============================================"
        log_ok "All services started successfully!"
        log_ok "============================================"
        log_info "Java API:       http://localhost:$JAVA_PORT"
        log_info "Python API:     http://localhost:$PYTHON_PORT"
        log_info "Neo4j Browser:  http://localhost:7474"
        log_info "API Docs:       http://localhost:$JAVA_PORT/swagger-ui.html"
        log_info ""
        log_info "Commands:"
        log_info "  ./scripts/start_all.sh stop     # 停止所有服务"
        log_info "  ./scripts/start_all.sh health   # 健康检查"
        log_info "  ./scripts/start_all.sh logs     # 查看日志"
        ;;
    infra)
        start_infra
        ;;
    java)
        start_java
        ;;
    python)
        start_python
        ;;
    dev)
        start_dev
        ;;
    stop)
        stop_all
        ;;
    health)
        check_health
        ;;
    logs)
        show_logs "${2:-all}"
        ;;
    *)
        echo "Usage: $0 {all|infra|java|python|dev|stop|health|logs [java|python|all]}"
        echo ""
        echo "Modes:"
        echo "  all     - Start everything (infra + python + java)"
        echo "  infra   - Start only infrastructure (Neo4j + Kafka)"
        echo "  java    - Start only Java service"
        echo "  python  - Start only Python service"
        echo "  dev     - Start Java + Python in dev mode (in-memory, no Docker)"
        echo "  stop    - Stop all services"
        echo "  health  - Check all service health"
        echo "  logs    - Show logs (optionally: java|python|all)"
        echo ""
        echo "Environment variables:"
        echo "  SERVER_PORT=$JAVA_PORT"
        echo "  PYTHON_PORT=$PYTHON_PORT"
        echo "  NEO4J_URI=$NEO4J_URI"
        echo "  PYTHON_SERVICE_URL=$PYTHON_SERVICE_URL"
        exit 1
        ;;
esac
