import os
import json
import pytest
import numpy as np
import psutil
from unittest.mock import MagicMock, patch, AsyncMock
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sklearn.preprocessing import StandardScaler

from app.api.v1.controllers import (
    telemetry_controller,
    topology_controller,
    ml_rca_controller,
    ml_alert_clustering_controller,
    ml_anomaly_controller,
    ml_risk_controller,
    ml_registry_controller,
    organization_controller,
    risk_score_controller,
    slo_controller,
    notification_controller,
    incident_controller,
    auth_controller,
    system_controller,
)
from app.core.db import connect_db, disconnect_db
from app.core.auth import require_agent_or_user, get_current_user, create_access_token, SECRET_KEY, ALGORITHM
from app.ml_services.anomaly_detection.service import AnomalyDetectionService
from app.ml_services.anomaly_detection.models import LSTMAutoencoder
from app.ml_services.alert_clustering.embeddings import benchmark_embeddings, EmbeddingGenerator
from app.telemetry.collectors.windows import WindowsCollector
from app.schemas.extended import OrganizationCreate


# ========================================================
# 1. TELEMETRY CONTROLLER EXHAUSTIVE FILTERS & LIVE OS
# ========================================================
@pytest.mark.asyncio
async def test_telemetry_controller_exhaustive_filters(monkeypatch):
    t0 = datetime.now(timezone.utc) - timedelta(minutes=10)
    t1 = datetime.now(timezone.utc)

    sample_metric = SimpleNamespace(name="cpu_usage", serviceId="s1", timestamp=t0, value=50.0)
    sample_log = SimpleNamespace(level="ERROR", serviceId="s1", timestamp=t0, message="err")
    sample_trace = SimpleNamespace(traceId="tr-99", serviceId="s1", timestamp=t0, durationMs=10)
    sample_alert = SimpleNamespace(
        id="a1", severity="CRITICAL", title="Out of Memory", description="Pod killed",
        firedAt=t0, incidentId="inc-1", service=SimpleNamespace(name="auth"), serviceId="s1"
    )
    sample_incident = SimpleNamespace(
        id="inc-1", title="Critical Incident", severity="HIGH", status="OPEN",
        createdAt=t0, alerts=[sample_alert], service=SimpleNamespace(name="auth"), serviceId="s1"
    )

    class MockTable:
        def __init__(self, item): self.item = item
        async def find_many(self, where=None, **kwargs): return [self.item]
        async def find_first(self, **kwargs): return self.item

    monkeypatch.setattr(telemetry_controller, "prisma", SimpleNamespace(
        metric=MockTable(sample_metric),
        log=MockTable(sample_log),
        trace=MockTable(sample_trace),
        alert=MockTable(sample_alert),
        incident=MockTable(sample_incident),
        service=MockTable(SimpleNamespace(id="s1")),
        node=MockTable(SimpleNamespace(id="n1")),
    ))

    # 1. Metrics filter
    m_res = await telemetry_controller.get_metrics(serviceId="s1", name="cpu_usage", start_time=t0, end_time=t1)
    assert len(m_res) == 1
    assert m_res[0].name == "cpu_usage"

    # 2. Logs filter
    l_res = await telemetry_controller.get_logs(serviceId="s1", level="ERROR", start_time=t0, end_time=t1)
    assert len(l_res) == 1
    assert l_res[0].level == "ERROR"

    # 3. Traces filter
    tr_res = await telemetry_controller.get_traces(serviceId="s1", traceId="tr-99", start_time=t0, end_time=t1)
    assert len(tr_res) == 1
    assert tr_res[0].traceId == "tr-99"

    # 4. Alerts filter
    al_res = await telemetry_controller.get_alerts(serviceId="s1", severity="critical", start_time=t0, end_time=t1)
    assert len(al_res) == 1

    # 5. Incidents filter
    inc_res = await telemetry_controller.get_incidents(serviceId="s1", status="OPEN", start_time=t0, end_time=t1)
    assert len(inc_res) == 1

    # 6. Topology filter
    top_res = await telemetry_controller.get_topology(clusterId="cl-prod")
    assert "nodes" in top_res
    assert "services" in top_res

    # 7. safe_collect branches
    mock_coll = SimpleNamespace(
        good_method=lambda: {"status": "ok"},
        failing_method=MagicMock(side_effect=RuntimeError("Collector failed")),
    )
    monkeypatch.setattr(telemetry_controller, "get_collector", lambda: mock_coll)

    assert telemetry_controller.safe_collect("good_method") == {"status": "ok"}
    with pytest.raises(HTTPException) as exc1:
        telemetry_controller.safe_collect("failing_method")
    assert exc1.value.status_code == 500

    with pytest.raises(HTTPException) as exc2:
        telemetry_controller.safe_collect("unsupported_method")
    assert exc2.value.status_code == 404

    # 8. Live collector routes
    monkeypatch.setattr(telemetry_controller, "safe_collect", lambda m: {m: True})
    assert (await telemetry_controller.get_cpu_live())["get_cpu"] is True
    assert (await telemetry_controller.get_memory_live())["get_memory"] is True
    assert (await telemetry_controller.get_storage_live())["get_disk"] is True
    assert (await telemetry_controller.get_network_live())["get_network"] is True
    assert (await telemetry_controller.get_processes_live())["get_processes"] is True
    assert (await telemetry_controller.get_services_live())["get_services"] is True
    assert (await telemetry_controller.get_gpu_live())["get_gpu"] is True
    assert (await telemetry_controller.get_battery_live())["get_battery"] is True


