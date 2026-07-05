#!/bin/sh
set -eu

PRIMARY_HOST="${PRIMARY_HOST:-db}"
REPLICATION_USER="${REPLICATION_USER:-replicator}"
REPLICATION_PASSWORD="${REPLICATION_PASSWORD:-replicator}"
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "==> Waiting for primary at ${PRIMARY_HOST}..."
    until pg_isready -h "$PRIMARY_HOST" -U "$POSTGRES_USER" -q; do
        sleep 2
    done

    echo "==> Taking base backup from primary..."
    rm -rf "${PGDATA:?}"/*
    PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup \
        -h "$PRIMARY_HOST" \
        -U "$REPLICATION_USER" \
        -D "$PGDATA" \
        -Fp \
        -Xs \
        -P \
        -R
    echo "==> Replica data directory initialized."
fi

exec /usr/local/bin/docker-entrypoint.sh postgres
