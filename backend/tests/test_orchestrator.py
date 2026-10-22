import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from types import SimpleNamespace
import asyncio
import json
from datetime import datetime, timedelta, timezone

from app.api.v1.controllers import (
    auth_controller,
    ml_orchestrator_controller,
    ml_rca_controller,
    system_controller,
    user_controller,
)
from app.core import auth as auth_core
from app.core.auth import get_current_user

client = TestClient(app)
test_user = SimpleNamespace(
    id="test-user",
    email="admin@example.test",
    organizationId="test-organization",
    role="ADMIN",
    firstName="Test",
    lastName="Admin",
)
app.dependency_overrides[get_current_user] = lambda: test_user

def test_orchestrator_health():
    response = client.get("/api/v1/ml/analyze/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "anomaly_detection" in data["services"]


def test_metrics_endpoint_is_registered_in_api_schema():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/metrics/" in response.json()["paths"]


def test_protected_api_requires_a_bearer_token():
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.get("/api/v1/ml/analyze/health")
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 401


def test_agent_endpoint_requires_the_configured_agent_token(monkeypatch):
    class EmptyActionQueue:
        async def find_many(self, **kwargs):
            return []

    monkeypatch.setenv("AGENT_API_TOKEN", "test-agent-token")
    monkeypatch.setattr(
        system_controller,
        "prisma",
        SimpleNamespace(actionqueue=EmptyActionQueue()),
    )

    unauthorized = client.get("/api/v1/system/actions")
    authorized = client.get(
        "/api/v1/system/actions",
        headers={"X-Agent-Token": "test-agent-token"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json() == []


def test_login_returns_a_token_without_exposing_the_password_hash(monkeypatch):
    user = SimpleNamespace(
        id="user-id",
        email="admin@example.test",
        organizationId="organization-id",
        role="ADMIN",
        firstName="Test",
        lastName="Admin",
        isActive=True,
        passwordHash="stored-password-hash",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )

    class UserStore:
        async def find_unique(self, **kwargs):
            assert kwargs["where"]["email"] == "admin@example.test"
            return user

    class AuthSessionStore:
        async def create(self, *, data):
            assert data["userId"] == user.id
            assert data["expiresAt"] > datetime.now(timezone.utc)

    class AuditLogStore:
        async def create(self, *, data):
            assert data["action"] == "LOGIN"
            assert data["userId"] == user.id

    class Transaction:
        authsession = AuthSessionStore()
        auditlog = AuditLogStore()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        auth_controller,
        "prisma",
        SimpleNamespace(user=UserStore(), tx=lambda: Transaction()),
    )
    monkeypatch.setattr(auth_controller, "verify_password", lambda plain, hashed: True)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.test", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["expires_in"] == 1800
    assert "passwordHash" not in response.json()["user"]


def test_disabled_user_cannot_log_in(monkeypatch):
    user = SimpleNamespace(
        isActive=False,
        passwordHash="stored-password-hash",
    )

    class UserStore:
        async def find_unique(self, **kwargs):
            return user

    monkeypatch.setattr(auth_controller, "prisma", SimpleNamespace(user=UserStore()))
    monkeypatch.setattr(
        auth_controller,
        "verify_password",
        lambda *_: pytest.fail("Disabled users must be rejected before password verification."),
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "disabled@example.test", "password": "correct-password"},
    )

    assert response.status_code == 401


def test_revoked_jwt_session_is_rejected(monkeypatch):
    session_id = "session-to-revoke"
    user = SimpleNamespace(
        id="user-id",
        email="admin@example.test",
        organizationId="organization-id",
        role="ADMIN",
        isActive=True,
    )
    session = SimpleNamespace(
        id=session_id,
        userId=user.id,
        expiresAt=datetime.now(timezone.utc) + timedelta(minutes=10),
        revokedAt=datetime.now(timezone.utc),
    )

    class AuthSessionStore:
        async def find_unique(self, **kwargs):
            return session

    class UserStore:
        async def find_unique(self, **kwargs):
            return user

    monkeypatch.setattr(
        auth_core,
        "prisma",
        SimpleNamespace(authsession=AuthSessionStore(), user=UserStore()),
    )
    app.dependency_overrides.pop(get_current_user, None)
    token = auth_core.create_access_token({"sub": user.email, "sid": session_id})
    try:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 401


def test_logout_revokes_session_and_records_audit(monkeypatch):
    updated_session = {}
    audit_entry = {}
    session_id = "logout-session"

    class AuthSessionStore:
        async def update(self, *, where, data):
            assert where == {"id": session_id}
            updated_session.update(data)

    class AuditLogStore:
        async def create(self, *, data):
            audit_entry.update(data)

    class Transaction:
        authsession = AuthSessionStore()
        auditlog = AuditLogStore()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        auth_controller,
        "prisma",
        SimpleNamespace(tx=lambda: Transaction()),
    )
    app.dependency_overrides[get_current_user] = lambda: test_user
    token = auth_core.create_access_token(
        {"sub": test_user.email, "sid": session_id}
    )
    try:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 204
    assert updated_session["revokedAt"].tzinfo == timezone.utc
    assert audit_entry["action"] == "LOGOUT"
    assert audit_entry["userId"] == test_user.id


