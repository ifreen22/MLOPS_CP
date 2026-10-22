import os
import json
import math
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app, bootstrap_admin_user, lifespan
from app.api.v1.controllers import (
    system_controller,
    playbook_controller,
    policy_controller,
    service_controller,
    situation_controller,
    log_controller,
    metric_controller,
    trace_controller,
    alert_controller,
    deployment_controller,
    user_controller,
    ml_orchestrator_controller,
    ml_alert_clustering_controller,
    ml_rca_controller,
    ml_risk_controller,
    ml_anomaly_controller,
    ml_registry_controller,
)
from app.ml_services.orchestrator.service import AIOrchestratorService, orchestrator_service
from app.ml_services.alert_clustering.service import AlertClusteringService
from app.ml_services.anomaly_detection.service import AnomalyDetectionService
from app.ml_services.risk_prediction.service import RiskPredictionService
from app.ml_services.root_cause.service import RootCauseAnalysisService
from app.ml_services.registry import sync_experiments_to_db, REGISTRY_MODELS
from app.telemetry.collectors.windows import WindowsCollector
from app.telemetry.collectors.linux import LinuxCollector
from app.telemetry.collectors.mac import MacCollector
from app.telemetry.collectors.base import BaseCollector
from app.schemas.extended import UserCreate, UserUpdate

client = TestClient(app)


# ========================================================
# 1. SYSTEM CONTROLLER BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_system_root_and_settings_branches(monkeypatch):
    system_controller.last_telemetry = None
    res = await system_controller.get_system_root()
    assert res["status"] == "online"
    assert res["agentConnected"] is False

    system_controller.last_telemetry = {"cpu": {"usage_percent": 12.0}}
    res2 = await system_controller.get_system_root()
    assert res2["agentConnected"] is True

    # Settings: non-admin enabling autoRecovery -> 403
    operator_user = SimpleNamespace(id="u1", role="OPERATOR", organizationId="org1")
    with pytest.raises(HTTPException) as exc_info:
        await system_controller.update_settings(
            system_controller.SystemSettingsUpdate(autoRecovery=True),
            current_user=operator_user,
        )
    assert exc_info.value.status_code == 403

    # Settings: no effective changes
    mock_settings = SimpleNamespace(id="s1", isMonitoring=True, autoRecovery=False, pollingInterval=2)
    class MockSettingsTable:
        async def find_first(self): return mock_settings
        async def create(self, **kw): return mock_settings
        async def update(self, **kw): return mock_settings
    class MockAuditTable:
        async def create(self, **kw): return None

    class MockTx:
        async def __aenter__(self):
            return SimpleNamespace(systemsettings=MockSettingsTable(), auditlog=MockAuditTable())
        async def __aexit__(self, *args): pass

    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        systemsettings=MockSettingsTable(),
        auditlog=MockAuditTable(),
        tx=lambda: MockTx(),
    ))

    admin_user = SimpleNamespace(id="adm1", role="ADMIN", organizationId="org1")
    res_no_change = await system_controller.update_settings(
        system_controller.SystemSettingsUpdate(isMonitoring=True),
        current_user=admin_user,
    )
    assert res_no_change == mock_settings

    # Settings: effective changes
    res_changed = await system_controller.update_settings(
        system_controller.SystemSettingsUpdate(pollingInterval=5),
        current_user=admin_user,
    )
    assert res_changed is not None


