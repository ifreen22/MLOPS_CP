import os
import sys
import json
import pytest
import numpy as np
import psutil
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

# ML imports
from app.ml_services.alert_clustering import inference, visualization as ac_vis, dataset as ac_dataset
from app.ml_services.alert_clustering.service import AlertClusteringService
from app.ml_services.anomaly_detection.service import AnomalyDetectionService
from app.ml_services.risk_prediction import models as rp_models, visualization as rp_vis
from app.ml_services.orchestrator.service import AIOrchestratorService
from app.telemetry.collectors.windows import WindowsCollector
from app.telemetry.collectors.linux import LinuxCollector
from app.api.v1.controllers import user_controller
from app.schemas.extended import UserCreate, UserUpdate


# ========================================================
# 1. ALERT CLUSTERING INFERENCE & VISUALIZATION
# ========================================================
@pytest.mark.asyncio
async def test_alert_clustering_inference_and_vis(monkeypatch, tmp_path):
    # 1. inference.run_clustering_on_db
    # a. Not loaded and load_model fails -> RuntimeError
    mock_svc = SimpleNamespace(
        is_loaded=False,
        load_model=lambda: None,
        batch_predict=lambda texts: [{"cluster_id": -1, "confidence": 0.5}],
    )
    monkeypatch.setattr(inference, "alert_clustering_service", mock_svc)
    with pytest.raises(RuntimeError):
        await inference.run_clustering_on_db()

    # b. Empty alerts -> returns {alerts: 0, situations_created: 0}
    mock_svc.is_loaded = True
    class MockDbEmpty:
        async def connect(self): pass
        async def disconnect(self): pass
        alert = SimpleNamespace(find_many=AsyncMock(return_value=[]))
    monkeypatch.setattr(inference, "Prisma", lambda: MockDbEmpty())
    res_empty = await inference.run_clustering_on_db()
    assert res_empty["alerts"] == 0

    # c. Alerts with cluster -1 and valid cluster
    class MockAlert:
        def __init__(self, id, title, severity="CRITICAL", serviceId="s1"):
            self.id = id
            self.title = title
            self.severity = severity
            self.description = "alert desc"
            self.serviceId = serviceId

    alerts = [
        MockAlert("a1", "Noise Alert"),
        MockAlert("a2", "Critical Alert", severity="CRITICAL", serviceId="auth"),
        MockAlert("a3", "Dup Alert", severity="LOW", serviceId="billing"),
    ]
    mock_svc.batch_predict = lambda texts: [
        {"cluster_id": -1, "confidence": 0.1},
        {"cluster_id": 1, "confidence": 0.95},
        {"cluster_id": 2, "confidence": 0.8},
    ]

    class MockDbWithAlerts:
        async def connect(self): pass
        async def disconnect(self): pass
        alert = SimpleNamespace(find_many=AsyncMock(return_value=alerts))
        alertcluster = SimpleNamespace(
            find_first=AsyncMock(side_effect=[None, SimpleNamespace(id="exist")]),
            create=AsyncMock(return_value=SimpleNamespace(id="c1")),
        )
        situation = SimpleNamespace(
            create=AsyncMock(return_value=SimpleNamespace(id="sit-1")),
        )

    monkeypatch.setattr(inference, "Prisma", lambda: MockDbWithAlerts())
    res_full = await inference.run_clustering_on_db()
    assert res_full["situations_created"] == 1

    # 2. ac_vis (UMAP, TSNE, generate_all_visualizations)
    mock_umap_mod = SimpleNamespace(
        UMAP=lambda **kw: SimpleNamespace(
            fit_transform=lambda X: np.zeros((len(X), 2))
        )
    )
    monkeypatch.setattr(ac_vis, "umap", mock_umap_mod)
    monkeypatch.setattr(ac_vis, "VIS_DIR", str(tmp_path))
    embeddings = np.random.randn(50, 4)
    labels = [0, 1] * 25
    ac_vis.plot_umap(embeddings, labels, "test_model")
    ac_vis.plot_tsne(embeddings, labels, "test_model")
    ac_vis.generate_all_visualizations(embeddings, {"test_model": labels})


