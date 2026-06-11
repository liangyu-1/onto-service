FROM eclipse-temurin:17-jre-jammy

ENV KAFKA_VERSION=3.7.0
ENV SCALA_VERSION=2.13
ENV KAFKA_HOME=/opt/kafka
ENV PATH=${PATH}:${KAFKA_HOME}/bin

RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN wget -qO- https://archive.apache.org/dist/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz \
    | tar -xzf - -C /opt \
    && mv /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} ${KAFKA_HOME}

WORKDIR ${KAFKA_HOME}

# KRaft mode: generate cluster id and format storage on first run
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9092 9093

ENTRYPOINT ["/entrypoint.sh"]
