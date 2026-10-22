import pytest
import numpy as np
import torch
from unittest.mock import MagicMock, patch

from app.ml_services.anomaly_detection.models import LSTMAutoencoder
from app.ml_services.anomaly_detection.service import AnomalyDetectionService
from app.ml_services.risk_prediction.service import RiskPredictionService
from app.ml_services.alert_clustering.service import AlertClusteringService
from app.ml_services.root_cause.service import RootCauseAnalysisService
from app.ml_services.root_cause.models import GraphSAGE
from app.ml_services.root_cause.graph_builder import SockShopGraphBuilder
from app.ml_services.orchestrator.service import AIOrchestratorService
from app.ml_services.registry import (
    get_model_registry_summary,
    get_model_detail,
    sync_all_models_to_mlflow,
    REGISTRY_MODELS
)


# ==========================================
# 1. ANOMALY DETECTION UNIT TESTS
# ==========================================
def test_lstm_autoencoder_forward():
    model = LSTMAutoencoder(n_features=6, hidden_dim=8)
    x = torch.randn(2, 5, 6) # batch=2, seq_len=5, features=6
    out = model(x)
    assert out.shape == x.shape


def test_anomaly_service_prediction():
    service = AnomalyDetectionService()
    if service.is_loaded:
        sample = {
            "value": 50.0,
            "sin_hour": 0.5,
            "cos_hour": 0.86,
            "rolling_mean_5": 50.0,
            "rolling_std_5": 1.2,
            "lag_1": 49.5
        }
        is_anomaly = service.predict(sample)
        assert isinstance(is_anomaly, (bool, np.bool_))


# ==========================================
# 2. RISK PREDICTION UNIT TESTS
# ==========================================
def test_risk_prediction_service():
    service = RiskPredictionService()
    health = service.get_health()
    assert "status" in health

    if service.model is not None:
        payload = {
            "deployment_size": 250,
            "files_changed": 15,
            "code_churn": 45,
            "developer_experience": 0.85,
            "deployment_time": 14.5,
            "day_of_week": 2,
            "rollback_count": 0,
            "previous_incident_count": 1,
            "cpu_increase": 5.2,
            "memory_increase": 8.1,
            "network_latency": 15.0,
            "disk_io": 22.0,
            "service_dependency_count": 4,
            "anomaly_score": 0.12,
            "root_cause_score": 0.05
        }
        res = service.predict(payload)
        assert "risk_score" in res
        assert 0.0 <= res["risk_score"] <= 1.0
        assert "confidence" in res
        assert "recommended_action" in res


# ==========================================
# 3. ALERT CLUSTERING UNIT TESTS
# ==========================================
def test_alert_clustering_service():
    service = AlertClusteringService()
    assert hasattr(service, "is_loaded")


# ==========================================
# 4. ROOT CAUSE GRAPH SAGE UNIT TESTS
# ==========================================
def test_graph_builder_and_graphsage():
    builder = SockShopGraphBuilder(seed=42)
    assert builder.num_nodes == 7
    assert builder.A_tensor.shape == (7, 7)
    assert len(builder.services) == 7

    model = GraphSAGE(num_node_features=5, hidden_dim=16, num_nodes=7)
    batch_x = torch.randn(1, 7, 5)
    out = model(batch_x, builder.A_tensor)
    assert out.shape == (1, 7)


def test_rca_service_health_and_validation():
    service = RootCauseAnalysisService()
    health = service.get_health()
    assert health["model"] == "GraphSAGE"
    assert health["nodes"] == 7

    if service.is_loaded:
        with pytest.raises(ValueError):
            service.predict_root_cause([[0.0] * 5])


# ==========================================
# 5. AI ORCHESTRATOR UNIT TESTS
# ==========================================
def test_ai_orchestrator_service():
    orchestrator = AIOrchestratorService()
    health = orchestrator.get_health()
    assert "status" in health
    assert "services" in health


# ==========================================
# 6. ML REGISTRY UNIT TESTS
# ==========================================
def test_ml_registry_functions():
    summary = get_model_registry_summary()
    assert isinstance(summary, list)
    assert len(summary) >= 4

    names = [m["model_name"] for m in summary]
    assert "AnomalyDetector" in names
    assert "AlertClusterer" in names
    assert "RootCauseAnalyzer" in names
    assert "ChangeRiskPredictor" in names

    ad_detail = get_model_detail("AnomalyDetector")
    assert ad_detail["algorithm"] == "IsolationForest"
    assert "precision" in ad_detail["metrics"]
    assert "recall" in ad_detail["metrics"]
    assert "f1" in ad_detail["metrics"]

    assert get_model_detail("UnknownModel") is None

    synced = sync_all_models_to_mlflow()
    assert len(synced) >= 4