# ========================================================
# 2. DATASET LOGHUB BRANCHES
# ========================================================
def test_alert_clustering_dataset_download(monkeypatch, tmp_path):
    monkeypatch.setattr(ac_dataset, "DATA_DIR", str(tmp_path))
    sample_log = tmp_path / "HDFS_2k.log"
    
    # Mock urlretrieve to write a dummy file
    def mock_retrieve(url, path):
        with open(path, "w") as f:
            f.write("2026-01-01 INFO test line 1\n2026-01-01 ERROR test line 2\n")
    
    monkeypatch.setattr(ac_dataset.urllib.request, "urlretrieve", mock_retrieve)
    df = ac_dataset.download_and_load_dataset()
    assert len(df) == 2


# ========================================================
# 3. ANOMALY DETECTION LOAD_MODEL LSTM & MISSING
# ========================================================
def test_anomaly_load_model_lstm_and_missing(monkeypatch, tmp_path):
    # Missing files -> returns early
    svc = AnomalyDetectionService.__new__(AnomalyDetectionService)
    svc.features = []
    svc.threshold = 0.0
    svc.is_loaded = False
    monkeypatch.setattr("app.ml_services.anomaly_detection.service.MODEL_DIR", str(tmp_path))
    svc.load_model()
    assert svc.is_loaded is False

    # LSTM configuration
    import pickle
    import torch
    from sklearn.preprocessing import StandardScaler
    from app.ml_services.anomaly_detection.models import LSTMAutoencoder

    config_path = tmp_path / "model_config.json"
    scaler_path = tmp_path / "scaler.pkl"
    pt_path = tmp_path / "best_model.pt"

    config_path.write_text(json.dumps({"type": "lstm", "features": ["f1", "f2"], "threshold": 0.05}))
    scaler = StandardScaler()
    scaler.fit(np.zeros((5, 6)))
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    
    lstm_model = LSTMAutoencoder(n_features=6)
    torch.save(lstm_model.state_dict(), pt_path)

    svc.load_model()
    assert svc.is_loaded is True
    assert svc.model_type == "lstm"
    assert svc.threshold == 0.05


# ========================================================
# 4. RISK PREDICTION MODELS & VISUALIZATION BRANCHES
# ========================================================
def test_risk_prediction_models_missing_libs(monkeypatch):
    # Simulate missing lightgbm and catboost
    real_import = __import__
    def fake_import(name, *args, **kwargs):
        if name in ("lightgbm", "catboost"):
            raise ImportError(f"No module named {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    models = rp_models.get_all_models()
    assert "LightGBM" not in models
    assert "CatBoost" not in models


def test_risk_prediction_visualization_branches(monkeypatch, tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    monkeypatch.setattr(rp_vis, "VIS_DIR", str(tmp_path))
    
    y_true = np.array([0, 1, 0, 1, 0, 1])
    y_prob = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7])
    y_pred = np.array([0, 1, 0, 1, 0, 1])

    rp_vis.plot_roc_curve(y_true, y_prob, "TestModel")
    rp_vis.plot_pr_curve(y_true, y_prob, "TestModel")
    rp_vis.plot_confusion_matrix(y_true, y_pred, "TestModel")
    rp_vis.plot_calibration_curve(y_true, y_prob, "TestModel")
    rp_vis.plot_prediction_distribution(y_prob, "TestModel")

    mock_model = MagicMock()
    mock_model.feature_importances_ = np.array([0.1, 0.3, 0.6])
    rp_vis.plot_feature_importance(mock_model, ["f1", "f2", "f3"])

    rp_vis.plot_learning_curve([5, 10], [[0.8, 0.85], [0.85, 0.9]], [[0.7, 0.75], [0.75, 0.8]])

    # SHAP with list output
    X = np.random.randn(20, 5)
    class MockExplainer:
        def __init__(self, m): pass
        def shap_values(self, X): return [X, X] # list of arrays

    mock_shap = SimpleNamespace(
        TreeExplainer=MockExplainer,
        summary_plot=lambda *a, **k: None
    )
    monkeypatch.setattr(rp_vis, "shap", mock_shap)
    rp_vis.plot_shap_summary(MagicMock(), X, ["f1", "f2", "f3", "f4", "f5"])

    # SHAP raising exception
    def failing_explainer(m):
        raise RuntimeError("SHAP boom")
    mock_shap.TreeExplainer = failing_explainer
    rp_vis.plot_shap_summary(MagicMock(), X, ["f1", "f2", "f3", "f4", "f5"])