@pytest.mark.asyncio
async def test_system_actions_completion_and_errors(monkeypatch):
    class MockActionQueue:
        async def find_unique(self, where):
            if where.get("id") == "act-notfound":
                return None
            if where.get("id") == "act-done":
                return SimpleNamespace(id="act-done", status="SUCCESS", organizationId="org1", requestedByUserId="u1")
            return SimpleNamespace(id="act-pending", status="PENDING", organizationId="org1", requestedByUserId="u1")
        async def update(self, where, data):
            return SimpleNamespace(id=where.get("id"), status=data["status"])

    class MockAudit:
        async def create(self, **kw): return None

    class MockTx:
        async def __aenter__(self):
            return SimpleNamespace(actionqueue=MockActionQueue(), auditlog=MockAudit())
        async def __aexit__(self, *args): pass

    monkeypatch.setattr(system_controller, "prisma", SimpleNamespace(
        actionqueue=MockActionQueue(),
        auditlog=MockAudit(),
        tx=lambda: MockTx(),
    ))

    # Not found -> 404
    with pytest.raises(HTTPException) as exc1:
        await system_controller.complete_action("act-notfound", system_controller.ActionCompletion(status="SUCCESS"))
    assert exc1.value.status_code == 404

    # Already completed -> 409
    with pytest.raises(HTTPException) as exc2:
        await system_controller.complete_action("act-done", system_controller.ActionCompletion(status="SUCCESS"))
    assert exc2.value.status_code == 409

    # Successful completion
    res = await system_controller.complete_action("act-pending", system_controller.ActionCompletion(status="SUCCESS", result="done"))
    assert res.status == "SUCCESS"


# ========================================================
# 2. PLAYBOOK CONTROLLER BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_playbook_controller_branches(monkeypatch):
    viewer = SimpleNamespace(id="v1", role="VIEWER", organizationId="org1")
    admin = SimpleNamespace(id="adm", role="ADMIN", organizationId="org1")

    # 404 for unknown playbook
    with pytest.raises(HTTPException) as exc:
        await playbook_controller.execute_playbook("unknown-pb", playbook_controller.PlaybookExecutionRequest(), current_user=admin)
    assert exc.value.status_code == 404

    # 403 for viewer executing non-dryRun
    with pytest.raises(HTTPException) as exc:
        await playbook_controller.execute_playbook(playbook_controller.BUILTIN_PLAYBOOK["id"], playbook_controller.PlaybookExecutionRequest(dryRun=False), current_user=viewer)
    assert exc.value.status_code == 403

    # 409 when no telemetry
    system_controller.last_telemetry = None
    with pytest.raises(HTTPException) as exc:
        await playbook_controller.execute_playbook(playbook_controller.BUILTIN_PLAYBOOK["id"], playbook_controller.PlaybookExecutionRequest(dryRun=True), current_user=admin)
    assert exc.value.status_code == 409

    # Telemetry with no high-CPU process
    system_controller.last_telemetry = {"processes": [{"pid": 10, "cpu_percent": 5.0, "name": "idle"}]}
    with pytest.raises(HTTPException) as exc:
        await playbook_controller.execute_playbook(playbook_controller.BUILTIN_PLAYBOOK["id"], playbook_controller.PlaybookExecutionRequest(dryRun=True), current_user=admin)
    assert exc.value.status_code == 409

    # Telemetry with high CPU process
    system_controller.last_telemetry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processes": [{"pid": 1234, "cpu_percent": 85.0, "name": "heavy.exe", "create_time": 1000.0}]
    }

    class MockTx:
        async def __aenter__(self):
            return SimpleNamespace(auditlog=SimpleNamespace(create=AsyncMock()))
        async def __aexit__(self, *args): pass

    monkeypatch.setattr(playbook_controller, "prisma", SimpleNamespace(
        tx=lambda: MockTx(),
        systemsettings=SimpleNamespace(find_first=AsyncMock(return_value=SimpleNamespace(autoRecovery=True))),
        actionqueue=SimpleNamespace(find_first=AsyncMock(return_value=SimpleNamespace(id="act-exist"))),
    ))

    # Dry run
    res_dry = await playbook_controller.execute_playbook(playbook_controller.BUILTIN_PLAYBOOK["id"], playbook_controller.PlaybookExecutionRequest(dryRun=True), current_user=admin)
    assert res_dry["status"] == "dry_run"

    # Non dry-run when already pending
    res_pending = await playbook_controller.execute_playbook(playbook_controller.BUILTIN_PLAYBOOK["id"], playbook_controller.PlaybookExecutionRequest(dryRun=False), current_user=admin)
    assert res_pending["status"] == "queued"