# ========================================================
# 2. TOPOLOGY CONTROLLER EXHAUSTIVE INGEST & FILTERS
# ========================================================
@pytest.mark.asyncio
async def test_topology_controller_exhaustive(monkeypatch):
    existing_node = SimpleNamespace(id="node-1", status="Ready", cpuCores=4, memoryBytes=16000000)
    existing_pod = SimpleNamespace(id="pod-1", status="Pending")

    class MockNodeTable:
        async def find_first(self, **kw): return existing_node
        async def update(self, where, data): return SimpleNamespace(id=where["id"], **data)
        async def find_many(self, **kw): return [existing_node]

    class MockPodTable:
        async def find_first(self, **kw): return existing_pod
        async def update(self, where, data): return SimpleNamespace(id=where["id"], **data)
        async def find_many(self, **kw): return [existing_pod]

    class MockNamespaceTable:
        async def find_first(self, **kw): return SimpleNamespace(id="ns-1")
        async def find_many(self, **kw): return []

    monkeypatch.setattr(topology_controller, "prisma", SimpleNamespace(
        node=MockNodeTable(),
        pod=MockPodTable(),
        namespace=MockNamespaceTable(),
        service=MockNodeTable(),
    ))

    # Ingest with existing node and pod update
    res = await topology_controller.create_topology(topology_controller.TopologyIngest(
        clusterId="cl-1",
        namespaceName="default",
        nodeName="worker-1",
        podName="auth-pod",
        cpuCores=8,
        memoryBytes=32000000,
        status="Running"
    ))
    assert res["node"].cpuCores == 8
    assert res["pod"].status == "Running"

    # Query with clusterId and time range
    t0 = datetime.now(timezone.utc) - timedelta(hours=1)
    t1 = datetime.now(timezone.utc)
    res_list = await topology_controller.get_topology(clusterId="cl-1", start_time=t0, end_time=t1)
    assert len(res_list["nodes"]) == 1


