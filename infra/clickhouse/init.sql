CREATE TABLE IF NOT EXISTS analytics.shop_events
(
    timestamp DateTime('UTC'),
    event LowCardinality(String),
    user_id Nullable(UInt64),
    session_key String DEFAULT '',
    path String DEFAULT '',
    method LowCardinality(String) DEFAULT '',
    status_code UInt16 DEFAULT 0,
    user_agent String DEFAULT '',
    ip String DEFAULT '',
    referer String DEFAULT '',
    page LowCardinality(String) DEFAULT '',
    element String DEFAULT '',
    element_text String DEFAULT '',
    href String DEFAULT '',
    product_id Nullable(UInt64),
    product_slug String DEFAULT '',
    product_name String DEFAULT '',
    order_id Nullable(UInt64),
    email String DEFAULT '',
    quantity Nullable(UInt32),
    total_cost String DEFAULT '',
    extra_json String DEFAULT '',
    kafka_partition UInt32 DEFAULT 0,
    kafka_offset UInt64 DEFAULT 0
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (event, timestamp)
TTL timestamp + INTERVAL 180 DAY;