# ========================================================
# 3. POLICY CONTROLLER BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_policy_controller_branches(monkeypatch):
    # Invalid Rego prefix -> 422
    with pytest.raises(HTTPException) as exc:
        await policy_controller.validate_policy(policy_controller.PolicyValidateRequest(rules="invalid rego code"))
    assert exc.value.status_code == 422

    # Protected system process -> DENY
    res_denied = await policy_controller.validate_policy(policy_controller.PolicyValidateRequest(
        rules="package aiops\ndefault allow = false",
        input_data={"action": "TERMINATE_PROCESS", "process_name": "csrss.exe", "cpu_percent": 95.0}
    ))
    assert res_denied["decision"] == "DENY"

    # CPU below 20% -> DENY
    res_low_cpu = await policy_controller.validate_policy(policy_controller.PolicyValidateRequest(
        rules="package aiops\ndefault allow = false",
        input_data={"action": "TERMINATE_PROCESS", "process_name": "custom.exe", "cpu_percent": 15.0}
    ))
    assert res_low_cpu["decision"] == "DENY"

    # Normal valid policy -> ALLOW
    res_allow = await policy_controller.validate_policy(policy_controller.PolicyValidateRequest(
        rules="package aiops\ndefault allow = false",
        input_data={"action": "TERMINATE_PROCESS", "process_name": "custom.exe", "cpu_percent": 55.0}
    ))
    assert res_allow["decision"] == "ALLOW"

    # Not found endpoints
    class MockPolicyTable:
        async def find_unique(self, **kw): return None
    monkeypatch.setattr(policy_controller, "prisma", SimpleNamespace(policy=MockPolicyTable()))

    with pytest.raises(HTTPException):
        await policy_controller.get_policy("nonexistent")
    with pytest.raises(HTTPException):
        await policy_controller.update_policy("nonexistent", policy_controller.PolicyUpdate(name="test"))
    with pytest.raises(HTTPException):
        await policy_controller.delete_policy("nonexistent")


# ========================================================
# 4. SERVICE & SITUATION CONTROLLER BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_service_and_situation_branches(monkeypatch):
    # Service Tier updating with existing [Tier: ...]
    class MockService:
        async def find_unique(self, where):
            return SimpleNamespace(id=where.get("id"), description="Old Service [Tier: Tier 2]")
        async def update(self, where, data):
            return SimpleNamespace(id=where.get("id"), description=data["description"])
        async def find_many(self, **kw):
            return []

    monkeypatch.setattr(service_controller, "prisma", SimpleNamespace(service=MockService()))
    res_tier = await service_controller.update_service_tier("s1", service_controller.ServiceTierUpdate(tier="Tier 1"))
    assert "[Tier: Tier 1]" in res_tier.description

    # Filter query parameters in services
    res_list = await service_controller.get_services(
        clusterId="cl-1",
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        end_time=datetime.now(timezone.utc)
    )
    assert res_list == []

    # Situation not found & not open
    class MockSituation:
        async def find_unique(self, where, **kwargs):
            if where.get("id") == "sit-404": return None
            if where.get("id") == "sit-closed": return SimpleNamespace(id="sit-closed", status="RESOLVED", summary="")
            return SimpleNamespace(id="sit-open", status="OPEN", summary="Open issue")
        async def update(self, where, data):
            return SimpleNamespace(id=where.get("id"), **data)

    monkeypatch.setattr(situation_controller, "prisma", SimpleNamespace(situation=MockSituation()))

    with pytest.raises(HTTPException) as exc:
        await situation_controller.get_situation("sit-404")
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await situation_controller.resolve_situation("sit-404", situation_controller.SituationResolution(resolutionNote="note"))
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await situation_controller.resolve_situation("sit-closed", situation_controller.SituationResolution(resolutionNote="note"))
    assert exc.value.status_code == 409

    res_res = await situation_controller.resolve_situation("sit-open", situation_controller.SituationResolution(resolutionNote="fixed it"))
    assert res_res.status == "RESOLVED"