# ========================================================
# 3. ML RCA CONTROLLER EXHAUSTIVE BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_ml_rca_controller_exhaustive(monkeypatch):
    # 1. training_blocked_reason branches
    # a. No telemetry -> blocked
    class MockNoTelem:
        async def find_first(self, **kw): return None
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockNoTelem()))
    assert "Recent host telemetry is required" in (await ml_rca_controller.training_blocked_reason())

    # b. Stale telemetry (>2 min) -> blocked
    old_telem = SimpleNamespace(
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=5),
        memoryTotal="8000000000",
        memoryUsed="4000000000"
    )
    class MockOldTelem:
        async def find_first(self, **kw): return old_telem
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockOldTelem()))
    assert "Recent host telemetry is required" in (await ml_rca_controller.training_blocked_reason())

    # c. Naive timestamp converted to UTC and low memory (<2 GiB free) -> blocked
    low_mem_telem = SimpleNamespace(
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None), # Naive timestamp
        memoryTotal="8000000000",
        memoryUsed="7500000000" # only 0.5 GB free
    )
    class MockLowMemTelem:
        async def find_first(self, **kw): return low_mem_telem
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockLowMemTelem()))
    reason_mem = await ml_rca_controller.training_blocked_reason()
    assert "at least 2 GiB" in reason_mem

    # d. Sufficient memory and fresh -> returns None
    good_telem = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        memoryTotal="16000000000",
        memoryUsed="4000000000" # 12 GB free
    )
    class MockGoodTelem:
        async def find_first(self, **kw): return good_telem
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(hosttelemetry=MockGoodTelem()))
    assert (await ml_rca_controller.training_blocked_reason()) is None

    # 2. train_root_cause_model execution
    monkeypatch.setattr("app.ml_services.root_cause.trainer.run_benchmarks", lambda: {"GraphSAGE": {}})
    ml_rca_controller.train_root_cause_model()
    assert ml_rca_controller.training_status["error"] is None

    # train_root_cause_model exception branch
    monkeypatch.setattr("app.ml_services.root_cause.trainer.run_benchmarks", MagicMock(side_effect=RuntimeError("Bench error")))
    ml_rca_controller.train_root_cause_model()
    assert "Bench error" in ml_rca_controller.training_status["error"]

    # 3. train_root_cause HTTP endpoint
    ml_rca_controller.training_status["running"] = True
    bg = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await ml_rca_controller.train_root_cause(bg)
    assert exc.value.status_code == 409

    ml_rca_controller.training_status["running"] = False
    # Allowed train
    res_train = await ml_rca_controller.train_root_cause(bg)
    assert res_train["status"] == "training"

    # 4. predict_root_cause error handling
    monkeypatch.setattr(ml_rca_controller.rca_service, "predict_root_cause", MagicMock(side_effect=RuntimeError("Model missing")))
    with pytest.raises(HTTPException) as exc:
        ml_rca_controller.predict_root_cause(ml_rca_controller.PredictRequest(telemetry_batch=[[0.1]*5]*7))
    assert exc.value.status_code == 503

    monkeypatch.setattr(ml_rca_controller.rca_service, "predict_root_cause", MagicMock(side_effect=ValueError("Bad batch")))
    with pytest.raises(HTTPException) as exc:
        ml_rca_controller.predict_root_cause(ml_rca_controller.PredictRequest(telemetry_batch=[[0.1]*5]*7))
    assert exc.value.status_code == 422


# ========================================================
# 4. ML ALERT CLUSTERING & ANOMALY CONTROLLERS WHEN NOT LOADED
# ========================================================
@pytest.mark.asyncio
async def test_ml_not_loaded_503_branches(monkeypatch):
    # Alert clustering
    monkeypatch.setattr(ml_alert_clustering_controller.alert_clustering_service, "is_loaded", False)
    monkeypatch.setattr(ml_alert_clustering_controller.alert_clustering_service, "load_model", lambda: None)

    with pytest.raises(HTTPException) as exc1:
        await ml_alert_clustering_controller.predict_cluster(ml_alert_clustering_controller.ClusteringRequest(log_text="test"))
    assert exc1.value.status_code == 503

    with pytest.raises(HTTPException) as exc2:
        await ml_alert_clustering_controller.batch_predict_cluster(ml_alert_clustering_controller.BatchClusteringRequest(log_texts=["test"]))
    assert exc2.value.status_code == 503

    with pytest.raises(HTTPException) as exc3:
        await ml_alert_clustering_controller.run_alert_clustering(MagicMock())
    assert exc3.value.status_code == 503

    # Anomaly detection
    monkeypatch.setattr(ml_anomaly_controller.anomaly_service, "is_loaded", False)
    monkeypatch.setattr(ml_anomaly_controller.anomaly_service, "load_model", lambda: None)

    with pytest.raises(HTTPException) as exc4:
        await ml_anomaly_controller.predict_anomaly(ml_anomaly_controller.AnomalyFeatures(value=1.0, sin_hour=0, cos_hour=1, rolling_mean_5=1, rolling_std_5=0, lag_1=1))
    assert exc4.value.status_code == 503

    with pytest.raises(HTTPException) as exc5:
        await ml_anomaly_controller.batch_predict_anomaly(ml_anomaly_controller.BatchAnomalyFeatures(data=[]))
    assert exc5.value.status_code == 503


