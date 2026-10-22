import pytest
import json
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from fastapi.testclient import TestClient

from app.main import app, bootstrap_admin_user
from app.core.auth import get_current_user
from app.api.v1.controllers import (
    telemetry_controller,
    user_controller,
    system_controller,
    ml_rca_controller,
    ml_anomaly_controller,
)

client = TestClient(app)

admin_user = SimpleNamespace(
    id="admin-ext-id",
    email="admin@ext.local",
    organizationId="org-ext-1",
    role="ADMIN",
    firstName="Ext",
    lastName="Admin",
    isActive=True,
)

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield
    app.dependency_overrides[get_current_user] = lambda: admin_user


# ==========================================
# 1. TELEMETRY CONTROLLER COMPREHENSIVE TESTS
# ==========================================
def test_telemetry_controller_ingest_and_query(monkeypatch):
    class MockRecord:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = kwargs.get("id", "rec-1")

    class MockTelemetryDb:
        async def create(self, **kwargs):
            return MockRecord(**kwargs.get("data", {}))

        async def find_many(self, **kwargs):
            return [MockRecord(
                id="item-1",
                serviceId="svc-1",
                name="cpu_usage",
                value=75.5,
                level="INFO",
                message="Service started",
                traceId="tr-1",
                spanId="sp-1",
                durationMs=120,
                status="OK",
                timestamp=datetime.now(timezone.utc),
                firedAt=datetime.now(timezone.utc),
                severity="CRITICAL",
                description="High load",
                title="Alert high load",
                incidentId="inc-1",
                service=SimpleNamespace(name="AuthService"),
                involvedObject="Pod/auth-1",
                reason="PodStarted",
                namespace="default"
            )]

    mock_db = MockTelemetryDb()
    monkeypatch.setattr(telemetry_controller, "prisma", SimpleNamespace(
        metric=mock_db,
        log=mock_db,
        trace=mock_db,
        alert=mock_db,
        k8sevent=mock_db,
        incident=mock_db,
        service=mock_db,
        node=mock_db,
    ))

    # Ingest metric, log, trace
    res_m = client.post("/api/v1/metrics", json={
        "serviceId": "svc-1", "name": "cpu", "value": 85.0
    })
    assert res_m.status_code == 200

    res_l = client.post("/api/v1/logs", json={
        "serviceId": "svc-1", "level": "WARN", "message": "High memory consumption"
    })
    assert res_l.status_code == 200

    res_t = client.post("/api/v1/traces", json={
        "serviceId": "svc-1", "traceId": "t-1", "spanId": "s-1", "name": "HTTP /login", "durationMs": 40, "status": "200"
    })
    assert res_t.status_code == 200

    # Query metrics, logs, traces, alerts, changes, incidents, topology
    assert client.get("/api/v1/metrics?serviceId=svc-1&name=cpu").status_code == 200
    assert client.get("/api/v1/logs?serviceId=svc-1&level=WARN").status_code == 200
    assert client.get("/api/v1/traces?serviceId=svc-1").status_code == 200
    assert client.get("/api/v1/alerts").status_code == 200
    assert client.get("/api/v1/changes").status_code == 200
    assert client.get("/api/v1/incidents?serviceId=svc-1&status=OPEN").status_code == 200
    assert client.get("/api/v1/topology?clusterId=prod-1").status_code == 200


def test_telemetry_controller_live_hardware_endpoints(monkeypatch):
    class MockCollector:
        def get_cpu(self): return {"usage_percent": 30.5}
        def get_memory(self): return {"percent": 45.0}
        def get_disk(self): return {"percent": 60.0}
        def get_network(self): return {"upload_speed": 100}
        def get_processes(self): return [{"name": "proc.exe", "pid": 123}]
        def get_services(self): return [{"name": "WinDefend", "status": "running"}]
        def get_gpu(self): return [{"name": "RTX 4090", "load": 20}]
        def get_battery(self): return {"percent": 95}

    monkeypatch.setattr(telemetry_controller, "get_collector", lambda: MockCollector())

    assert client.get("/api/v1/cpu").status_code == 200
    assert client.get("/api/v1/memory").status_code == 200
    assert client.get("/api/v1/storage").status_code == 200
    assert client.get("/api/v1/network").status_code == 200
    assert client.get("/api/v1/processes").status_code == 200
    assert client.get("/api/v1/gpu").status_code == 200
    assert client.get("/api/v1/battery").status_code == 200


