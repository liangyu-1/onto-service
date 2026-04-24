# ============================================================
# Ontology Service - Multi-stage Docker Build
# ============================================================

# ---- Stage 1: Build Java Service ----
FROM eclipse-temurin:17-jdk-jammy AS java-builder

# Use Tsinghua mirror for Ubuntu
RUN sed -i 's|http://ports.ubuntu.com/ubuntu-ports|http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y maven && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY onto-service-java/pom.xml .
COPY onto-service-java/src ./src

# Download dependencies and build
RUN mvn clean package -DskipTests

# ---- Stage 2: Runtime ----
FROM eclipse-temurin:17-jre-jammy

# Use Tsinghua mirror for Ubuntu, install python3 and pip
RUN sed -i 's|http://ports.ubuntu.com/ubuntu-ports|http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Use Tsinghua mirror for pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# Copy Java application
COPY --from=java-builder /build/target/*.jar ./onto-service.jar

# Copy Python application and install dependencies to python3.10 path
COPY onto-service-python/requirements.txt ./python/
RUN pip install --no-cache-dir -r ./python/requirements.txt

COPY onto-service-python/ ./python/

# Copy SQL scripts
COPY sql/ ./sql/

# Expose ports
EXPOSE 8080 5000

# Startup script
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
