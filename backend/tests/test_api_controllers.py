import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.api.v1.controllers import (
    alert_controller,
    situation_controller,
    incident_controller,
    log_controller,
    metric_controller,
    trace_controller,
    deployment_controller,
    service_controller,
    policy_controller,
    notification_controller,
    playbook_controller,
    topology_controller,
    slo_controller,
    risk_score_controller,
    organization_controller,
    dashboard_controller,
    telemetry_controller,
    ml_alert_clustering_controller,
    ml_anomaly_controller,
    ml_risk_controller,
    ml_rca_controller,
    ml_registry_controller,
    system_controller,
)

client = TestClient(app)

test_admin = SimpleNamespace(
    id="test-admin-id",
    email="admin@sentinel.local",
    organizationId="test-org-1",
    role="ADMIN",
    firstName="Test",
    lastName="Admin",
)

@pytest.fixture(autouse=True)
def override_auth():
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield
    if prev is not None:
        app.dependency_overrides[get_current_user] = prev
    else:
        app.dependency_overrides.pop(get_current_user, None)


# ==========================================
# 1. ALERTS CONTROLLER
# ==========================================
def test_create_and_get_alerts(monkeypatch):
    alerts_db = []

    class MockAlertTable:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            item = {"id": f"alert-{len(alerts_db)+1}", **d}
            alerts_db.append(item)
            return item

        async def find_many(self, **kwargs):
            skip = kwargs.get("skip", 0)
            take = kwargs.get("take", 100)
            return alerts_db[skip:skip+take]

    monkeypatch.setattr(alert_controller, "prisma", SimpleNamespace(alert=MockAlertTable()))

    res = client.post("/api/v1/alerts/", json={
        "organizationId": "test-org-1",
        "serviceId": "svc-auth",
        "title": "High Memory",
        "description": "Exceeded 90%",
        "severity": "CRITICAL",
        "status": "OPEN",
    })
    assert res.status_code == 200
    assert res.json()["title"] == "High Memory"

    res_get = client.get("/api/v1/alerts/?serviceId=svc-auth&skip=0&limit=10")
    assert res_get.status_code == 200
    assert len(res_get.json()) == 1


# ==========================================
# 2. SITUATION CONTROLLER
# ==========================================
def test_situations_crud_and_resolve(monkeypatch):
    situation_item = {
        "id": "sit-1",
        "title": "Cascading auth failure",
        "summary": "High latency in auth",
        "status": "OPEN",
        "severity": "CRITICAL",
        "clusters": [{"id": "cl-1", "title": "Auth 500 spike"}]
    }

    class MockSituationTable:
        async def find_many(self, **kwargs):
            return [situation_item]

        async def find_unique(self, **kwargs):
            where = kwargs.get("where", {})
            if where.get("id") == "sit-1":
                return SimpleNamespace(**situation_item)
            return None

        async def update(self, **kwargs):
            data = kwargs.get("data", {})
            situation_item["status"] = data["status"]
            situation_item["summary"] = data["summary"]
            return situation_item

    monkeypatch.setattr(situation_controller, "prisma", SimpleNamespace(situation=MockSituationTable()))

    res_list = client.get("/api/v1/situations/")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    res_single = client.get("/api/v1/situations/sit-1")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == "sit-1"

    res_404 = client.get("/api/v1/situations/nonexistent")
    assert res_404.status_code == 404

    res_resolve = client.post("/api/v1/situations/sit-1/resolve", json={
        "resolutionNote": "Restarted pods and scaled up"
    })
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"

    res_conflict = client.post("/api/v1/situations/sit-1/resolve", json={
        "resolutionNote": "Second try"
    })
    assert res_conflict.status_code == 409


