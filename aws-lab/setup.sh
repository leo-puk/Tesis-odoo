#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data/addons results
if [[ ! -f .env ]]; then
  umask 077
  printf 'PG_PASSWORD=%s\nODOO_VERSION=16.0\n' "$(openssl rand -hex 24)" > .env
fi
docker compose --env-file .env -f compose.yml config --quiet
docker compose --env-file .env -f compose.yml up -d --wait db odoo
ready=false
for attempt in {1..60}; do
  if curl --fail --silent --output /dev/null http://127.0.0.1:8069/web/database/selector; then
    ready=true
    break
  fi
  sleep 2
done
if [[ "$ready" != true ]]; then
  docker compose --env-file .env -f compose.yml logs --tail 60 odoo
  exit 1
fi
docker compose --env-file .env -f compose.yml build r2
docker compose --env-file .env -f compose.yml run --rm r2 --version
docker compose --env-file .env -f compose.yml ps
