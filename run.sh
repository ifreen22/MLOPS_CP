#!/usr/bin/env bash
# ==============================================================================
# AIOps Sentinel - Run Script for Linux / macOS / WSL
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Launching AIOps Sentinel microservices..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d

echo ""
echo "=========================================================================="
echo "AIOPS SENTINEL IS LIVE!"
echo "=========================================================================="
echo "  • Frontend Web Console:  http://localhost:8081 (or http://localhost:5173)"
echo "  • Backend Swagger API:   http://localhost:8000/docs"
echo "  • Prometheus Dashboard:  http://localhost:9090"
echo "  • Grafana Analytics:     http://localhost:3000 (admin / admin)"
echo "  • Loki Logs Query:       http://localhost:3100"
echo "=========================================================================="
