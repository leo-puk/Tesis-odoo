#!/usr/bin/env bash
# Equivalente POSIX de odoolab.ps1 (WSL / Linux).
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
cmd="${1:-status}"; shift || true
case "$cmd" in
  up)    docker compose up -d --build ;;
  down)  docker compose down ;;
  nuke)  docker compose down -v; docker rm -f $(docker ps -aq --filter label=odolab.role=fork) 2>/dev/null || true ;;
  shell) docker exec -it sbx-control bash ;;
  logs)  docker compose logs -f "$@" ;;
  *)     docker exec -e ODOLAB_HOST_ROOT="$PWD" sbx-control python -m odoolab.cli "$cmd" "$@" ;;
esac
