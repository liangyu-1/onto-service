#!/bin/bash
set -e

KAFKA_VERSION=3.7.0
SCALA_VERSION=2.13
KAFKA_HOME=/opt/kafka

# Download Kafka if not exists
if [ ! -d "$KAFKA_HOME" ]; then
    echo "Downloading Kafka..."
    wget -qO- https://archive.apache.org/dist/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz | tar -xzf - -C /opt
    mv /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} $KAFKA_HOME
fi

# Generate cluster id
CLUSTER_ID=$(cat /tmp/kafka-cluster-id 2>/dev/null || $KAFKA_HOME/bin/kafka-storage.sh random-uuid | tee /tmp/kafka-cluster-id)
echo "CLUSTER_ID: $CLUSTER_ID"

# Format storage
if [ ! -f "$KAFKA_HOME/logs/.formatted" ]; then
    echo "Formatting storage..."
    mkdir -p $KAFKA_HOME/logs
    $KAFKA_HOME/bin/kafka-storage.sh format -t $CLUSTER_ID -c $KAFKA_HOME/config/kraft/server.properties
    touch $KAFKA_HOME/logs/.formatted
fi

# Configure
cat > $KAFKA_HOME/config/kraft/server.properties <<EOF
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:9093
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://localhost:9093
advertised.listeners=PLAINTEXT://localhost:9092
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=$KAFKA_HOME/logs
num.partitions=1
offsets.topic.replication.factor=1
auto.create.topics.enable=true
EOF

echo "Starting Kafka..."
exec $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/kraft/server.properties