# ========================================================
# 5. LOG, METRIC, TRACE, ALERT, DEPLOYMENT CONTROLLERS
# ========================================================
@pytest.mark.asyncio
async def test_telemetry_ingest_and_time_filters(monkeypatch):
    class MockTable:
        async def find_many(self, where=None, **kw):
            return [{"where": where}]

    monkeypatch.setattr(log_controller, "prisma", SimpleNamespace(log=MockTable()))
    monkeypatch.setattr(metric_controller, "prisma", SimpleNamespace(metric=MockTable()))
    monkeypatch.setattr(trace_controller, "prisma", SimpleNamespace(trace=MockTable()))
    monkeypatch.setattr(alert_controller, "prisma", SimpleNamespace(alert=MockTable()))
    monkeypatch.setattr(deployment_controller, "prisma", SimpleNamespace(deployment=MockTable()))

    t0 = datetime.now(timezone.utc) - timedelta(hours=1)
    t1 = datetime.now(timezone.utc)

    # Test all with start_time & end_time
    assert len(await log_controller.get_logs(serviceId="s1", start_time=t0, end_time=t1)) == 1
    assert len(await metric_controller.get_metrics(serviceId="s1", start_time=t0, end_time=t1)) == 1
    assert len(await trace_controller.get_traces(serviceId="s1", start_time=t0, end_time=t1)) == 1
    assert len(await alert_controller.get_alerts(serviceId="s1", start_time=t0, end_time=t1)) == 1
    assert len(await deployment_controller.get_deployments(serviceId="s1", start_time=t0, end_time=t1)) == 1


# ========================================================
# 6. USER CONTROLLER BRANCHES & SCHEMAS
# ========================================================
@pytest.mark.asyncio
async def test_user_controller_branches_and_validators(monkeypatch):
    # Schema validation errors
    with pytest.raises(ValueError):
        UserCreate(email="not-an-email", password="ValidPassword123!", role="OPERATOR", firstName="A", lastName="B")

    with pytest.raises(ValueError):
        UserUpdate(email="invalid-email-format")

    valid_up = UserUpdate(email=None)
    assert valid_up.email is None

    admin = SimpleNamespace(id="adm1", role="ADMIN", organizationId="org1")

    # update_user empty changes -> 422
    with pytest.raises(HTTPException) as exc:
        await user_controller.update_user("u1", UserUpdate(), current_user=admin)
    assert exc.value.status_code == 422

    # update_user password > 72 bytes -> 422
    with pytest.raises(HTTPException) as exc:
        await user_controller.update_user("u1", UserUpdate(password="A" * 71 + "€"), current_user=admin)
    assert exc.value.status_code == 422

    # Mock user table
    class MockUserTable:
        async def find_first(self, where):
            if where.get("id") == "u-notfound": return None
            if where.get("id") in ("adm1", "u-admin"): return SimpleNamespace(id="adm1", role="ADMIN", isActive=True, email="adm@org.com")
            return SimpleNamespace(id="u2", role="OPERATOR", isActive=True, email="u2@org.com")
        async def find_unique(self, where):
            if where.get("email") == "dup@org.com": return SimpleNamespace(id="u99")
            return None
        async def count(self, **kw): return 1

    monkeypatch.setattr(user_controller, "prisma", SimpleNamespace(user=MockUserTable()))

    # User not found -> 404
    with pytest.raises(HTTPException) as exc:
        await user_controller.update_user("u-notfound", UserUpdate(firstName="New"), current_user=admin)
    assert exc.value.status_code == 404

    # Email collision -> 409
    with pytest.raises(HTTPException) as exc:
        await user_controller.update_user("u2", UserUpdate(email="dup@org.com"), current_user=admin)
    assert exc.value.status_code == 409

    # Admin self-demotion -> 409
    with pytest.raises(HTTPException) as exc:
        await user_controller.update_user("adm1", UserUpdate(role="OPERATOR"), current_user=admin)
    assert exc.value.status_code == 409

    # update_user_status self-disable -> 409
    with pytest.raises(HTTPException) as exc:
        await user_controller.update_user_status("adm1", user_controller.UserStatusUpdate(isActive=False), current_user=admin)
    assert exc.value.status_code == 409

    # delete_user self-delete -> 409
    with pytest.raises(HTTPException) as exc:
        await user_controller.delete_user("adm1", current_user=admin)
    assert exc.value.status_code == 409