# ========================================================
# 5. ORCHESTRATOR UNLOADED / FAILED BRANCHES
# ========================================================
def test_orchestrator_service_exceptions_and_actions(monkeypatch):
    # 1. Init exceptions
    with patch("app.ml_services.orchestrator.service.RootCauseAnalysisService", side_effect=RuntimeError("RCA fail")), \
         patch("app.ml_services.orchestrator.service.RiskPredictionService", side_effect=RuntimeError("Risk fail")):
        orch = AIOrchestratorService()
        assert orch.rca_service is None
        assert orch.risk_service is None

    # 2. Analyze telemetry branches
    active_orch = AIOrchestratorService()

    # Unavailable branch: no deployment context
    res1 = active_orch.analyze_telemetry({"anomaly_features": {"value": 50.0}})
    assert res1["risk_prediction"]["status"] == "unavailable"

    # Missing risk fields
    res2 = active_orch.analyze_telemetry({
        "anomaly_features": {"value": 50.0},
        "deployment_size": 100,
    })
    assert "Missing deployment fields" in res2["risk_prediction"]["detail"]

    # Model not loaded / risk_service is None
    active_orch.risk_service = None
    res3 = active_orch.analyze_telemetry({
        "anomaly_features": {"value": 50.0},
        "telemetry_batch": [[0.1]*5]*7,
        "deployment_size": 100,
        "files_changed": 5,
        "code_churn": 20,
        "developer_experience": 3,
        "deployment_time": 14,
        "day_of_week": 2,
        "rollback_count": 0,
        "previous_incident_count": 0,
        "cpu_increase": 5.0,
        "memory_increase": 10.0,
        "network_latency": 2.0,
        "disk_io": 1.0,
        "service_dependency_count": 3,
    })
    assert res3["risk_prediction"]["status"] == "unavailable"

    # Deployment blocked synthesis action
    active_orch.rca_service = SimpleNamespace(
        predict_root_cause=lambda t: {"confidence": 0.9, "root_cause_service": "auth"}
    )
    mock_risk = SimpleNamespace(
        model=MagicMock(),
        predict=lambda f: {"risk_level": "CRITICAL", "recommended_action": "Aborting deployment"}
    )
    active_orch.risk_service = mock_risk
    res4 = active_orch.analyze_telemetry({
        "cpu_usage": 50.0,
        "sin_hour": 0.0,
        "cos_hour": 1.0,
        "rolling_mean": 50.0,
        "rolling_std": 0.0,
        "lag_1": 50.0,
        "topology_batch": [[0.1]*5]*7,
        "deployment_size": 100,
        "files_changed": 5,
        "code_churn": 20,
        "developer_experience": 3,
        "deployment_time": 14,
        "day_of_week": 2,
        "rollback_count": 0,
        "previous_incident_count": 0,
        "cpu_increase": 5.0,
        "memory_increase": 10.0,
        "network_latency": 2.0,
        "disk_io": 1.0,
        "service_dependency_count": 3,
    })
    assert any("Deployment blocked" in a for a in res4["recommended_actions"])
    assert any("Isolate auth service" in a for a in res4["recommended_actions"])


