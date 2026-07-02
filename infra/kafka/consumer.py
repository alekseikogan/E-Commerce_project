import json
import os
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable


BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC = os.environ.get('KAFKA_TOPIC', 'shop.events')
GROUP_ID = os.environ.get('KAFKA_GROUP_ID', 'cozy-coza-events')


def wait_for_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=BOOTSTRAP,
                group_id=GROUP_ID,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda m: m.decode('utf-8'),
            )
            consumer.close()
            return
        except NoBrokersAvailable:
            print('Waiting for Kafka...')
            time.sleep(3)


def main():
    wait_for_kafka()
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: m.decode('utf-8'),
    )
    print(f'Listening on topic "{TOPIC}" (group: {GROUP_ID})')
    for message in consumer:
        try:
            payload = json.loads(message.value)
        except json.JSONDecodeError:
            payload = message.value
        print(
            f'partition={message.partition} offset={message.offset} '
            f'key={message.key} value={payload}'
        )


if __name__ == '__main__':
    main()