# ==========================================
# 3. INCIDENT, LOG, METRIC, TRACE CONTROLLERS
# ==========================================
def test_incident_log_metric_trace_controllers(monkeypatch):
    class GenericMockTable:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return {"id": "gen-1", **d}
        async def find_many(self, **kwargs):
            return [{"id": "gen-1"}]

    monkeypatch.setattr(incident_controller, "prisma", SimpleNamespace(incident=GenericMockTable()))
    monkeypatch.setattr(log_controller, "prisma", SimpleNamespace(log=GenericMockTable()))
    monkeypatch.setattr(metric_controller, "prisma", SimpleNamespace(metric=GenericMockTable()))
    monkeypatch.setattr(trace_controller, "prisma", SimpleNamespace(trace=GenericMockTable()))

    res_inc = client.post("/api/v1/incidents/", json={
        "organizationId": "test-org-1", "serviceId": "svc-1", "title": "Database Outage", "severity": "P1"
    })
    assert res_inc.status_code == 200
    assert client.get("/api/v1/incidents/").status_code == 200

    res_log = client.post("/api/v1/logs/", json={
        "serviceId": "svc-1", "level": "ERROR", "message": "Failed connection"
    })
    assert res_log.status_code == 200
    assert client.get("/api/v1/logs/").status_code == 200

    res_met = client.post("/api/v1/metrics/", json={
        "serviceId": "svc-1", "name": "cpu_util", "value": 94.2
    })
    assert res_met.status_code == 200
    assert client.get("/api/v1/metrics/").status_code == 200

    res_tr = client.post("/api/v1/traces/", json={
        "serviceId": "svc-1", "traceId": "tr-abc", "spanId": "sp-123", "name": "HTTP GET", "durationMs": 45, "status": "OK"
    })
    assert res_tr.status_code == 200
    assert client.get("/api/v1/traces/").status_code == 200


# ==========================================
# 4. DEPLOYMENT CONTROLLER
# ==========================================
def test_deployment_controller(monkeypatch):
    class MockDeploymentTable:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return {"id": "dep-1", **d}
        async def find_many(self, **kwargs):
            return [{"id": "dep-1", "serviceId": "svc-1"}]

    monkeypatch.setattr(deployment_controller, "prisma", SimpleNamespace(deployment=MockDeploymentTable()))

    res = client.post("/api/v1/deployments/", json={
        "serviceId": "svc-1", "version": "v1.2.0", "status": "SUCCESS"
    })
    assert res.status_code == 200
    assert client.get("/api/v1/deployments/").status_code == 200


# ==========================================
# 5. SERVICE CONTROLLER & TIER UPDATES
# ==========================================
def test_service_controller_crud_and_tier(monkeypatch):
    service_db = {"id": "svc-100", "name": "Payment API", "description": "Core checkout microservice"}

    class MockServiceTable:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return {"id": "svc-101", **d}
        async def find_many(self, **kwargs):
            return [service_db]
        async def find_unique(self, **kwargs):
            where = kwargs.get("where", {})
            if where.get("id") == "svc-100":
                return SimpleNamespace(**service_db)
            return None
        async def update(self, **kwargs):
            data = kwargs.get("data", {})
            service_db.update(data)
            return service_db

    monkeypatch.setattr(service_controller, "prisma", SimpleNamespace(service=MockServiceTable()))

    res_create = client.post("/api/v1/services/", json={
        "organizationId": "test-org-1", "clusterId": "cl-1", "name": "Auth API", "description": "Auth provider"
    })
    assert res_create.status_code == 200

    res_list = client.get("/api/v1/services/")
    assert res_list.status_code == 200

    res_tier = client.patch("/api/v1/services/svc-100/tier", json={"tier": "Tier 1 - Mission Critical"})
    assert res_tier.status_code == 200
    assert "[Tier: Tier 1 - Mission Critical]" in res_tier.json()["description"]

    res_404 = client.patch("/api/v1/services/nonexistent/tier", json={"tier": "Tier 2"})
    assert res_404.status_code == 404