# ========================================================
# 7. ML ORCHESTRATOR CONTROLLER & REAL TELEMETRY PROCESS BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_ml_orchestrator_process_remediations(monkeypatch):
    class MockTelemetryHistory:
        async def find_many(self, **kw): return [SimpleNamespace(cpuUsage=85.0)]

    monkeypatch.setattr(ml_orchestrator_controller, "prisma", SimpleNamespace(hosttelemetry=MockTelemetryHistory()))

    # 1. Chrome process
    system_controller.last_telemetry = {
        "cpu": {"usage_percent": 90.0},
        "ram": {"percent": 50.0},
        "disk": {"percent": 40.0},
        "network": {"upload_speed": 100, "download_speed": 100},
        "processes": [{"pid": 555, "name": "chrome.exe", "cpu_percent": 88.0}]
    }
    res_chrome = await ml_orchestrator_controller.analyze_telemetry()
    assert any("Chrome tabs" in a for a in res_chrome["analysis"]["recommended_actions"])

    # 2. Docker process
    system_controller.last_telemetry["processes"] = [{"pid": 556, "name": "docker.exe", "cpu_percent": 85.0}]
    res_docker = await ml_orchestrator_controller.analyze_telemetry()
    assert any("Docker containers" in a for a in res_docker["analysis"]["recommended_actions"])

    # 3. Code process
    system_controller.last_telemetry["processes"] = [{"pid": 557, "name": "code.exe", "cpu_percent": 85.0}]
    res_code = await ml_orchestrator_controller.analyze_telemetry()
    assert any("VS Code" in a for a in res_code["analysis"]["recommended_actions"])

    # 4. Postgres process
    system_controller.last_telemetry["processes"] = [{"pid": 558, "name": "postgres.exe", "cpu_percent": 85.0}]
    res_pg = await ml_orchestrator_controller.analyze_telemetry()
    assert any("PostgreSQL" in a for a in res_pg["analysis"]["recommended_actions"])

    # 5. Generic heavy process
    system_controller.last_telemetry["processes"] = [{"pid": 559, "name": "customworker.exe", "cpu_percent": 85.0}]
    res_gen = await ml_orchestrator_controller.analyze_telemetry()
    assert any("customworker.exe" in a for a in res_gen["analysis"]["recommended_actions"])

    # 6. High RAM & High Disk
    system_controller.last_telemetry["processes"] = []
    system_controller.last_telemetry["ram"]["percent"] = 92.0
    system_controller.last_telemetry["disk"]["percent"] = 95.0
    res_crit = await ml_orchestrator_controller.analyze_telemetry()
    assert any("critically high" in a for a in res_crit["analysis"]["recommended_actions"])
    assert any("Clear temp files" in a for a in res_crit["analysis"]["recommended_actions"])

    # 7. Normal operation
    system_controller.last_telemetry["ram"]["percent"] = 30.0
    system_controller.last_telemetry["disk"]["percent"] = 30.0
    res_norm = await ml_orchestrator_controller.analyze_telemetry()
    assert any("operating normally" in a for a in res_norm["analysis"]["recommended_actions"])


