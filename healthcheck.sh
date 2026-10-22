#!/usr/bin/env bash
# ==============================================================================
# AIOps Sentinel - Health Check Script for Linux / macOS / WSL
# ==============================================================================
set -euo pipefail

echo "=========================================================================="
echo "AIOPS SENTINEL SYSTEM HEALTH CHECK & AUDIT"
echo "Timestamp: $(date -u)"
echo "=========================================================================="

check_url() {
    local name="$1"
    local url="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" || echo "000")
    if [ "$code" -eq 200 ]; then
        printf "[PASS] %-30s | %-35s | HTTP %s\n" "$name" "$url" "$code"
    else
        printf "[FAIL] %-30s | %-35s | HTTP %s\n" "$name" "$url" "$code"
    fi
}

check_container() {
    local name="$1"
    local status
    status=$(docker inspect --format='{{.State.Status}} ({{if .State.Health}}{{.State.Health.Status}}{{else}}unmonitored{{end}})' "$name" 2>/dev/null || echo "not found")
    if [[ "$status" == *"running"* ]]; then
        printf "[PASS] %-30s | Docker Container | %s\n" "$name" "$status"
    else
        printf "[FAIL] %-30s | Docker Container | %s\n" "$name" "$status"
    fi
}

echo ""
echo "[1/2] Checking Docker Containers..."
check_container "mlops_cp-backend-1"
check_container "mlops_cp-frontend-1"
check_container "mlops_cp-nginx-1"
check_container "mlops_cp-db-1"
check_container "mlops_cp-redis-1"
check_container "mlops_cp-prometheus-1"
check_container "mlops_cp-grafana-1"
check_container "mlops_cp-loki-1"
check_container "mlops_cp-otel-collector-1"
check_container "mlops_cp-cadvisor-1"
check_container "mlops_cp-node-exporter-1"
check_container "mlops_cp-promtail-1"

echo ""
echo "[2/2] Checking HTTP Services..."
check_url "FastAPI Health" "http://localhost:8000/api/v1/health"
check_url "Prometheus Metrics" "http://localhost:8000/internal/metrics"
check_url "Anomaly ML Engine" "http://localhost:8000/api/v1/ml/anomaly/health"
check_url "Clusterer ML Engine" "http://localhost:8000/api/v1/ml/cluster/health"
check_url "RCA GNN ML Engine" "http://localhost:8000/api/v1/ml/root-cause/health"
check_url "Risk ML Engine" "http://localhost:8000/api/v1/ml/risk/health"
check_url "Frontend Ingress" "http://localhost:8081"
check_url "Prometheus UI" "http://localhost:9090/-/healthy"
check_url "Grafana UI" "http://localhost:3000/api/health"
check_url "Loki Ready Probe" "http://localhost:3100/ready"
echo "=========================================================================="