# ==========================================
# 6. POLICY CONTROLLER & REGO VALIDATION
# ==========================================
def test_policy_controller_and_rego_validation(monkeypatch):
    policy_item = {
        "id": "pol-1",
        "name": "Guardrail 1",
        "rules": "package aiops\ndefault allow = false\nallow { input.cpu < 90 }",
        "isEnabled": True
    }

    class MockPolicyTable:
        async def find_many(self, **kwargs):
            return [policy_item]
        async def find_unique(self, **kwargs):
            where = kwargs.get("where", {})
            if where.get("id") == "pol-1":
                return SimpleNamespace(**policy_item)
            return None
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return {"id": "pol-2", **d}
        async def update(self, **kwargs):
            d = kwargs.get("data", {})
            policy_item.update(d)
            return policy_item
        async def delete(self, **kwargs):
            return policy_item

    class MockOrgTable:
        async def find_first(self):
            return SimpleNamespace(id="org-default")

    monkeypatch.setattr(policy_controller, "prisma", SimpleNamespace(policy=MockPolicyTable(), organization=MockOrgTable()))

    res_list = client.get("/api/v1/policies/")
    assert res_list.status_code == 200
    assert client.get("/api/v1/policies/pol-1").status_code == 200
    assert client.get("/api/v1/policies/pol-unknown").status_code == 404

    res_create = client.post("/api/v1/policies/", json={
        "name": "New Policy", "rules": "package security\ndefault allow = true"
    })
    assert res_create.status_code == 200

    res_update = client.put("/api/v1/policies/pol-1", json={"name": "Renamed Policy"})
    assert res_update.status_code == 200

    res_del = client.delete("/api/v1/policies/pol-1")
    assert res_del.status_code == 200

    res_invalid = client.post("/api/v1/policies/validate", json={"rules": "default allow = true"})
    assert res_invalid.status_code == 422

    valid_rego = """package aiops.remediation
default allow = true
allow {
    input.action == "TERMINATE_PROCESS"
    input.cpu_percent > 80
}"""
    res_val = client.post("/api/v1/policies/validate", json={"rules": valid_rego})
    assert res_val.status_code == 200
    assert res_val.json()["valid"] is True
    assert res_val.json()["decision"] == "ALLOW"


# ==========================================
# 7. NOTIFICATION CONTROLLER & TEST DISPATCH
# ==========================================
def test_notification_controller(monkeypatch):
    class MockNotifTable:
        async def find_many(self, **kwargs):
            return [{"id": "notif-1", "type": "WEBHOOK", "message": "High error rate"}]
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return SimpleNamespace(id="notif-created-1", **d)

    class MockUserTable:
        async def find_first(self, **kwargs):
            return SimpleNamespace(id="admin-id", role="ADMIN")

    class MockOrgTable:
        async def find_first(self):
            return SimpleNamespace(id="org-id")

    monkeypatch.setattr(notification_controller, "prisma", SimpleNamespace(
        notification=MockNotifTable(),
        user=MockUserTable(),
        organization=MockOrgTable()
    ))

    assert client.get("/api/v1/notifications/settings").status_code == 200

    res_upd = client.post("/api/v1/notifications/settings", json={
        "webhookUrl": "https://hooks.slack.com/services/test",
        "slackChannel": "#sre-alerts",
        "pagerDutyRoutingKey": "pd-test",
        "minSeverity": "CRITICAL"
    })
    assert res_upd.status_code == 200

    res_test = client.post("/api/v1/notifications/test", json={
        "channel": "slack",
        "message": "Manual alert test"
    })
    assert res_test.status_code == 200
    assert res_test.json()["status"] == "delivered"


# ==========================================
# 8. PLAYBOOK CONTROLLER
# ==========================================
def test_playbook_controller(monkeypatch):
    class MockPlaybookTable:
        async def find_many(self, **kwargs):
            return [{"id": "custom-pb-1", "name": "Scale deployment", "actionType": "SCALE"}]

    class TransactionContext:
        class AuditLogStore:
            async def create(self, **kwargs):
                return kwargs.get("data", {})
        auditlog = AuditLogStore()
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class MockSettingsTable:
        async def find_first(self, **kwargs):
            return SimpleNamespace(id="s1", isMonitoring=True, autoRecovery=True, pollingInterval=2)

    monkeypatch.setattr(playbook_controller, "prisma", SimpleNamespace(
        playbook=MockPlaybookTable(),
        systemsettings=MockSettingsTable(),
        tx=lambda: TransactionContext()
    ))

    res_list = client.get("/api/v1/playbooks/")
    assert res_list.status_code == 200
    names = [p["id"] for p in res_list.json()]
    assert "terminate-high-cpu-process" in names

    res_404 = client.post("/api/v1/playbooks/unknown-pb/execute", json={"dryRun": True})
    assert res_404.status_code == 404

    system_controller.last_telemetry = None
    res_no_telemetry = client.post("/api/v1/playbooks/terminate-high-cpu-process/execute", json={"dryRun": True})
    assert res_no_telemetry.status_code == 409

    system_controller.last_telemetry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processes": [{"name": "stress.exe", "pid": 4567, "cpu_percent": 88.0, "memory_percent": 12.0, "create_time": 1000000.0}],
    }

    res_dry = client.post("/api/v1/playbooks/terminate-high-cpu-process/execute", json={"dryRun": True})
    assert res_dry.status_code == 200
    assert res_dry.json()["status"] == "dry_run"
    assert res_dry.json()["target"] == 4567


