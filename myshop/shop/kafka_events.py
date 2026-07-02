import json
import logging
from datetime import datetime, timezone

from django.conf import settings

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer

    try:
        from kafka import KafkaProducer
    except ImportError:
        logger.warning('kafka-python is not installed; events will not be published')
        return None

    try:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode('utf-8'),
            key_serializer=lambda key: str(key).encode('utf-8') if key is not None else None,
        )
    except Exception:
        logger.exception('Failed to create Kafka producer')
        return None

    return _producer


def publish_event(event_type, payload, key=None):
    producer = _get_producer()
    if producer is None:
        return False

    message = {
        'event': event_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    try:
        producer.send(settings.KAFKA_EVENTS_TOPIC, value=message, key=key)
    except Exception:
        logger.exception('Failed to publish Kafka event %s', event_type)
        return False

    return True
