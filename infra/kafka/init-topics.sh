#!/bin/bash
set -e

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"

echo "Waiting for Kafka at ${BOOTSTRAP}..."
until /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server "${BOOTSTRAP}" >/dev/null 2>&1; do
  sleep 2
done

echo "Creating topics..."
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" \
  --create --if-not-exists --topic shop.events --partitions 3 --replication-factor 1

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" \
  --create --if-not-exists --topic load.test --partitions 3 --replication-factor 1

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" --list
echo "Kafka topics ready."
