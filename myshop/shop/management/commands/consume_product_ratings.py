import json
import os
import time

from django.core.management.base import BaseCommand
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from shop.ratings import apply_event


class Command(BaseCommand):
    help = 'Consume shop.events and update product popularity stats'

    def handle(self, *args, **options):
        bootstrap_servers = os.environ.get(
            'KAFKA_BOOTSTRAP_SERVERS',
            'kafka:9092',
        )
        topic = os.environ.get('KAFKA_EVENTS_TOPIC', 'shop.events')
        group_id = os.environ.get('KAFKA_RATING_GROUP_ID', 'cozy-coza-rating')

        self.stdout.write(
            f'Listening on "{topic}" (group: {group_id}) at {bootstrap_servers}'
        )

        while True:
            try:
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=bootstrap_servers,
                    group_id=group_id,
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    value_deserializer=lambda message: message.decode('utf-8'),
                )
                break
            except NoBrokersAvailable:
                self.stdout.write('Waiting for Kafka...')
                time.sleep(3)

        for message in consumer:
            try:
                payload = json.loads(message.value)
            except json.JSONDecodeError:
                self.stderr.write(f'Skipping invalid JSON at offset {message.offset}')
                continue

            try:
                apply_event(payload)
            except Exception:
                self.stderr.write(
                    f'Failed to apply event at offset {message.offset}: {message.value}'
                )
                raise

            self.stdout.write(
                f'offset={message.offset} event={payload.get("event")} '
                f'product_id={payload.get("product_id") or payload.get("order_id")}'
            )
