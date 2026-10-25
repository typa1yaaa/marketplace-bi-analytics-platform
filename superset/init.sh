#!/bin/sh
set -e
superset db upgrade
superset fab create-admin --username admin --firstname Admin --lastname User \
  --email admin@example.com --password admin || true
superset init

superset set-database-uri -d marketplace \
  -u "postgresql+psycopg2://${PGUSER}:${PGPASSWORD}@postgres:5432/${PGDATABASE}" || true