# ==========================================
# 2. USER CONTROLLER EXTENDED CRUD & AUDIT
# ==========================================
def test_user_controller_extended(monkeypatch):
    target_user = SimpleNamespace(
        id="user-target-id",
        email="target@ext.local",
        organizationId="org-ext-1",
        role="OPERATOR",
        isActive=True,
        firstName="Target",
        lastName="User",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )

    class MockUserTable:
        async def find_first(self, **kwargs):
            return target_user
        async def find_unique(self, **kwargs):
            return None
        async def update(self, **kwargs):
            d = kwargs.get("data", {})
            target_user.__dict__.update(d)
            return target_user
        async def delete(self, **kwargs):
            return target_user
        async def count(self, **kwargs):
            return 2

    class MockAuditTable:
        async def create(self, **kwargs):
            return kwargs.get("data", {})

    class MockSessionTable:
        async def find_many(self, **kwargs):
            return []
        async def update_many(self, **kwargs):
            return 1

    class MockTx:
        user = MockUserTable()
        auditlog = MockAuditTable()
        authsession = MockSessionTable()
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass

    monkeypatch.setattr(user_controller, "prisma", SimpleNamespace(
        user=MockUserTable(),
        auditlog=MockAuditTable(),
        tx=lambda: MockTx()
    ))

    # Update role and details
    res_upd = client.patch("/api/v1/users/user-target-id", json={
        "firstName": "UpdatedName",
        "role": "ADMIN",
        "password": "NewSecurePassword123!"
    })
    assert res_upd.status_code == 200

    # Update status
    res_stat = client.patch("/api/v1/users/user-target-id/status", json={"isActive": False})
    assert res_stat.status_code == 200
    assert res_stat.json()["isActive"] is False

    # Delete user
    res_del = client.delete("/api/v1/users/user-target-id")
    assert res_del.status_code == 204


# ==========================================
# 3. SYSTEM CONTROLLER INGEST, HISTORY & SETTINGS
# ==========================================
def test_system_controller_ingest_and_settings(monkeypatch):
    class MockHostTelemetry:
        async def create(self, **kwargs):
            return SimpleNamespace(id="ht-1", **kwargs.get("data", {}))
        async def find_many(self, **kwargs):
            return [SimpleNamespace(id="ht-1", cpuUsage=45.0, timestamp=datetime.now(timezone.utc))]

    class MockHostProcess:
        async def create_many(self, **kwargs):
            return len(kwargs.get("data", []))

    class MockSettingsTable:
        async def find_first(self, **kwargs):
            return SimpleNamespace(id="set-1", isMonitoring=True, autoRecovery=True, pollingInterval=2)
        async def update(self, **kwargs):
            return SimpleNamespace(id="set-1", **kwargs.get("data", {}))

    class MockAuditLog:
        async def create(self, **kwargs):
            return kwargs.get("data", {})

    class MockActionQueue:
        async def find_unique(self, **kwargs):
            return SimpleNamespace(
                id="act-123",
                status="PENDING",
                organizationId="org-ext-1",
                requestedByUserId="admin-ext-id"
            )
        async def update(self, **kwargs):
            return SimpleNamespace(id="act-123", **kwargs.get("data", {}))

    class MockTx:
        systemsettings = MockSettingsTable()
        auditlog = MockAuditLog()
        actionqueue = MockActionQueue()
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass

    monkeypatch.setenv("AGENT_API_TOKEN", "agent-secret")
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        hosttelemetry=MockHostTelemetry(),
        hostprocess=MockHostProcess(),
        systemsettings=MockSettingsTable(),
        actionqueue=MockActionQueue(),
        tx=lambda: MockTx()
    ))

    # Ingest host telemetry
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {"usage_percent": 65.0},
        "ram": {"total": 16000000000, "used": 8000000000, "percent": 50.0},
        "disk": {"total": 500000000000, "used": 200000000000, "percent": 40.0},
        "network": {"bytes_sent": 1000, "bytes_recv": 2000},
        "processes": [{"name": "test.exe", "pid": 9999, "cpu_percent": 30.0, "memory_percent": 5.0, "exe": "C:\\test.exe"}]
    }
    res_ingest = client.post("/api/v1/system/telemetry", json=payload, headers={"X-Agent-Token": "agent-secret"})
    assert res_ingest.status_code == 200

    # History
    assert client.get("/api/v1/system/history").status_code == 200

    # Update system settings
    res_sett = client.post("/api/v1/system/settings", json={"autoRecovery": True, "pollingInterval": 5})
    assert res_sett.status_code == 200

    # Complete action
    res_comp = client.post("/api/v1/system/actions/act-123/complete", json={
        "status": "SUCCESS", "result": "Terminated successfully"
    }, headers={"X-Agent-Token": "agent-secret"})
    assert res_comp.status_code == 200