# ==========================================
# 9. TOPOLOGY CONTROLLER
# ==========================================
def test_topology_controller(monkeypatch):
    class MockTopologyNamespace:
        async def find_first(self, **kwargs):
            return None
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return SimpleNamespace(id="ns-1", **d)
        async def find_many(self, **kwargs):
            return [{"id": "ns-1", "name": "default"}]

    class MockTopologyNode:
        async def find_first(self, **kwargs):
            return None
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return SimpleNamespace(id="node-1", **d)
        async def find_many(self, **kwargs):
            return [{"id": "node-1", "name": "worker-1"}]

    class MockTopologyPod:
        async def find_first(self, **kwargs):
            return None
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return SimpleNamespace(id="pod-1", **d)
        async def find_many(self, **kwargs):
            return [{"id": "pod-1", "name": "api-pod"}]

    class MockTopologyService:
        async def find_many(self, **kwargs):
            return [{"id": "svc-1", "name": "frontend", "pods": []}]

    monkeypatch.setattr(topology_controller, "prisma", SimpleNamespace(
        namespace=MockTopologyNamespace(),
        node=MockTopologyNode(),
        pod=MockTopologyPod(),
        service=MockTopologyService(),
    ))

    res_ingest = client.post("/api/v1/topology/", json={
        "clusterId": "cluster-prod",
        "namespaceName": "production",
        "nodeName": "ip-10-0-1-5",
        "podName": "frontend-6d8b-xyz",
        "status": "Running",
        "cpuCores": 4,
        "memoryBytes": 16000000000
    })
    assert res_ingest.status_code == 200

    res_get = client.get("/api/v1/topology/")
    assert res_get.status_code == 200
    assert "nodes" in res_get.json()
    assert "pods" in res_get.json()


# ==========================================
# 10. SLO CONTROLLER CRUD & DELETE
# ==========================================
def test_slo_controller_crud(monkeypatch):
    slo_item = {
        "id": "slo-1",
        "name": "Host CPU headroom",
        "description": "Host CPU headroom SLO",
        "metric": "cpu_usage",
        "threshold": 80.0,
        "targetPercent": 99.0,
        "windowHours": 24,
    }

    class MockSloTable:
        async def find_many(self, **kwargs):
            return [SimpleNamespace(**slo_item)]
        async def find_unique(self, **kwargs):
            where = kwargs.get("where", {})
            if where.get("id") == "slo-1":
                return SimpleNamespace(**slo_item)
            return None
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return SimpleNamespace(id="slo-2", **d)
        async def delete(self, **kwargs):
            return SimpleNamespace(id="slo-1")

    class MockTelemetryTable:
        async def find_many(self, **kwargs):
            return []

    monkeypatch.setattr(slo_controller, "prisma", SimpleNamespace(
        servicelevelobjective=MockSloTable(),
        hosttelemetry=MockTelemetryTable()
    ))

    res_list = client.get("/api/v1/slos/")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    res_create = client.post("/api/v1/slos/", json={
        "name": "RAM Objective",
        "description": "Keep RAM < 85%",
        "metric": "memory_usage",
        "threshold": 85.0,
        "targetPercent": 99.5,
        "windowHours": 12
    })
    assert res_create.status_code == 201

    assert client.delete("/api/v1/slos/slo-1").status_code == 204
    assert client.delete("/api/v1/slos/nonexistent").status_code == 404