def test_user_listing_is_admin_only():
    viewer = SimpleNamespace(
        id="viewer",
        organizationId="test-organization",
        role="VIEWER",
    )
    app.dependency_overrides[get_current_user] = lambda: viewer
    try:
        response = client.get("/api/v1/users/")
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 403


def test_admin_user_creation_hashes_password_and_uses_current_organization(monkeypatch):
    created_data = {}
    user = SimpleNamespace(
        id="new-user",
        organizationId="test-organization",
        email="operator@example.test",
        firstName=None,
        lastName=None,
        role="OPERATOR",
        isActive=True,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )

    class UserStore:
        async def find_unique(self, **kwargs):
            return None

        async def create(self, *, data):
            created_data.update(data)
            return user

    class AuditLogStore:
        async def create(self, *, data):
            assert data["action"] == "USER_CREATED"
            assert data["resourceId"] == user.id

    class Transaction:
        user = UserStore()
        auditlog = AuditLogStore()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        user_controller,
        "prisma",
        SimpleNamespace(user=UserStore(), tx=lambda: Transaction()),
    )
    monkeypatch.setattr(user_controller, "get_password_hash", lambda value: "hashed-value")

    response = client.post(
        "/api/v1/users/",
        json={
            "email": "operator@example.test",
            "password": "long-enough-password",
            "role": "OPERATOR",
        },
    )

    assert response.status_code == 201
    assert created_data["organizationId"] == test_user.organizationId
    assert created_data["passwordHash"] == "hashed-value"
    assert "password" not in created_data
    assert "passwordHash" not in response.json()


def test_admin_cannot_delete_the_last_active_administrator(monkeypatch):
    target = SimpleNamespace(
        id="last-admin",
        organizationId=test_user.organizationId,
        email="last-admin@example.test",
        role="ADMIN",
        isActive=True,
    )

    class UserStore:
        async def find_first(self, *, where):
            assert where == {
                "id": target.id,
                "organizationId": test_user.organizationId,
            }
            return target

    class TransactionUserStore:
        async def count(self, *, where):
            assert where == {
                "organizationId": test_user.organizationId,
                "role": "ADMIN",
                "isActive": True,
            }
            return 1

        async def update(self, **kwargs):
            pytest.fail("The last active administrator must not be deactivated.")

    class Transaction:
        user = TransactionUserStore()
        auditlog = SimpleNamespace(
            create=lambda **kwargs: pytest.fail("No audit mutation expected.")
        )

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        user_controller,
        "prisma",
        SimpleNamespace(user=UserStore(), tx=lambda: Transaction()),
    )

    response = client.delete(f"/api/v1/users/{target.id}")

    assert response.status_code == 409
    assert "last active administrator" in response.json()["detail"]