# ========================================================
# 5. ML RISK & REGISTRY ERROR BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_ml_risk_and_registry_exceptions(monkeypatch):
    monkeypatch.setattr(ml_risk_controller.risk_service, "predict", MagicMock(side_effect=RuntimeError("Risk crash")))
    with pytest.raises(HTTPException) as exc1:
        ml_risk_controller.predict_risk(ml_risk_controller.RiskRequest())
    assert exc1.value.status_code == 500

    with pytest.raises(HTTPException) as exc2:
        ml_risk_controller.predict_risk_batch([ml_risk_controller.RiskRequest()])
    assert exc2.value.status_code == 500

    monkeypatch.setattr(ml_registry_controller, "sync_all_models_to_mlflow", MagicMock(side_effect=RuntimeError("MLflow sync fail")))
    with pytest.raises(HTTPException) as exc3:
        await ml_registry_controller.sync_registry()
    assert exc3.value.status_code == 500


# ========================================================
# 6. ANOMALY SERVICE LSTM INFERENCE & EMBEDDINGS BENCHMARK
# ========================================================
def test_anomaly_lstm_and_embeddings_benchmark(monkeypatch):
    # LSTM Autoencoder inference branch in service.py
    service = AnomalyDetectionService()
    service.model_type = "lstm"
    service.model = LSTMAutoencoder(n_features=6)
    scaler = StandardScaler()
    scaler.fit(np.zeros((10, 6)))
    service.scaler = scaler
    service.threshold = 0.5
    service.is_loaded = True

    is_anom = service.predict({"value": 10.0})
    assert isinstance(is_anom, bool)

    # Embeddings benchmark execution in embeddings.py
    monkeypatch.setattr(EmbeddingGenerator, "generate", lambda self, texts: np.random.randn(len(texts), 384))
    res_bench = benchmark_embeddings(["error log 1", "timeout log 2"])
    assert "all-MiniLM-L6-v2" in res_bench
    assert "BAAI/bge-base-en-v1.5" in res_bench


# ========================================================
# 7. WINDOWS COLLECTOR EXCEPTION BRANCHES
# ========================================================
def test_windows_collector_exceptions(monkeypatch):
    win = WindowsCollector()

    # GPUtil exception
    class MockBadGPUtil:
        @staticmethod
        def getGPUs(): raise RuntimeError("GPU query failed")
    monkeypatch.setattr("app.telemetry.collectors.windows.GPUtil", MockBadGPUtil)
    assert win.get_gpu() == []

    # WMI exception
    class MockBadWMI:
        def __init__(self, **kw): pass
        def MSAcpi_ThermalZoneTemperature(self): raise RuntimeError("WMI query failed")
    monkeypatch.setattr("app.telemetry.collectors.windows.wmi", SimpleNamespace(WMI=lambda **kw: MockBadWMI()))
    assert win.get_temperature() == []

    # win_service_iter NoSuchProcess
    class MockFlakyService:
        def as_dict(self): raise psutil.NoSuchProcess(pid=999)
    monkeypatch.setattr("psutil.win_service_iter", lambda: [MockFlakyService()])
    assert win.get_services() == []