# ========================================================
# 6. COLLECTORS (WINDOWS & LINUX) EXTRA BRANCHES
# ========================================================
def test_collectors_windows_and_linux_branches(monkeypatch):
    # WindowsCollector
    win = WindowsCollector()
    
    # GPU with GPUtil Exception
    mock_gputil_fail = SimpleNamespace(getGPUs=MagicMock(side_effect=RuntimeError("GPU err")))
    monkeypatch.setattr("app.telemetry.collectors.windows.GPUtil", mock_gputil_fail)
    assert win.get_gpu() == []

    # Temperature with wmi Exception
    mock_wmi_fail = SimpleNamespace(WMI=MagicMock(side_effect=RuntimeError("WMI err")))
    monkeypatch.setattr("app.telemetry.collectors.windows.wmi", mock_wmi_fail)
    assert win.get_temperature() == []

    # Temperature with valid wmi
    mock_temp = SimpleNamespace(CurrentTemperature=3100) # 310 K -> 36.85 C
    mock_wmi_ok = SimpleNamespace(WMI=lambda namespace: SimpleNamespace(MSAcpi_ThermalZoneTemperature=lambda: [mock_temp]))
    monkeypatch.setattr("app.telemetry.collectors.windows.wmi", mock_wmi_ok)
    temps = win.get_temperature()
    assert len(temps) == 1
    assert round(temps[0]["temperature"], 1) == 36.9

    # Services with NoSuchProcess
    class MockServiceIter:
        def as_dict(self): raise psutil.NoSuchProcess(pid=999)
    monkeypatch.setattr(psutil, "win_service_iter", lambda: [MockServiceIter()])
    assert win.get_services() == []

    # LinuxCollector
    linux = LinuxCollector()
    monkeypatch.setattr("app.telemetry.collectors.linux.GPUtil", mock_gputil_fail)
    assert linux.get_gpu() == []
    monkeypatch.setattr("app.telemetry.collectors.linux.GPUtil", None)
    assert linux.get_gpu() == []

    # Linux sensors_temperatures
    mock_sensor = SimpleNamespace(label="", current=50.0, high=80.0, critical=100.0)
    monkeypatch.setattr(psutil, "sensors_temperatures", lambda: {"coretemp": [mock_sensor]}, raising=False)
    ltemps = linux.get_temperature()
    assert len(ltemps) == 1
    assert ltemps[0]["label"] == "coretemp"
    assert linux.get_services() == []


# ========================================================
# 7. USER CONTROLLER BRANCHES
# ========================================================
@pytest.mark.asyncio
async def test_user_controller_extended_branches(monkeypatch):
    admin_user = SimpleNamespace(id="adm-1", organizationId="org-1", role="ADMIN")

    # 1. create_user conflict (email exists)
    class MockUserTable:
        async def find_unique(self, where):
            if "email" in where and where["email"] == "dup@example.com":
                return SimpleNamespace(id="u-existing")
            return None
        async def find_many(self, **kw):
            return [admin_user]
        async def find_first(self, where):
            return admin_user

    monkeypatch.setattr(user_controller, "prisma", SimpleNamespace(user=MockUserTable()))

    with pytest.raises(HTTPException) as exc1:
        await user_controller.create_user(
            UserCreate(email="dup@example.com", password="password12345", firstName="A", lastName="B", role="OPERATOR"),
            current_user=admin_user
        )
    assert exc1.value.status_code == 409

    # 2. get_users
    users = await user_controller.get_users(current_user=admin_user)
    assert len(users) == 1

    # 3. update_user removing own admin role -> 409
    with pytest.raises(HTTPException) as exc2:
        await user_controller.update_user(
            "adm-1",
            UserUpdate(role="OPERATOR"),
            current_user=admin_user
        )
    assert exc2.value.status_code == 409

    # 4. update_user with duplicate email -> 409
    target_user = SimpleNamespace(id="other-1", role="OPERATOR", isActive=True)
    class MockUserTable2:
        async def find_first(self, where):
            return target_user
        async def find_unique(self, where):
            return SimpleNamespace(id="someone-else")
    monkeypatch.setattr(user_controller, "prisma", SimpleNamespace(user=MockUserTable2()))

    with pytest.raises(HTTPException) as exc3:
        await user_controller.update_user(
            "other-1",
            UserUpdate(email="dup@example.com"),
            current_user=admin_user
        )
    assert exc3.value.status_code == 409

    # 5. update_user_status when user not found -> 404
    from app.api.v1.controllers.user_controller import UserStatusUpdate
    class MockUserTableEmpty:
        async def find_first(self, where): return None
    monkeypatch.setattr(user_controller, "prisma", SimpleNamespace(user=MockUserTableEmpty()))
    with pytest.raises(HTTPException) as exc4:
        await user_controller.update_user_status("not-found", UserStatusUpdate(isActive=False), current_user=admin_user)
    assert exc4.value.status_code == 404

    # 6. delete_user when user not found -> 404
    with pytest.raises(HTTPException) as exc5:
        await user_controller.delete_user("not-found", current_user=admin_user)
    assert exc5.value.status_code == 404