def test_audit_logs_are_limited_to_the_current_organization(monkeypatch):
    requested = {}

    class AuditLogStore:
        async def find_many(self, **kwargs):
            requested.update(kwargs)
            return []

    monkeypatch.setattr(
        user_controller,
        "prisma",
        SimpleNamespace(auditlog=AuditLogStore()),
    )

    response = client.get("/api/v1/users/audit-logs?limit=25&skip=5")

    assert response.status_code == 200
    assert response.json() == []
    assert requested["where"] == {"organizationId": test_user.organizationId}
    assert requested["take"] == 25
    assert requested["skip"] == 5


def test_disabling_user_revokes_active_sessions(monkeypatch):
    target = SimpleNamespace(
        id="operator-id",
        organizationId=test_user.organizationId,
        email="operator@example.test",
        role="OPERATOR",
        isActive=True,
    )
    session = SimpleNamespace(id="operator-session")
    revoked = []
    audit_entries = []

    class UserStore:
        async def find_first(self, *, where):
            return target

    class TransactionUserStore:
        async def update(self, *, where, data):
            assert where == {"id": target.id}
            assert data == {"isActive": False}
            return SimpleNamespace(
                id=target.id,
                organizationId=target.organizationId,
                email=target.email,
                role=target.role,
                isActive=False,
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
            )

    class AuthSessionStore:
        async def find_many(self, *, where):
            assert where == {"userId": target.id, "revokedAt": None}
            return [session]

        async def update(self, *, where, data):
            revoked.append((where, data))

    class AuditLogStore:
        async def create(self, *, data):
            audit_entries.append(data)

    class Transaction:
        user = TransactionUserStore()
        authsession = AuthSessionStore()
        auditlog = AuditLogStore()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        user_controller,
        "prisma",
        SimpleNamespace(user=UserStore(), tx=lambda: Transaction()),
    )

    response = client.patch(
        f"/api/v1/users/{target.id}/status",
        json={"isActive": False},
    )

    assert response.status_code == 200
    assert response.json()["isActive"] is False
    assert revoked[0][0] == {"id": session.id}
    assert revoked[0][1]["revokedAt"].tzinfo == timezone.utc
    assert audit_entries[0]["action"] == "USER_DISABLED"


def test_slo_rejects_unknown_metric():
    response = client.post(
        "/api/v1/slos/",
        json={
            "name": "Invalid metric",
            "metric": "network_latency",
            "threshold": 80,
            "targetPercent": 99,
            "windowHours": 24,
        },
    )

    assert response.status_code == 422


def test_slo_rejects_target_above_one_hundred_percent():
    response = client.post(
        "/api/v1/slos/",
        json={
            "name": "Invalid target",
            "metric": "cpu_usage",
            "threshold": 80,
            "targetPercent": 100.1,
            "windowHours": 24,
        },
    )

    assert response.status_code == 422