# ========================================================
# 8. CORE DB & CORE AUTH EXHAUSTIVE CHECKS
# ========================================================
@pytest.mark.asyncio
async def test_core_db_and_auth_checks(monkeypatch):
    # DB connect and disconnect
    class MockPrismaStatus:
        def __init__(self): self.conn = False
        def is_connected(self): return self.conn
        async def connect(self): self.conn = True
        async def disconnect(self): self.conn = False

    monkeypatch.setattr("app.core.db.prisma", MockPrismaStatus())
    await connect_db()
    await disconnect_db()

    # Auth: require_agent_or_user with matching agent token
    monkeypatch.setenv("AGENT_API_TOKEN", "super-agent-secret-token-12345")
    agent_res = await require_agent_or_user(agent_token="super-agent-secret-token-12345", auth_header=None)
    assert agent_res["type"] == "agent"

    # Auth: require_agent_or_user with Bearer JWT
    now = datetime.now(timezone.utc)
    mock_session = SimpleNamespace(id="s-active", revokedAt=None, expiresAt=now + timedelta(hours=1), userId="u1")
    mock_user = SimpleNamespace(id="u1", email="valid@user.com", isActive=True, role="ADMIN")

    class MockAuthDb:
        async def find_unique(self, where):
            if "id" in where and where["id"] == "s-active": return mock_session
            if "id" in where and where["id"] == "u1": return mock_user
            return None

    monkeypatch.setattr("app.core.auth.prisma", SimpleNamespace(authsession=MockAuthDb(), user=MockAuthDb()))
    jwt_tok = create_access_token({"sub": "valid@user.com", "sid": "s-active"})
    user_res = await require_agent_or_user(agent_token=None, auth_header=f"Bearer {jwt_tok}")
    assert user_res.email == "valid@user.com"

    # Auth: invalid token -> 401
    with pytest.raises(HTTPException) as exc1:
        await require_agent_or_user(agent_token=None, auth_header="Bearer bad-jwt-token")
    assert exc1.value.status_code == 401

    # get_current_user with missing sub/sid
    bad_payload_tok = create_access_token({"sub": "", "sid": ""})
    with pytest.raises(HTTPException) as exc2:
        await get_current_user(token=bad_payload_tok)
    assert exc2.value.status_code == 401


# ========================================================
# 9. MISCELLANEOUS CONTROLLER COVERAGE
# ========================================================
@pytest.mark.asyncio
async def test_misc_controllers_coverage(monkeypatch):
    # 1. Organization Controller
    class MockOrgDb:
        async def create(self, data): return SimpleNamespace(id="o1", **data)
        async def find_many(self, **kw): return [SimpleNamespace(id="o1", name="AIOps", createdAt=datetime.now(timezone.utc))]

    monkeypatch.setattr(organization_controller, "prisma", SimpleNamespace(organization=MockOrgDb()))
    org = await organization_controller.create_organization(OrganizationCreate(name="New Org"))
    assert org.name == "New Org"
    orgs = await organization_controller.get_organizations()
    assert len(orgs) == 1

    # 2. Risk Score _parse_factors when non-JSON string
    raw_str = risk_score_controller._parse_factors("not a json string")
    assert raw_str == "not a json string"

    # 3. SLO Controller empty and zero error budget branches
    class MockSloEmpty:
        async def find_many(self, **kw): return []
    monkeypatch.setattr(slo_controller, "prisma", SimpleNamespace(servicelevelobjective=MockSloEmpty()))
    assert await slo_controller.list_slos() == []

    obj_zero_budget = SimpleNamespace(
        id="slo-1", serviceId="s1", name="Latency", metric="cpu_usage", threshold=90.0,
        targetPercent=100.0, windowHours=1, description="Sample SLO"
    )
    telem_rec = SimpleNamespace(timestamp=datetime.now(timezone.utc), cpuUsage=50.0)
    class MockSloBudget:
        async def find_many(self, **kw): return [obj_zero_budget]
    class MockTelemList:
        async def find_many(self, **kw): return [telem_rec]

    monkeypatch.setattr(slo_controller, "prisma", SimpleNamespace(
        servicelevelobjective=MockSloBudget(),
        hosttelemetry=MockTelemList()
    ))
    slo_res = await slo_controller.list_slos()
    assert len(slo_res) == 1
    assert slo_res[0]["errorBudgetRemainingPercent"] == 100.0

    # 4. Notification Controller list
    class MockNotifDb:
        async def find_many(self, **kw): return []
    monkeypatch.setattr(notification_controller, "prisma", SimpleNamespace(notification=MockNotifDb()))
    assert await notification_controller.list_notifications() == []

    # 5. Incident Controller filters
    class MockIncDb:
        async def find_many(self, where=None, **kw): return [{"where": where}]
    monkeypatch.setattr(incident_controller, "prisma", SimpleNamespace(incident=MockIncDb()))
    inc_res = await incident_controller.get_incidents(serviceId="s1", start_time=datetime.now(timezone.utc))
    assert len(inc_res) == 1

    # 6. Auth Controller status and me
    class MockUserCount:
        async def count(self): return 1
    monkeypatch.setattr(auth_controller, "prisma", SimpleNamespace(user=MockUserCount()))
    st = await auth_controller.auth_status()
    assert st["configured"] is True
    me = await auth_controller.get_current_user_profile(current_user=SimpleNamespace(id="u1"))
    assert me.id == "u1"


