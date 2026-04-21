# ============================================================
# Ontology Service - Multi-stage Docker Build
# ============================================================

# ---- Stage 1: Build Java Service ----
FROM maven:3.9-eclipse-temurin-17 AS java-builder

WORKDIR /build
COPY onto-service-java/pom.xml .
COPY onto-service-java/src ./src

# Download dependencies and build
RUN mvn clean package -DskipTests

# ---- Stage 2: Build Python Service ----
FROM python:3.11-slim AS python-builder

WORKDIR /build
COPY onto-service-python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY onto-service-python/ ./

# ---- Stage 3: Runtime ----
FROM eclipse-temurin:17-jre-jammy

# Install Python
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Java application
COPY --from=java-builder /build/target/*.jar ./onto-service.jar

# Copy Python application
COPY --from=python-builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages
COPY onto-service-python/ ./python/

# Copy SQL scripts
COPY sql/ ./sql/

# Expose ports
EXPOSE 8080 5000

# Startup script
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