# ========================================================
# 8. ML SERVICES EDGE CASES & ERROR BRANCHES
# ========================================================
def test_ml_services_deep_branches(monkeypatch):
    # Orchestrator with exceptions in sub-services
    orch = AIOrchestratorService()

    # Anomaly service throwing exception
    monkeypatch.setattr(orch.anomaly_service, "predict", MagicMock(side_effect=RuntimeError("Anomaly engine error")))
    res_anom_fail = orch.analyze_telemetry({
        "cpu_usage": 50.0, "sin_hour": 0.0, "cos_hour": 1.0, "rolling_mean": 50.0, "rolling_std": 0.0, "lag_1": 50.0
    })
    assert res_anom_fail["anomaly_detection"]["status"] == "unavailable"

    # Alert clustering throwing exception
    monkeypatch.setattr(orch.alert_clustering_service, "predict", MagicMock(side_effect=RuntimeError("Clustering error")))
    res_clust_fail = orch.analyze_telemetry({"log_text": "sample error log line"})
    assert res_clust_fail["alert_clustering"]["status"] == "unavailable"

    # RCA service throwing exception
    monkeypatch.setattr(orch.rca_service, "predict_root_cause", MagicMock(side_effect=RuntimeError("RCA error")))
    res_rca_fail = orch.analyze_telemetry({"topology_batch": [[1.0] * 5] * 7})
    assert res_rca_fail["root_cause_analysis"]["status"] == "unavailable"

    # Risk service predict exception
    monkeypatch.setattr(orch.risk_service, "predict", MagicMock(side_effect=RuntimeError("Risk error")))
    full_risk_payload = {
        "cpu_usage": 50.0, "sin_hour": 0.0, "cos_hour": 1.0, "rolling_mean": 50.0, "rolling_std": 0.0, "lag_1": 50.0,
        "topology_batch": [[1.0] * 5] * 7,
        "deployment_size": 100, "files_changed": 5, "code_churn": 10, "developer_experience": 0.9,
        "deployment_time": 12.0, "day_of_week": 2, "rollback_count": 0, "previous_incident_count": 0,
        "cpu_increase": 0.1, "memory_increase": 0.1, "network_latency": 10.0, "disk_io": 5.0,
        "service_dependency_count": 3
    }
    monkeypatch.setattr(orch.anomaly_service, "predict", MagicMock(return_value=False))
    monkeypatch.setattr(orch.rca_service, "predict_root_cause", MagicMock(return_value={"root_cause_service": "auth", "confidence": 0.8}))
    res_risk_fail = orch.analyze_telemetry(full_risk_payload)
    assert res_risk_fail["risk_prediction"]["status"] == "unavailable"

    # AnomalyDetectionService when not loaded
    anom_svc = AnomalyDetectionService()
    anom_svc.is_loaded = False
    with pytest.raises(ValueError):
        anom_svc.predict({"value": 10.0})

    # AlertClusteringService when not loaded
    clust_svc = AlertClusteringService()
    clust_svc.is_loaded = False
    with pytest.raises(ValueError):
        clust_svc.predict("log line")
    with pytest.raises(ValueError):
        clust_svc.batch_predict(["log line"])

    # RiskPredictionService when not loaded
    risk_svc = RiskPredictionService()
    risk_svc.model = None
    assert risk_svc.get_health()["status"] == "unhealthy"
    with pytest.raises(ValueError):
        risk_svc.predict({})

    # RootCauseAnalysisService when not loaded or wrong shape
    rca_svc = RootCauseAnalysisService()
    rca_svc.is_loaded = False
    with pytest.raises(RuntimeError):
        rca_svc.predict_root_cause([[1.0] * 5] * 7)

    rca_svc.is_loaded = True
    with pytest.raises(ValueError):
        rca_svc.predict_root_cause([[1.0] * 2]) # Wrong shape


# ========================================================
# 9. ML REGISTRY SYNC TO DB
# ========================================================
@pytest.mark.asyncio
async def test_ml_registry_sync_to_db(monkeypatch):
    class MockExpTable:
        def __init__(self):
            self.created = []
            self.updated = []
        async def find_first(self, where):
            if where.get("modelName") == "AnomalyDetector":
                return SimpleNamespace(id="exp-1")
            return None
        async def update(self, where, data):
            self.updated.append((where, data))
            return SimpleNamespace(id=where.get("id"), **data)
        async def create(self, data):
            self.created.append(data)
            return SimpleNamespace(id="exp-new", **data)

    mock_table = MockExpTable()
    monkeypatch.setattr("app.ml_services.registry.prisma", SimpleNamespace(mlexperiment=mock_table))

    records = await sync_experiments_to_db()
    assert len(records) == len(REGISTRY_MODELS)
    assert len(mock_table.updated) >= 1
    assert len(mock_table.created) >= 1


