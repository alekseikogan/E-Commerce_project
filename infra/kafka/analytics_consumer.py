import json
import os
import time
from datetime import datetime, timezone

import clickhouse_connect
from clickhouse_connect.driver.exceptions import OperationalError
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC = os.environ.get('KAFKA_EVENTS_TOPIC', 'shop.events')
GROUP_ID = os.environ.get('KAFKA_ANALYTICS_GROUP_ID', 'cozy-coza-analytics')
CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
CLICKHOUSE_DATABASE = os.environ.get('CLICKHOUSE_DATABASE', 'analytics')
CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', '')
BATCH_SIZE = int(os.environ.get('ANALYTICS_BATCH_SIZE', '100'))
FLUSH_INTERVAL = float(os.environ.get('ANALYTICS_FLUSH_INTERVAL', '2'))

COLUMN_NAMES = [
    'timestamp',
    'event',
    'user_id',
    'session_key',
    'path',
    'method',
    'status_code',
    'user_agent',
    'ip',
    'referer',
    'page',
    'element',
    'element_text',
    'href',
    'product_id',
    'product_slug',
    'product_name',
    'order_id',
    'email',
    'quantity',
    'total_cost',
    'extra_json',
    'kafka_partition',
    'kafka_offset',
]

ROW_FIELDS = {
    'event',
    'user_id',
    'session_key',
    'path',
    'method',
    'status_code',
    'user_agent',
    'ip',
    'referer',
    'page',
    'element',
    'element_text',
    'href',
    'product_id',
    'product_slug',
    'product_name',
    'order_id',
    'email',
    'quantity',
    'total_cost',
}


def wait_for_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=BOOTSTRAP,
                group_id=GROUP_ID,
            )
            consumer.close()
            return
        except NoBrokersAvailable:
            print('Waiting for Kafka...')
            time.sleep(3)


def wait_for_clickhouse():
    while True:
        try:
            client = clickhouse_connect.get_client(
                host=CLICKHOUSE_HOST,
                port=CLICKHOUSE_PORT,
                username=CLICKHOUSE_USER,
                password=CLICKHOUSE_PASSWORD,
                database=CLICKHOUSE_DATABASE,
            )
            client.query('SELECT 1 FROM shop_events LIMIT 1')
            return client
        except Exception as exc:
            print(f'Waiting for ClickHouse ({CLICKHOUSE_DATABASE}.shop_events): {exc}')
            time.sleep(3)


def parse_timestamp(value):
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def to_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def event_to_row(payload, partition, offset):
    extra = {
        key: value
        for key, value in payload.items()
        if key not in ROW_FIELDS and key != 'timestamp'
    }
    return [
        parse_timestamp(payload.get('timestamp')),
        str(payload.get('event', '')),
        to_int(payload.get('user_id')),
        str(payload.get('session_key') or ''),
        str(payload.get('path') or ''),
        str(payload.get('method') or ''),
        int(payload.get('status_code') or 0),
        str(payload.get('user_agent') or ''),
        str(payload.get('ip') or ''),
        str(payload.get('referer') or ''),
        str(payload.get('page') or ''),
        str(payload.get('element') or ''),
        str(payload.get('element_text') or payload.get('text') or ''),
        str(payload.get('href') or ''),
        to_int(payload.get('product_id')),
        str(payload.get('product_slug') or ''),
        str(payload.get('product_name') or ''),
        to_int(payload.get('order_id')),
        str(payload.get('email') or ''),
        to_int(payload.get('quantity')),
        str(payload.get('total_cost') or ''),
        json.dumps(extra, ensure_ascii=False, default=str) if extra else '',
        int(partition),
        int(offset),
    ]


def flush_batch(client, batch):
    if not batch:
        return client

    for attempt in range(1, 4):
        try:
            client.insert('shop_events', batch, column_names=COLUMN_NAMES)
            print(f'Inserted {len(batch)} events into ClickHouse', flush=True)
            return client
        except Exception as exc:
            print(f'ClickHouse insert failed (attempt {attempt}/3): {exc}', flush=True)
            time.sleep(2)
            client = wait_for_clickhouse()

    print(f'Dropped batch of {len(batch)} events after retries', flush=True)
    return client


def main():
    wait_for_kafka()
    client = wait_for_clickhouse()
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda message: message.decode('utf-8'),
    )
    print(
        f'Analytics consumer listening on "{TOPIC}" '
        f'(group: {GROUP_ID}) -> ClickHouse {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}',
        flush=True,
    )

    batch = []
    last_flush = time.monotonic()

    for message in consumer:
        try:
            payload = json.loads(message.value)
        except json.JSONDecodeError:
            print(f'Skipping invalid JSON at offset {message.offset}')
            continue

        batch.append(event_to_row(payload, message.partition, message.offset))

        if len(batch) >= BATCH_SIZE or time.monotonic() - last_flush >= FLUSH_INTERVAL:
            client = flush_batch(client, batch)
            batch = []
            last_flush = time.monotonic()


if __name__ == '__main__':
    main()
