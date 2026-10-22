#!/usr/bin/env bash
# ==============================================================================
# AIOps Sentinel - Stop Script for Linux / macOS / WSL
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping AIOps Sentinel services..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" stop
echo "Services stopped. Persistent volumes preserved."
