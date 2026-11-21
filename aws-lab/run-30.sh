#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
action="${1:-start}"
shift || true
if ! command -v docker >/dev/null 2>&1; then
  sudo bash user-data.sh
fi
docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  docker_cmd=(sudo docker)
fi
export R2_BATCH_ID="${R2_BATCH_ID:-lote30}"
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
if [[ ! "$R2_BATCH_ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo 'R2_BATCH_ID must contain letters, numbers, underscores or hyphens.' >&2
  exit 1
fi
mkdir -p data results
compose=("${docker_cmd[@]}" compose -f experiments.compose.yml)
case "$action" in
  start) "${compose[@]}" up -d --build runner ;;
  logs) "${compose[@]}" logs -f --tail 60 runner ;;
  status) "${compose[@]}" ps -a ;;
  summary) "${compose[@]}" run --rm runner summary --output "/results/$R2_BATCH_ID" ;;
  evaluate) "${compose[@]}" run --rm runner evaluate --output "/results/$R2_BATCH_ID" "$@" ;;
  stop) "${compose[@]}" stop runner ;;
  *) echo 'Use: bash aws-lab/run-30.sh start|logs|status|summary|evaluate|stop' >&2; exit 2 ;;
esac
