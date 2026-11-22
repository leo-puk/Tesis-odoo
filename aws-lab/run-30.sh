#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
action="${1:-start}"
shift || true
export R2_BATCH_ID="${R2_BATCH_ID:-lote30_v6}"
if [[ ! "$R2_BATCH_ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo 'R2_BATCH_ID must contain letters, numbers, underscores or hyphens.' >&2
  exit 1
fi
if [[ "$action" == judge ]]; then
  exec python3 experimentos.py judge --output "results/$R2_BATCH_ID" --cache data/batch-cache "$@"
fi
if ! command -v docker >/dev/null 2>&1; then
  sudo bash user-data.sh
fi
docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  docker_cmd=(sudo docker)
fi
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
mkdir -p data results
compose=("${docker_cmd[@]}" compose -p "tesis-$R2_BATCH_ID" -f experiments.compose.yml)
container="tesis-$R2_BATCH_ID-runner"
case "$action" in
  start)
    if [[ "$#" -eq 0 ]]; then set -- --next 1; fi
    if "${docker_cmd[@]}" inspect "$container" >/dev/null 2>&1; then
      if [[ "$("${docker_cmd[@]}" inspect -f '{{.State.Running}}' "$container")" == true ]]; then
        echo "This batch is already running. Use logs or stop before starting another block." >&2
        exit 1
      fi
      "${docker_cmd[@]}" rm "$container" >/dev/null
    fi
    "${compose[@]}" run -d --build --name "$container" runner run \
      --output "/results/$R2_BATCH_ID" --cache /data/batch-cache "$@"
    ;;
  logs) "${docker_cmd[@]}" logs -f "$@" "$container" ;;
  status) "${docker_cmd[@]}" ps -a --filter "name=^/${container}$" ;;
  summary|evaluate|review|apply-review|freeze-sample)
    "${compose[@]}" run --rm runner "$action" --output "/results/$R2_BATCH_ID" --cache /data/batch-cache "$@"
    ;;
  stop) "${docker_cmd[@]}" stop "$container" ;;
  *) echo 'Use: bash aws-lab/run-30.sh start|logs|status|summary|review|judge|apply-review|freeze-sample|evaluate|stop [options]' >&2; exit 2 ;;
esac
