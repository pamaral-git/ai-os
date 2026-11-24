#!/usr/bin/env bash
# dsh.sh — Start and manage DeepSeek Harness with optional network mode and storage binding.
#
# Workspaces:
#   --temp        (Default) Disposable in-memory tmpfs (/workspace)
#   --permanent   Bind to permanent storage (synchronized automatically)
#   --drivework   Alias for --permanent
#
# Network Modes:
#   --airgap      (Default) Zero external egress, DNS rejected, llama-swap port 9008 only
#   --web         Outbound DNS + HTTP/HTTPS allowed for web research / git clones / Libgen
#
# Commands:
#   up            Launch harness with chosen profile (default: --airgap --temp)
#   down / stop   Stop the harness containers (syncs back permanent storage if used)
#   sync          Manually sync between container workspace and permanent storage
#   link          Print active browser authentication URL
#   logs          Stream logs from core service
# Check ai-os/Docs/Shell-DSH-Llama.html for further help
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_COMPOSE="$DIR/Deepseek-Harness/compose.yml"
[ -f "$BASE_COMPOSE" ] || BASE_COMPOSE="$HOME/.config/openshell/docker-compose.yml"
DRIVEWORK_OVERRIDE="$DIR/Deepseek-Harness/drivework.yml"
[ -f "$DRIVEWORK_OVERRIDE" ] || DRIVEWORK_OVERRIDE="$HOME/.config/openshell/docker-compose.drivework.yml"

HOST_XDRIVE="${HOST_XDRIVE:-$HOME/drivework}"
CONTAINER_BRIDGE="${CONTAINER_BRIDGE:-$HOME/drivework}"

ACTION="up"
NET_MODE="airgap"
STORAGE_MODE="temp"

for arg in "$@"; do
  case "$arg" in
    up|down|stop|sync|link|logs) ACTION="$arg" ;;
    --airgap) NET_MODE="airgap" ;;
    --web)    NET_MODE="web" ;;
    --temp)   STORAGE_MODE="temp" ;;
    --permanent|--drivework) STORAGE_MODE="permanent" ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

COMPOSE_CMD=(docker compose -f "$BASE_COMPOSE")
if [ "$STORAGE_MODE" = "permanent" ]; then
  COMPOSE_CMD+=(-f "$DRIVEWORK_OVERRIDE")
fi

sync_to_bridge() {
  if [ -d "$HOST_XDRIVE" ]; then
    mkdir -p "$CONTAINER_BRIDGE"
    rsync -a --exclude '.git' "$HOST_XDRIVE/" "$CONTAINER_BRIDGE/" 2>/dev/null || true
  fi
}

sync_to_xdrive() {
  if [ -d "$CONTAINER_BRIDGE" ] && [ -d "$(dirname "$HOST_XDRIVE")" ]; then
    mkdir -p "$HOST_XDRIVE"
    rsync -a --exclude '.git' "$CONTAINER_BRIDGE/" "$HOST_XDRIVE/" 2>/dev/null || true
  fi
}

case "$ACTION" in
  up)
    export NETWORK_MODE="$NET_MODE"
    if [ "$STORAGE_MODE" = "permanent" ]; then
      sync_to_bridge
    fi

    echo "=========================================================="
    echo "Starting DeepSeek Harness:"
    echo "  - Network Profile : $NET_MODE"
    echo "  - Workspace Mode  : $STORAGE_MODE $([ "$STORAGE_MODE" = "permanent" ] && echo "($HOST_XDRIVE)" || echo "(disposable tmpfs)")"
    echo "  - Inference Target: 192.168.127.254:9008 (Mac host llama-swap)"
    echo "=========================================================="

    "${COMPOSE_CMD[@]}" up -d
    echo "Waiting for core service to start..."
    for i in {1..20}; do
      link="$( "${COMPOSE_CMD[@]}" logs core 2>/dev/null | grep -o 'http://127.0.0.1:8999/?token=[^ ]*' | tail -n 1 || true)"
      if [ -n "$link" ]; then
        echo ""
        echo "=========================================================="
        echo "DeepSeek Harness is Ready!"
        echo "Open this link in your Mac browser:"
        echo "$link"
        echo "=========================================================="
        exit 0
      fi
      sleep 1
    done
    "${COMPOSE_CMD[@]}" logs --tail=15
    ;;
  down|stop)
    echo "Stopping DeepSeek Harness..."
    "${COMPOSE_CMD[@]}" down
    sync_to_xdrive
    echo "Synced workspace changes back to $HOST_XDRIVE"
    ;;
  sync)
    echo "Synchronizing between container workspace and $HOST_XDRIVE..."
    sync_to_xdrive
    sync_to_bridge
    echo "Sync complete."
    ;;
  logs)
    "${COMPOSE_CMD[@]}" logs -f "${2:-core}"
    ;;
  link)
    link="$( "${COMPOSE_CMD[@]}" logs core 2>/dev/null | grep -o 'http://127.0.0.1:8999/?token=[^ ]*' | tail -n 1 || true)"
    if [ -n "$link" ]; then
      echo "$link"
    else
      echo "Harness not running or token not found. Run: $0 up"
    fi
    ;;
esac