# ========================================================
# 10. TELEMETRY COLLECTORS ON ALL PLATFORMS
# ========================================================
# 10. TELEMETRY COLLECTORS ON ALL PLATFORMS
# ========================================================
def test_all_telemetry_collectors(monkeypatch):
    # WindowsCollector
    mock_svc = SimpleNamespace(as_dict=lambda: {"name": "svc1", "display_name": "Service 1", "status": "running", "start_type": "auto"})
    monkeypatch.setattr("psutil.win_service_iter", lambda: [mock_svc])
    win = WindowsCollector()
    assert isinstance(win.get_gpu(), list)
    assert isinstance(win.get_temperature(), list)
    assert isinstance(win.get_services(), list)

    # LinuxCollector
    linux = LinuxCollector()
    assert isinstance(linux.get_gpu(), list)
    assert isinstance(linux.get_temperature(), list)
    assert isinstance(linux.get_services(), list)

    # MacCollector
    mac = MacCollector()
    assert mac.get_gpu() == []
    assert isinstance(mac.get_temperature(), list)
    assert mac.get_services() == []

    # BaseCollector methods
    assert win.get_battery() is None or isinstance(win.get_battery(), dict)
    disk = win.get_disk()
    assert "partitions" in disk
    net = win.get_network()
    assert "bytes_sent" in net
    assert win.get_uptime() > 0


# ========================================================
# 11. BATCH ENDPOINTS & BACKGROUND RUNNERS
# ========================================================
@pytest.mark.asyncio
async def test_batch_endpoints_and_background_runners(monkeypatch):
    # 1. Alert Clustering controller batch, run, statistics
    class MockCountPrisma:
        async def count(self, **kw): return 0
    monkeypatch.setattr("app.core.db.prisma", SimpleNamespace(
        alert=MockCountPrisma(),
        situation=MockCountPrisma(),
        alertcluster=MockCountPrisma(),
    ))
    res_stat = await ml_alert_clustering_controller.get_statistics()
    assert "open_alerts" in res_stat

    bg_tasks = MagicMock()
    res_run = await ml_alert_clustering_controller.run_alert_clustering(bg_tasks)
    assert res_run["status"] == "started"
    bg_tasks.add_task.assert_called_once()

    res_train_clust = await ml_alert_clustering_controller.trigger_training(bg_tasks)
    assert "initiated" in res_train_clust["status"]

    # 2. Anomaly batch predict
    res_anom_batch = await ml_anomaly_controller.batch_predict_anomaly(
        ml_anomaly_controller.BatchAnomalyFeatures(data=[
            ml_anomaly_controller.AnomalyFeatures(value=50.0, sin_hour=0.0, cos_hour=1.0, rolling_mean_5=50.0, rolling_std_5=0.0, lag_1=50.0)
        ])
    )
    assert "anomalies" in res_anom_batch

    # 3. RCA batch predict
    res_rca_batch = ml_rca_controller.predict_root_cause_batch([
        ml_rca_controller.PredictRequest(telemetry_batch=[[0.1] * 5] * 7)
    ])
    assert len(res_rca_batch) == 1

    # 4. Risk batch predict
    res_risk_batch = ml_risk_controller.predict_risk_batch([
        ml_risk_controller.RiskRequest(deployment_size=100.0)
    ])
    assert len(res_risk_batch) == 1


# ========================================================
# 12. MAIN LIFESPAN & ADMIN BOOTSTRAP
# ========================================================
@pytest.mark.asyncio
async def test_main_bootstrap_and_lifespan(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@sentinel.local")
    monkeypatch.setenv("ADMIN_PASSWORD", "SuperSecurePassword123!")

    class MockUserTable:
        async def count(self): return 0
        async def find_unique(self, where): return None
        async def create(self, **kw): return None

    class MockOrgTable:
        async def find_first(self): return None
        async def create(self, **kw): return SimpleNamespace(id="org-bootstrap")

    class MockPrisma:
        async def connect(self): pass
        async def disconnect(self): pass
        user = MockUserTable()
        organization = MockOrgTable()

    monkeypatch.setattr("app.main.prisma", MockPrisma())
    await bootstrap_admin_user()

    # Test lifespan
    async with lifespan(app):
        pass
