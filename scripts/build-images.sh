#!/bin/bash
# =============================================================================
# OaaS 本体语义检索服务 - 一键构建镜像脚本 (Java Only)
# =============================================================================
# 用法:
#   ./build-images.sh [选项]
#
# 选项:
#   -t, --tag <tag>       镜像标签 (默认: latest)
#   -r, --registry <url>  镜像仓库前缀 (默认: 空，本地构建)
#   -p, --push            构建后推送到仓库
#   -h, --help            显示帮助
#
# 示例:
#   ./build-images.sh                          # 本地构建，tag=latest
#   ./build-images.sh -t v1.2.0                # 本地构建，tag=v1.2.0
#   ./build-images.sh -r registry.example.com  # 带仓库前缀
#   ./build-images.sh -t v1.2.0 -p             # 构建并推送
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认值
TAG="latest"
REGISTRY=""
PUSH=false

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 打印帮助
show_help() {
    cat << 'HELP'
用法: ./build-images.sh [选项]

选项:
  -t, --tag <tag>       镜像标签 (默认: latest)
  -r, --registry <url>  镜像仓库前缀 (默认: 空，本地构建)
  -p, --push            构建后推送到仓库
  -h, --help            显示帮助

示例:
  ./build-images.sh                          # 本地构建，tag=latest
  ./build-images.sh -t v1.2.0                # 本地构建，tag=v1.2.0
  ./build-images.sh -r registry.example.com  # 带仓库前缀
  ./build-images.sh -t v1.2.0 -p             # 构建并推送
HELP
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 计算完整镜像名
get_image_name() {
    local name=$1
    if [[ -n "$REGISTRY" ]]; then
        echo "${REGISTRY%/}/${name}:${TAG}"
    else
        echo "${name}:${TAG}"
    fi
}

JAVA_IMAGE=$(get_image_name "onto-service-java")

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  OaaS 镜像构建脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  项目根目录: ${YELLOW}${PROJECT_ROOT}${NC}"
echo -e "  镜像标签:   ${YELLOW}${TAG}${NC}"
[[ -n "$REGISTRY" ]] && echo -e "  镜像仓库:   ${YELLOW}${REGISTRY}${NC}"
[[ "$PUSH" == true ]] && echo -e "  推送镜像:   ${GREEN}是${NC}" || echo -e "  推送镜像:   ${RED}否${NC}"
echo ""

# =============================================================================
# 步骤 0: 前置检查
# =============================================================================
echo -e "${BLUE}[0/2] 前置检查...${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

# 检查 Maven
if ! command -v mvn &> /dev/null; then
    echo -e "${RED}错误: Maven 未安装，无法构建 Java 项目${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} 前置检查通过"
echo ""

# =============================================================================
# 步骤 1: 构建 Java 镜像
# =============================================================================
echo -e "${BLUE}[1/2] 构建 Java 镜像: ${YELLOW}${JAVA_IMAGE}${NC}"

cd "${PROJECT_ROOT}/onto-service-java"

# 强制重新编译，确保配置代码最新
echo -e "  ${YELLOW}执行 Maven 构建...${NC}"
mvn clean package -DskipTests -q
JAR_FILE=$(ls target/*.jar 2>/dev/null | grep -v "sources\|javadoc" | head -1 || true)

if [[ -z "$JAR_FILE" ]]; then
    echo -e "${RED}错误: 构建后仍未找到 jar 文件${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Jar 文件: ${YELLOW}${JAR_FILE}${NC}"

# 使用项目根目录的 Dockerfile（包含 entrypoint 和配置）
echo -e "  ${YELLOW}开始构建 Docker 镜像...${NC}"
docker build --platform linux/amd64 -t "${JAVA_IMAGE}" "${PROJECT_ROOT}"

echo -e "  ${GREEN}✓${NC} Java 镜像构建完成: ${YELLOW}${JAVA_IMAGE}${NC}"

# 推送
if [[ "$PUSH" == true ]]; then
    echo -e "  ${YELLOW}推送镜像...${NC}"
    docker push "${JAVA_IMAGE}"
    echo -e "  ${GREEN}✓${NC} 推送完成"
fi

echo ""

# =============================================================================
# 步骤 2: 验证
# =============================================================================
echo -e "${BLUE}[2/2] 验证镜像...${NC}"

JAVA_SIZE=$(docker images --format "{{.Size}}" "${JAVA_IMAGE}" 2>/dev/null || echo "未知")
echo -e "  ${GREEN}✓${NC} Java 镜像: ${YELLOW}${JAVA_IMAGE}${NC} (${JAVA_SIZE})"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  镜像构建完成!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 输出 Helm 部署命令示例
echo -e "${BLUE}Helm 部署示例:${NC}"
echo ""
echo -e "  ${YELLOW}helm install onto-service ./charts/onto-service \\\n"
echo -e "    --namespace onto-service --create-namespace \\\n"
if [[ -n "$REGISTRY" ]]; then
    echo -e "    --set java.image.repository=${REGISTRY}/onto-service-java \\\n"
    echo -e "    --set java.image.tag=${TAG}${NC}"
else
    echo -e "    --set java.image.tag=${TAG}${NC}"
fi
echo ""