def test_orchestrator_analyze_mock_payload():
    payload = {
        "cpu_usage": 0.85,
        "sin_hour": 0.5,
        "cos_hour": 0.5,
        "rolling_mean": 0.6,
        "rolling_std": 0.1,
        "lag_1": 0.8,
        "log_text": "CPU overload on frontend service connected to cart database.",
        "deployment_size": 25.0,
        "files_changed": 5.0,
        "code_churn": 120.0,
        "developer_experience": 2.0,
        "deployment_time": 3.0,
        "day_of_week": 5.0,
        "rollback_count": 1.0,
        "previous_incident_count": 2.0,
        "cpu_increase": 0.5,
        "memory_increase": 0.4,
        "network_latency": 250.0,
        "disk_io": 80.0,
        "service_dependency_count": 10.0
    }
    
    response = client.post("/api/v1/ml/analyze", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    analysis = data["analysis"]
    
    assert "anomaly_detection" in analysis
    assert "alert_clustering" in analysis
    assert "root_cause_analysis" in analysis
    assert "risk_prediction" in analysis
    assert "confidence" not in analysis["anomaly_detection"]
    assert "cluster_id" in analysis["alert_clustering"]
    assert "recommended_actions" in analysis
    
    actions = analysis["recommended_actions"]
    assert isinstance(actions, list)


def test_orchestrator_analyze_uses_latest_host_telemetry(monkeypatch):
    telemetry = {
        "cpu": {"usage_percent": 42.0},
        "ram": {"percent": 92.0},
        "disk": {"percent": 95.0},
        "network": {"upload_speed": 10.0, "download_speed": 20.0},
        "processes": [
            {"pid": 0, "name": "System Idle Process", "cpu_percent": 99.0}
        ],
    }
    captured = {}

    class EmptyTelemetryHistory:
        async def find_many(self, **kwargs):
            return []

    monkeypatch.setattr(system_controller, "last_telemetry", telemetry)
    monkeypatch.setattr(
        ml_orchestrator_controller,
        "prisma",
        SimpleNamespace(hosttelemetry=EmptyTelemetryHistory()),
    )

    def analyze(payload):
        captured.update(payload)
        return {"recommended_actions": []}

    monkeypatch.setattr(
        ml_orchestrator_controller.orchestrator_service,
        "analyze_telemetry",
        analyze,
    )

    response = client.post("/api/v1/ml/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert captured["cpu_usage"] == 42.0
    assert "log_text" not in captured
    assert "RAM usage is critically high." in " ".join(
        data["analysis"]["recommended_actions"]
    )
    assert "Free disk space immediately." in " ".join(
        data["analysis"]["recommended_actions"]
    )
    assert "System Idle Process" not in " ".join(
        data["analysis"]["recommended_actions"]
    )


def test_ml_polling_never_queues_process_termination_without_confirmation(monkeypatch):
    telemetry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {"usage_percent": 95.0},
        "ram": {"percent": 50.0},
        "disk": {"percent": 50.0},
        "network": {"upload_speed": 0.0, "download_speed": 0.0},
        "processes": [
            {
                "pid": 1234,
                "name": "worker.exe",
                "cpu_percent": 95.0,
            }
        ],
    }
    settings_reads = []
    action_queue_calls = []

    class TelemetryHistory:
        async def find_many(self, **kwargs):
            return []

    class SystemSettings:
        async def find_first(self, **kwargs):
            settings_reads.append(kwargs)
            return SimpleNamespace(autoRecovery=True)

    class ActionQueue:
        async def find_first(self, **kwargs):
            action_queue_calls.append(("find_first", kwargs))

        async def create(self, **kwargs):
            action_queue_calls.append(("create", kwargs))

    monkeypatch.setattr(system_controller, "last_telemetry", telemetry)
    monkeypatch.setattr(
        ml_orchestrator_controller,
        "prisma",
        SimpleNamespace(
            hosttelemetry=TelemetryHistory(),
            systemsettings=SystemSettings(),
            actionqueue=ActionQueue(),
        ),
    )
    monkeypatch.setattr(
        ml_orchestrator_controller.orchestrator_service,
        "analyze_telemetry",
        lambda payload: {"recommended_actions": []},
    )

    response = client.post("/api/v1/ml/analyze")

    assert response.status_code == 200
    assert "Consider reviewing high-CPU process: worker.exe (PID: 1234)" in (
        response.json()["analysis"]["recommended_actions"]
    )
    assert settings_reads == []
    assert action_queue_calls == []


def test_orchestrator_marks_models_unavailable_without_real_inputs(monkeypatch):
    clustering_calls = []
    monkeypatch.setattr(system_controller, "last_telemetry", None)
    monkeypatch.setattr(
        ml_orchestrator_controller.orchestrator_service.alert_clustering_service,
        "predict",
        lambda text: clustering_calls.append(text),
    )

    response = client.post(
        "/api/v1/ml/analyze",
        json={"cpu_usage": 50, "deployment_size": 12},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["anomaly_detection"]["status"] == "unavailable"
    assert analysis["alert_clustering"]["status"] == "unavailable"
    assert analysis["root_cause_analysis"]["status"] == "unavailable"
    assert analysis["risk_prediction"]["status"] == "unavailable"
    assert "files_changed" in analysis["risk_prediction"]["detail"]
    assert clustering_calls == []


@pytest.mark.parametrize(
    ("age_seconds", "free_memory", "expected_blocked"),
    [
        (0, 3 * 1024**3, False),
        (0, 1 * 1024**3, True),
        (300, 3 * 1024**3, True),
    ],
)
def test_rca_training_preflight_requires_recent_telemetry_and_free_memory(
    monkeypatch, age_seconds, free_memory, expected_blocked
):
    timestamp = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)

    class LatestTelemetry:
        async def find_first(self, **kwargs):
            return SimpleNamespace(
                timestamp=timestamp,
                memoryTotal=8 * 1024**3,
                memoryUsed=8 * 1024**3 - free_memory,
            )

    from app.core import db

    monkeypatch.setattr(db, "prisma", SimpleNamespace(hosttelemetry=LatestTelemetry()))

    reason = asyncio.run(ml_rca_controller.training_blocked_reason())

    assert (reason is not None) is expected_blocked


def test_termination_action_rejects_stale_telemetry(monkeypatch):
    monkeypatch.setattr(
        system_controller,
        "last_telemetry",
        {
            "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=31)).isoformat(),
            "processes": [
                {
                    "pid": 1234,
                    "name": "worker.exe",
                    "cpu_percent": 55,
                    "create_time": 1000.0,
                }
            ],
        },
    )

    with pytest.raises(HTTPException) as error:
        system_controller.get_eligible_process(1234)

    assert error.value.status_code == 409


def test_termination_action_requires_process_identity(monkeypatch):
    monkeypatch.setattr(
        system_controller,
        "last_telemetry",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processes": [
                {"pid": 1234, "name": "worker.exe", "cpu_percent": 55}
            ],
        },
    )

    with pytest.raises(HTTPException) as error:
        system_controller.get_eligible_process(1234)

    assert error.value.status_code == 409


