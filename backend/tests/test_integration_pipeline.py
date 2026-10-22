import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.api.v1.controllers import (
    telemetry_controller,
    system_controller,
    playbook_controller,
    ml_orchestrator_controller,
)

client = TestClient(app)

integration_user = SimpleNamespace(
    id="integ-admin",
    email="admin@pipeline.local",
    organizationId="org-pipeline",
    role="ADMIN",
    firstName="Pipeline",
    lastName="Admin",
)

@pytest.fixture(autouse=True)
def override_auth(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "pipeline-agent-token")
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: integration_user
    yield
    if prev is not None:
        app.dependency_overrides[get_current_user] = prev
    else:
        app.dependency_overrides.pop(get_current_user, None)


def test_full_autonomous_incident_remediation_pipeline(monkeypatch):
    audit_events = []
    actions_queued = []

    class MockActionQueue:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            item = SimpleNamespace(id=f"act-{len(actions_queued)+1}", **d)
            actions_queued.append(item)
            return item

        async def find_many(self, **kwargs):
            return actions_queued

        async def find_first(self, **kwargs):
            return None

    class MockAuditLog:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            audit_events.append(d)
            return d

    class MockTelemetryTable:
        async def create(self, **kwargs):
            return kwargs.get("data", {})

    class MockSettingsTable:
        async def find_first(self, **kwargs):
            return SimpleNamespace(id="set-1", autoRecovery=True, isMonitoring=True, pollingInterval=2)

    class MockTransaction:
        actionqueue = MockActionQueue()
        auditlog = MockAuditLog()
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class MockPrisma:
        actionqueue = MockActionQueue()
        auditlog = MockAuditLog()
        systemtelemetry = MockTelemetryTable()
        systemsettings = MockSettingsTable()
        def tx(self):
            return MockTransaction()

    mock_prisma = MockPrisma()
    monkeypatch.setattr(system_controller, "prisma", mock_prisma)
    monkeypatch.setattr(playbook_controller, "prisma", mock_prisma)

    telemetry_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {"usage_percent": 89.4, "logical_cores": 8, "current_freq": 3200},
        "ram": {"percent": 74.0, "total": 16000000000, "used": 11840000000},
        "disk": {"percent": 55.0},
        "network": {"upload_speed": 4096, "download_speed": 8192},
        "processes": [
            {"name": "rogue_worker.exe", "pid": 8844, "cpu_percent": 85.0, "memory_percent": 15.0, "create_time": 1000000.0},
            {"name": "system.exe", "pid": 4, "cpu_percent": 1.0, "memory_percent": 2.0, "create_time": 1000000.0}
        ]
    }
    system_controller.last_telemetry = telemetry_payload

    # 1. Query Mission Control telemetry endpoint
    res_telemetry = client.get("/api/v1/system/live", headers={"X-Agent-Token": "pipeline-agent-token"})
    assert res_telemetry.status_code == 200
    assert res_telemetry.json()["data"]["cpu"]["usage_percent"] == 89.4

    # 2. Execute remediation playbook on the rogue process
    res_exec = client.post("/api/v1/playbooks/terminate-high-cpu-process/execute", json={
        "dryRun": False,
        "pid": 8844
    })
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "queued"
    assert res_exec.json()["target"] == 8844

    # 3. Verify action queue state
    res_actions = client.get("/api/v1/system/actions", headers={"X-Agent-Token": "pipeline-agent-token"})
    assert res_actions.status_code == 200
    assert len(res_actions.json()) >= 1
    assert res_actions.json()[-1]["target"] == "8844"
