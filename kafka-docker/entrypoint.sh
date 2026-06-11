#!/bin/bash
set -e

export KAFKA_NODE_ID=${KAFKA_NODE_ID:-1}
export KAFKA_PROCESS_ROLES=${KAFKA_PROCESS_ROLES:-broker,controller}
export KAFKA_CONTROLLER_QUORUM_VOTERS=${KAFKA_CONTROLLER_QUORUM_VOTERS:-1@localhost:9093}
export KAFKA_LISTENERS=${KAFKA_LISTENERS:-PLAINTEXT://:9092,CONTROLLER://:9093}
export KAFKA_ADVERTISED_LISTENERS=${KAFKA_ADVERTISED_LISTENERS:-PLAINTEXT://localhost:9092}
export KAFKA_CONTROLLER_LISTENER_NAMES=${KAFKA_CONTROLLER_LISTENER_NAMES:-CONTROLLER}
export KAFKA_INTER_BROKER_LISTENER_NAME=${KAFKA_INTER_BROKER_LISTENER_NAME:-PLAINTEXT}
export KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=${KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR:-1}
export KAFKA_AUTO_CREATE_TOPICS_ENABLE=${KAFKA_AUTO_CREATE_TOPICS_ENABLE:-true}

# Generate cluster id if not provided
if [ -z "$CLUSTER_ID" ]; then
    CLUSTER_ID=$(${KAFKA_HOME}/bin/kafka-storage.sh random-uuid)
    echo "Generated CLUSTER_ID: ${CLUSTER_ID}"
fi

# Format storage if not already formatted
if [ ! -f "${KAFKA_HOME}/logs/.formatted" ]; then
    echo "Formatting Kafka storage..."
    ${KAFKA_HOME}/bin/kafka-storage.sh format -t ${CLUSTER_ID} -c ${KAFKA_HOME}/config/kraft/server.properties
    mkdir -p ${KAFKA_HOME}/logs
    touch ${KAFKA_HOME}/logs/.formatted
fi

# Update server.properties with environment variables
CONFIG_FILE=${KAFKA_HOME}/config/kraft/server.properties

cat > ${CONFIG_FILE} <<EOF
process.roles=${KAFKA_PROCESS_ROLES}
node.id=${KAFKA_NODE_ID}
controller.quorum.voters=${KAFKA_CONTROLLER_QUORUM_VOTERS}
listeners=${KAFKA_LISTENERS}
advertised.listeners=${KAFKA_ADVERTISED_LISTENERS}
controller.listener.names=${KAFKA_CONTROLLER_LISTENER_NAMES}
inter.broker.listener.name=${KAFKA_INTER_BROKER_LISTENER_NAME}
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=${KAFKA_HOME}/logs
num.partitions=1
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=${KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR}
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
auto.create.topics.enable=${KAFKA_AUTO_CREATE_TOPICS_ENABLE}
EOF

echo "Starting Kafka KRaft server..."
exec ${KAFKA_HOME}/bin/kafka-server-start.sh ${CONFIG_FILE}