def test_termination_action_rejects_non_finite_cpu_telemetry(monkeypatch):
    monkeypatch.setattr(
        system_controller,
        "last_telemetry",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processes": [
                {
                    "pid": 1234,
                    "name": "worker.exe",
                    "cpu_percent": float("nan"),
                    "create_time": 1000.0,
                }
            ],
        },
    )

    with pytest.raises(HTTPException) as error:
        system_controller.get_eligible_process(1234)

    assert error.value.status_code == 409


def test_queue_termination_action_persists_requester_and_audit(monkeypatch):
    action_data = {}
    audit_data = {}

    class ActionQueue:
        async def create(self, *, data):
            action_data.update(data)
            return SimpleNamespace(id="action-1")

    class AuditLog:
        async def create(self, *, data):
            audit_data.update(data)

    class Transaction:
        actionqueue = ActionQueue()
        auditlog = AuditLog()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        system_controller,
        "prisma",
        SimpleNamespace(tx=lambda: Transaction()),
    )
    process = {"name": "worker.exe"}

    action = asyncio.run(
        system_controller.queue_termination_action(1234, process, 1000.0, test_user)
    )

    assert action.id == "action-1"
    assert action_data["organizationId"] == test_user.organizationId
    assert action_data["requestedByUserId"] == test_user.id
    assert action_data["processName"] == "worker.exe"
    assert action_data["processCreateTime"] == 1000.0
    assert audit_data["action"] == "PROCESS_TERMINATION_QUEUED"
    assert audit_data["resourceId"] == "action-1"
    assert json.loads(audit_data["details"]) == {
        "pid": 1234,
        "processName": "worker.exe",
        "processCreateTime": 1000.0,
    }


def test_viewer_cannot_queue_process_termination():
    viewer = SimpleNamespace(
        id="viewer",
        organizationId="test-organization",
        role="VIEWER",
    )
    app.dependency_overrides[get_current_user] = lambda: viewer
    try:
        response = client.post(
            "/api/v1/system/actions",
            json={"actionType": "TERMINATE_PROCESS", "target": 1234},
        )
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 403


