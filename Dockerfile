# ============================================================
# Ontology Service - Java Only Docker Build
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
RUN mvn clean package -DskipTests -T 1C

# ---- Stage 2: Runtime ----
FROM eclipse-temurin:17-jre-jammy

# Use Tsinghua mirror for Ubuntu
RUN sed -i 's|http://ports.ubuntu.com/ubuntu-ports|http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports|g' /etc/apt/sources.list && \
    apt-get update && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Java application
COPY --from=java-builder /build/target/*.jar ./onto-service.jar

# Copy SQL scripts
COPY sql/ ./sql/

# Expose port
EXPOSE 8080

# Startup script
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