# ==========================================
# 11. RISK SCORE & DASHBOARD CONTROLLER
# ==========================================
def test_risk_score_and_dashboard_controllers(monkeypatch):
    class MockRiskScoreTable:
        async def create(self, **kwargs):
            d = kwargs.get("data", {})
            return SimpleNamespace(
                id="rs-1",
                deploymentId=d.get("deploymentId"),
                score=d.get("score"),
                factors=d.get("factors"),
                createdAt=datetime.now(timezone.utc)
            )
        async def find_many(self, **kwargs):
            return [SimpleNamespace(
                id="rs-1",
                deploymentId="dep-1",
                score=0.85,
                factors='{"reason": "high churn"}',
                createdAt=datetime.now(timezone.utc)
            )]

    monkeypatch.setattr(risk_score_controller, "prisma", SimpleNamespace(riskscore=MockRiskScoreTable()))

    res_post = client.post("/api/v1/risk-scores/", json={
        "deploymentId": "dep-1",
        "score": 0.72,
        "factors": {"reason": "Large diff size"}
    })
    assert res_post.status_code == 200
    assert client.get("/api/v1/risk-scores/").status_code == 200

    class MockCounts:
        async def count(self, **kwargs):
            return 5
    class MockTelemetry:
        async def find_first(self, **kwargs):
            return SimpleNamespace(cpuUsage=15.0)
    class MockSituation:
        async def find_many(self, **kwargs):
            return []
    monkeypatch.setattr(dashboard_controller, "prisma", SimpleNamespace(
        incident=MockCounts(),
        alert=MockCounts(),
        deployment=MockCounts(),
        hosttelemetry=MockTelemetry(),
        situation=MockSituation(),
    ))
    res_dash = client.get("/api/v1/dashboard/")
    assert res_dash.status_code == 200
    assert "kpis" in res_dash.json()


# ==========================================
# 12. ML CONTROLLERS (ANOMALY, CLUSTERING, RISK, RCA, REGISTRY)
# ==========================================
def test_ml_controllers_comprehensive(monkeypatch):
    res_anom_h = client.get("/api/v1/ml/anomaly/health")
    assert res_anom_h.status_code == 200

    res_anom_det = client.post("/api/v1/ml/anomaly/predict", json={
        "value": 98.5,
        "sin_hour": 0.5,
        "cos_hour": 0.86,
        "rolling_mean_5": 50.0,
        "rolling_std_5": 1.2,
        "lag_1": 49.5
    })
    assert res_anom_det.status_code == 200

    res_clust_h = client.get("/api/v1/ml/cluster/health")
    assert res_clust_h.status_code == 200

    res_clust_pred = client.post("/api/v1/ml/cluster", json={"log_text": "CPU overload on auth pod"})
    assert res_clust_pred.status_code in (200, 503)

    res_risk_h = client.get("/api/v1/ml/risk/health")
    assert res_risk_h.status_code == 200

    res_risk_pred = client.post("/api/v1/ml/risk/predict", json={
        "deployment_size": 250,
        "files_changed": 15,
        "code_churn": 45,
        "developer_experience": 0.85
    })
    assert res_risk_pred.status_code == 200

    async def mock_blocked():
        return None
    monkeypatch.setattr(ml_rca_controller, "training_blocked_reason", mock_blocked)

    res_rca_h = client.get("/api/v1/ml/root-cause/health")
    assert res_rca_h.status_code == 200

    res_reg_list = client.get("/api/v1/ml/registry/")
    assert res_reg_list.status_code == 200
    assert len(res_reg_list.json()) >= 4

    class MockMlExperimentTable:
        async def find_many(self, **kwargs):
            return []
    monkeypatch.setattr(ml_registry_controller, "prisma", SimpleNamespace(mlexperiment=MockMlExperimentTable()))

    res_reg_exp = client.get("/api/v1/ml/registry/experiments")
    assert res_reg_exp.status_code == 200

    res_reg_detail = client.get("/api/v1/ml/registry/AnomalyDetector")
    assert res_reg_detail.status_code == 200
    assert res_reg_detail.json()["model_name"] == "AnomalyDetector"

    res_reg_404 = client.get("/api/v1/ml/registry/NonExistentModel")
    assert res_reg_404.status_code == 404

    res_reg_sync = client.post("/api/v1/ml/registry/sync")
    assert res_reg_sync.status_code == 200
    assert res_reg_sync.json()["status"] == "success"