def test_operator_cannot_queue_action_when_auto_recovery_is_disabled(monkeypatch):
    class DisabledSettings:
        async def find_first(self):
            return SimpleNamespace(autoRecovery=False)

    monkeypatch.setattr(
        system_controller,
        "prisma",
        SimpleNamespace(systemsettings=DisabledSettings()),
    )
    operator = SimpleNamespace(
        id="operator",
        organizationId="test-organization",
        role="OPERATOR",
    )
    app.dependency_overrides[get_current_user] = lambda: operator
    try:
        response = client.post(
            "/api/v1/system/actions",
            json={"actionType": "TERMINATE_PROCESS", "target": 1234},
        )
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 409


def test_action_history_is_limited_to_current_organization(monkeypatch):
    captured = {}

    class ActionQueue:
        async def find_many(self, **kwargs):
            captured.update(kwargs)
            return []

    monkeypatch.setattr(
        system_controller,
        "prisma",
        SimpleNamespace(actionqueue=ActionQueue()),
    )
    operator = SimpleNamespace(
        id="operator",
        organizationId="organization-a",
        role="OPERATOR",
    )
    app.dependency_overrides[get_current_user] = lambda: operator
    try:
        response = client.get("/api/v1/system/actions/history?limit=20")
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 200
    assert captured["where"] == {"organizationId": "organization-a"}
    assert captured["take"] == 20
    assert captured["order"] == {"createdAt": "desc"}


def test_action_history_allows_viewers_with_organization_scoping(monkeypatch):
    captured = {}

    class ActionQueue:
        async def find_many(self, **kwargs):
            captured.update(kwargs)
            return []

    monkeypatch.setattr(
        system_controller,
        "prisma",
        SimpleNamespace(actionqueue=ActionQueue()),
    )
    viewer = SimpleNamespace(
        id="viewer",
        organizationId="organization-b",
        role="VIEWER",
    )
    app.dependency_overrides[get_current_user] = lambda: viewer
    try:
        response = client.get("/api/v1/system/actions/history")
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_user

    assert response.status_code == 200
    assert captured["where"] == {"organizationId": "organization-b"}


def test_agent_completion_persists_result_and_audit(monkeypatch):
    completion_data = {}
    audit_data = {}
    pending_action = SimpleNamespace(
        id="action-1",
        status="PENDING",
        organizationId="test-organization",
        requestedByUserId="test-user",
    )

    class ActionQueue:
        async def find_unique(self, **kwargs):
            assert kwargs["where"] == {"id": "action-1"}
            return pending_action

        async def update(self, *, where, data):
            completion_data.update(data)
            return {"id": where["id"], **data}

    class AuditLog:
        async def create(self, *, data):
            audit_data.update(data)

    class Transaction:
        actionqueue = ActionQueue()
        auditlog = AuditLog()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setenv("AGENT_API_TOKEN", "test-agent-token")
    monkeypatch.setattr(
        system_controller,
        "prisma",
        SimpleNamespace(tx=lambda: Transaction()),
    )

    response = client.post(
        "/api/v1/system/actions/action-1/complete",
        headers={"X-Agent-Token": "test-agent-token"},
        json={"status": "FAILED", "result": "Process identity changed."},
    )

    assert response.status_code == 200
    assert completion_data["status"] == "FAILED"
    assert completion_data["result"] == "Process identity changed."
    assert completion_data["completedAt"].tzinfo == timezone.utc
    assert audit_data["action"] == "PROCESS_TERMINATION_COMPLETED"
    assert json.loads(audit_data["details"]) == {
        "status": "FAILED",
        "result": "Process identity changed.",
        "completedBy": "windows-agent",
    }


def test_agent_completion_rejects_unknown_status_before_database_access(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "test-agent-token")
    response = client.post(
        "/api/v1/system/actions/action-1/complete",
        headers={"X-Agent-Token": "test-agent-token"},
        json={"status": "RUNNING", "result": "invalid"},
    )

    assert response.status_code == 422