# ========================================================
# 8. EXTRA COVERAGE BOOST (ALERT SERVICE, AUTH, COLLECTORS)
# ========================================================
@pytest.mark.asyncio
async def test_extra_coverage_boost_95(monkeypatch, tmp_path):
    # 1. AlertClusteringService load_model not exists and train
    svc = AlertClusteringService.__new__(AlertClusteringService)
    svc.is_loaded = False
    monkeypatch.setattr("app.ml_services.alert_clustering.service.MODEL_DIR", str(tmp_path))
    svc.load_model()
    assert svc.is_loaded is False

    # train()
    mock_run_pipe = MagicMock()
    monkeypatch.setattr("app.ml_services.alert_clustering.trainer.run_pipeline", mock_run_pipe)
    svc.train()
    assert mock_run_pipe.called

    # 2. Orchestrator _ensure_loaded and rca_service=None / risk_service.model=None
    orch = AIOrchestratorService()
    orch.anomaly_service = SimpleNamespace(is_loaded=False, load_model=MagicMock(), predict=lambda f: True)
    orch.alert_clustering_service = SimpleNamespace(is_loaded=False, load_model=MagicMock())
    orch._ensure_loaded()
    assert orch.anomaly_service.load_model.called
    assert orch.alert_clustering_service.load_model.called

    # rca_service is None
    orch.rca_service = None
    res_rca_none = orch.analyze_telemetry({"anomaly_features": {"value": 50.0}})
    assert res_rca_none["root_cause_analysis"]["status"] == "unavailable"

    # risk_service.model is None with full deployment context
    orch.rca_service = SimpleNamespace(predict_root_cause=lambda t: {"confidence": 0.5})
    orch.risk_service = SimpleNamespace(model=None)
    res_risk_none = orch.analyze_telemetry({
        "cpu_usage": 50.0,
        "sin_hour": 0.0,
        "cos_hour": 1.0,
        "rolling_mean": 50.0,
        "rolling_std": 0.0,
        "lag_1": 50.0,
        "topology_batch": [[0.1]*5]*7,
        "deployment_size": 100,
        "files_changed": 5,
        "code_churn": 20,
        "developer_experience": 3,
        "deployment_time": 14,
        "day_of_week": 2,
        "rollback_count": 0,
        "previous_incident_count": 0,
        "cpu_increase": 5.0,
        "memory_increase": 10.0,
        "network_latency": 2.0,
        "disk_io": 1.0,
        "service_dependency_count": 3,
    })
    assert "Risk prediction model is not loaded" in res_risk_none["risk_prediction"]["detail"]

    # 3. auth.py get_current_user with inactive user or mismatch email
    from app.core.auth import get_current_user, create_access_token
    now = datetime.now(timezone.utc)
    mock_session = SimpleNamespace(id="s-auth-boost", revokedAt=None, expiresAt=now + timedelta(hours=1), userId="u-inactive")
    mock_inactive_user = SimpleNamespace(id="u-inactive", email="user@test.com", isActive=False)

    class MockAuthDb:
        async def find_unique(self, where):
            if "id" in where and where["id"] == "s-auth-boost": return mock_session
            if "id" in where and where["id"] == "u-inactive": return mock_inactive_user
            return None

    monkeypatch.setattr("app.core.auth.prisma", SimpleNamespace(authsession=MockAuthDb(), user=MockAuthDb()))
    tok = create_access_token({"sub": "user@test.com", "sid": "s-auth-boost"})
    with pytest.raises(HTTPException) as exc_auth:
        await get_current_user(token=tok)
    assert exc_auth.value.status_code == 401

    # 4. WindowsCollector lines 22 & 32 (GPUtil is None and wmi is None)
    win = WindowsCollector()
    monkeypatch.setattr("app.telemetry.collectors.windows.GPUtil", None)
    monkeypatch.setattr("app.telemetry.collectors.windows.wmi", None)
    assert win.get_gpu() == []
    assert win.get_temperature() == []