# ========================================================
# 10. SYSTEM CONTROLLER EXHAUSTIVE COVERAGE
# ========================================================
@pytest.mark.asyncio
async def test_system_controller_exhaustive(monkeypatch):
    # 1. get_eligible_process tests
    system_controller.last_telemetry = None
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # No timestamp
    system_controller.last_telemetry = {"timestamp": "invalid-time"}
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # Timestamp with no tzinfo
    system_controller.last_telemetry = {"timestamp": "2026-01-01T12:00:00"}
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # Stale timestamp (>30s ago)
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    system_controller.last_telemetry = {"timestamp": old_time}
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # Fresh timestamp, process not found
    fresh_time = datetime.now(timezone.utc).isoformat()
    system_controller.last_telemetry = {"timestamp": fresh_time, "processes": []}
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 404

    # Low CPU process (<20)
    system_controller.last_telemetry = {
        "timestamp": fresh_time,
        "processes": [{"pid": 100, "cpu_percent": 10.0, "name": "app.exe"}]
    }
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # Protected process
    system_controller.last_telemetry = {
        "timestamp": fresh_time,
        "processes": [{"pid": 100, "cpu_percent": 50.0, "name": "csrss.exe"}]
    }
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # Missing/invalid create_time
    system_controller.last_telemetry = {
        "timestamp": fresh_time,
        "processes": [{"pid": 100, "cpu_percent": 50.0, "name": "worker.exe"}]
    }
    with pytest.raises(HTTPException) as exc:
        system_controller.get_eligible_process(100)
    assert exc.value.status_code == 409

    # Valid process
    system_controller.last_telemetry = {
        "timestamp": fresh_time,
        "processes": [{"pid": 100, "cpu_percent": 50.0, "name": "worker.exe", "create_time": 123456789.0}]
    }
    proc, ctime = system_controller.get_eligible_process(100)
    assert proc["pid"] == 100
    assert ctime == 123456789.0

    # 2. Endpoints: get_system_root
    res_root = await system_controller.get_system_root()
    assert res_root["status"] == "online"
    assert res_root["agentConnected"] is True

    # 3. get_system_history & get_system_processes
    class MockHistoryTable:
        async def find_many(self, **kw): return [{"id": "t1"}]
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        hosttelemetry=MockHistoryTable(),
        hostprocess=MockHistoryTable()
    ))
    assert len(await system_controller.get_system_history(limit=10)) == 1
    assert len(await system_controller.get_system_processes(limit=10)) == 1

    # 4. Settings endpoints
    class MockSettingsTable:
        def __init__(self, item=None): self.item = item
        async def find_first(self): return self.item
        async def create(self, data): return SimpleNamespace(id="sett-1", **data)
    
    # get_settings when None -> creates default
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        systemsettings=MockSettingsTable(None)
    ))
    s1 = await system_controller.get_settings()
    assert s1.isMonitoring is False

    # get_agent_settings
    s2 = await system_controller.get_agent_settings()
    assert s2.isMonitoring is False

    # update_settings with non-admin enabling autoRecovery
    with pytest.raises(HTTPException) as exc_up:
        await system_controller.update_settings(
            system_controller.SystemSettingsUpdate(autoRecovery=True),
            current_user=SimpleNamespace(id="u1", role="OPERATOR", organizationId="org-1")
        )
    assert exc_up.value.status_code == 403

    # update_settings with transaction
    class MockTx:
        async def __aenter__(self):
            return SimpleNamespace(
                systemsettings=SimpleNamespace(update=AsyncMock(return_value=SimpleNamespace(id="sett-1", pollingInterval=5))),
                auditlog=SimpleNamespace(create=AsyncMock())
            )
        async def __aexit__(self, *args): pass

    existing_sett = SimpleNamespace(id="sett-1", isMonitoring=False, autoRecovery=False, pollingInterval=2)
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        systemsettings=MockSettingsTable(existing_sett),
        tx=lambda: MockTx()
    ))

    # No changes
    no_ch = await system_controller.update_settings(
        system_controller.SystemSettingsUpdate(pollingInterval=2),
        current_user=SimpleNamespace(id="u1", role="ADMIN", organizationId="org-1")
    )
    assert no_ch.pollingInterval == 2

    # With changes
    ch = await system_controller.update_settings(
        system_controller.SystemSettingsUpdate(pollingInterval=5),
        current_user=SimpleNamespace(id="u1", role="ADMIN", organizationId="org-1")
    )
    assert ch.pollingInterval == 5

    # 5. Actions endpoints
    class MockActionQueue:
        async def find_many(self, **kw): return [{"id": "act-1"}]
        async def find_first(self, **kw): return None
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        actionqueue=MockActionQueue(),
        systemsettings=MockSettingsTable(SimpleNamespace(id="sett-1", autoRecovery=False))
    ))
    assert len(await system_controller.get_pending_actions()) == 1
    assert len(await system_controller.get_action_history(limit=5, current_user=SimpleNamespace(organizationId="org-1"))) == 1

    # create_action when autoRecovery is False -> 409
    with pytest.raises(HTTPException) as exc_act:
        await system_controller.create_action(
            system_controller.ActionRequest(actionType="TERMINATE_PROCESS", target=100),
            current_user=SimpleNamespace(id="u1", role="ADMIN", organizationId="org-1")
        )
    assert exc_act.value.status_code == 409

    # complete_action tests
    class MockActionTx:
        def __init__(self, action_item): self.action_item = action_item
        async def __aenter__(self):
            return SimpleNamespace(
                actionqueue=SimpleNamespace(
                    find_unique=AsyncMock(return_value=self.action_item),
                    update=AsyncMock(return_value=SimpleNamespace(id="act-1", status="SUCCESS"))
                ),
                auditlog=SimpleNamespace(create=AsyncMock())
            )
        async def __aexit__(self, *args): pass

    # Action not found -> 404
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(tx=lambda: MockActionTx(None)))
    with pytest.raises(HTTPException) as exc_nf:
        await system_controller.complete_action("act-404", system_controller.ActionCompletion(status="SUCCESS"))
    assert exc_nf.value.status_code == 404

    # Action already completed -> 409
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(tx=lambda: MockActionTx(SimpleNamespace(id="act-1", status="SUCCESS"))))
    with pytest.raises(HTTPException) as exc_alr:
        await system_controller.complete_action("act-1", system_controller.ActionCompletion(status="SUCCESS"))
    assert exc_alr.value.status_code == 409

    # Action pending -> complete successfully
    pending_act = SimpleNamespace(id="act-1", status="PENDING", organizationId="org-1", requestedByUserId="u1")
    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(tx=lambda: MockActionTx(pending_act)))
    completed = await system_controller.complete_action("act-1", system_controller.ActionCompletion(status="SUCCESS", result="Terminated"))
    assert completed.status == "SUCCESS"

