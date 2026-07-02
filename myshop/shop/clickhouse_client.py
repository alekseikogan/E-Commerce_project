import logging

import clickhouse_connect
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client

    _client = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DATABASE,
    )
    return _client


def query_rows(sql, parameters=None):
    try:
        result = get_client().query(sql, parameters=parameters or {})
        return result.result_rows, result.column_names
    except Exception:
        logger.exception('ClickHouse query failed')
        return [], []


def query_dicts(sql, parameters=None):
    rows, columns = query_rows(sql, parameters)
    return [dict(zip(columns, row)) for row in rows]