# ==========================================
# 4. ML RCA & ANOMALY EXTENDED TESTS
# ==========================================
@pytest.mark.asyncio
async def test_ml_rca_controller_extended(monkeypatch):
    class MockTelemetryTable:
        def __init__(self, sample):
            self.sample = sample
        async def find_first(self, **kwargs):
            return self.sample

    # Test 1: No telemetry
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockTelemetryTable(None)))
    assert "required" in await ml_rca_controller.training_blocked_reason()

    # Test 2: Stale telemetry
    stale_sample = SimpleNamespace(
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
        memoryTotal=16 * 1024**3,
        memoryUsed=8 * 1024**3
    )
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockTelemetryTable(stale_sample)))
    assert "required" in await ml_rca_controller.training_blocked_reason()

    # Test 3: Low memory
    low_mem_sample = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        memoryTotal=4 * 1024**3,
        memoryUsed=3.5 * 1024**3 # 0.5 GiB free < 2 GiB
    )
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockTelemetryTable(low_mem_sample)))
    assert "at least 2 GiB" in await ml_rca_controller.training_blocked_reason()

    # Test 4: Valid telemetry
    valid_sample = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        memoryTotal=16 * 1024**3,
        memoryUsed=8 * 1024**3
    )
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockTelemetryTable(valid_sample)))
    assert await ml_rca_controller.training_blocked_reason() is None

    # Test predict endpoint with 7 nodes x 5 features
    batch_data = [[0.1, 0.2, 0.3, 0.4, 0.5]] * 7
    res_pred = client.post("/api/v1/ml/root-cause/predict", json={"telemetry_batch": batch_data})
    assert res_pred.status_code in (200, 503)


def test_ml_anomaly_batch_prediction():
    res = client.post("/api/v1/ml/anomaly/batch", json={
        "data": [
            {"value": 90.0, "sin_hour": 0.5, "cos_hour": 0.86, "rolling_mean_5": 50.0, "rolling_std_5": 1.2, "lag_1": 49.5},
            {"value": 20.0, "sin_hour": 0.5, "cos_hour": 0.86, "rolling_mean_5": 50.0, "rolling_std_5": 1.2, "lag_1": 49.5}
        ]
    })
    assert res.status_code == 200
    assert "anomalies" in res.json()


# ==========================================
# 5. MAIN BOOTSTRAP ADMIN USER TESTS
# ==========================================
@pytest.mark.asyncio
async def test_main_bootstrap_admin_user(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "bootstrap@admin.local")
    monkeypatch.setenv("ADMIN_PASSWORD", "SuperSecurePassword123!")

    created_users = []

    class MockUserStore:
        def __init__(self, existing=None, count_val=0):
            self.existing = existing
            self.count_val = count_val

        async def find_unique(self, where):
            return self.existing

        async def count(self):
            return self.count_val

        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            created_users.append(d)
            return SimpleNamespace(id="new-admin", **d)

    class MockOrgStore:
        async def find_first(self):
            return SimpleNamespace(id="org-1", name="Local Org")
        async def create(self, **kwargs):
            return SimpleNamespace(id="org-1", **kwargs.get("data", {}))

    # Case 1: Existing Admin
    monkeypatch.setattr("app.main.prisma", SimpleNamespace(
        user=MockUserStore(existing=SimpleNamespace(role="ADMIN")),
        organization=MockOrgStore()
    ))
    await bootstrap_admin_user()

    # Case 2: Existing non-admin raises error
    monkeypatch.setattr("app.main.prisma", SimpleNamespace(
        user=MockUserStore(existing=SimpleNamespace(role="VIEWER")),
        organization=MockOrgStore()
    ))
    with pytest.raises(RuntimeError):
        await bootstrap_admin_user()

    # Case 3: Users exist in system
    monkeypatch.setattr("app.main.prisma", SimpleNamespace(
        user=MockUserStore(existing=None, count_val=5),
        organization=MockOrgStore()
    ))
    await bootstrap_admin_user()

    # Case 4: No users exist -> creates bootstrap admin
    monkeypatch.setattr("app.main.prisma", SimpleNamespace(
        user=MockUserStore(existing=None, count_val=0),
        organization=MockOrgStore()
    ))
    await bootstrap_admin_user()
    assert len(created_users) == 1
    assert created_users[0]["email"] == "bootstrap@admin.local"
