import os
import time
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.api.v1.controllers import system_controller

client = TestClient(app)

perf_user = SimpleNamespace(
    id="perf-user",
    email="perf@sentinel.local",
    organizationId="org-perf",
    role="ADMIN",
    firstName="Perf",
    lastName="Tester",
)

@pytest.fixture(autouse=True)
def override_auth(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "test-agent-token-xyz")
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: perf_user
    yield
    if prev is not None:
        app.dependency_overrides[get_current_user] = prev
    else:
        app.dependency_overrides.pop(get_current_user, None)


def test_telemetry_endpoint_latency():
    system_controller.last_telemetry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {"usage_percent": 45.0, "logical_cores": 8},
        "ram": {"percent": 50.0, "total": 16000000000, "used": 8000000000},
        "disk": {"percent": 40.0},
        "network": {"upload_speed": 100, "download_speed": 200},
        "processes": [{"name": "test.exe", "pid": 1234, "cpu_percent": 10.0, "memory_percent": 2.0}]
    }

    latencies = []
    headers = {"X-Agent-Token": "test-agent-token-xyz"}
    client.get("/api/v1/system/live", headers=headers)
    for _ in range(10):
        start = time.perf_counter()
        res = client.get("/api/v1/system/live", headers=headers)
        duration_ms = (time.perf_counter() - start) * 1000
        latencies.append(duration_ms)
        assert res.status_code == 200

    p95 = sorted(latencies)[int(0.95 * len(latencies))]
    assert p95 < 200.0, f"Telemetry p95 latency {p95:.2f}ms exceeded SLA"


def test_anomaly_detection_inference_latency():
    sample = {
        "value": 85.0,
        "sin_hour": 0.5,
        "cos_hour": 0.86,
        "rolling_mean_5": 50.0,
        "rolling_std_5": 1.2,
        "lag_1": 49.5
    }

    latencies = []
    client.post("/api/v1/ml/anomaly/predict", json=sample)
    for _ in range(10):
        start = time.perf_counter()
        res = client.post("/api/v1/ml/anomaly/predict", json=sample)
        duration_ms = (time.perf_counter() - start) * 1000
        latencies.append(duration_ms)
        assert res.status_code == 200

    p95 = sorted(latencies)[int(0.95 * len(latencies))]
    assert p95 < 200.0, f"Anomaly detection p95 latency {p95:.2f}ms exceeded SLA"


def test_risk_prediction_inference_latency():
    sample = {
        "deployment_size": 200,
        "files_changed": 10,
        "code_churn": 30,
        "developer_experience": 0.85
    }

    latencies = []
    client.post("/api/v1/ml/risk/predict", json=sample)
    for _ in range(10):
        start = time.perf_counter()
        res = client.post("/api/v1/ml/risk/predict", json=sample)
        duration_ms = (time.perf_counter() - start) * 1000
        latencies.append(duration_ms)
        assert res.status_code == 200

    p95 = sorted(latencies)[int(0.95 * len(latencies))]
    assert p95 < 200.0, f"Risk prediction p95 latency {p95:.2f}ms exceeded SLA"
