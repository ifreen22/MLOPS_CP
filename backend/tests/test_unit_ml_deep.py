import os
import json
import pytest
import numpy as np
import pandas as pd
import torch
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

# 1. Risk Prediction Imports
from app.ml_services.risk_prediction.dataset import generate_risk_dataset
from app.ml_services.risk_prediction.evaluation import evaluate_model
from app.ml_services.risk_prediction.models import get_all_models
from app.ml_services.risk_prediction.visualization import (
    plot_roc_curve,
    plot_pr_curve,
    plot_confusion_matrix,
    plot_calibration_curve,
    plot_prediction_distribution,
    plot_feature_importance,
    plot_learning_curve,
)

# 2. Root Cause Imports
from app.ml_services.root_cause.graph_builder import SockShopGraphBuilder
from app.ml_services.root_cause.models import GCN, GraphSAGE, GAT
from app.ml_services.root_cause.trainer import (
    compute_metrics as compute_rca_metrics,
    train_gnn,
    evaluate_gnn,
)
from app.ml_services.root_cause.visualization import generate_visualizations

# 3. Alert Clustering Imports
from app.ml_services.alert_clustering.clustering import (
    ClusteringModels,
    run_clustering_benchmark,
)
from app.ml_services.alert_clustering.evaluation import evaluate_clusters
from app.ml_services.alert_clustering.visualization import (
    plot_umap,
    plot_tsne,
    generate_all_visualizations,
)
from app.ml_services.alert_clustering.dataset import download_and_load_dataset
from app.ml_services.alert_clustering.models import (
    AlertClusteringRequest,
    BatchAlertClusteringRequest,
    AlertClusterResponse,
)
from app.ml_services.alert_clustering.inference import run_clustering_on_db


# ==========================================
# RISK PREDICTION DEEP TESTS
# ==========================================
def test_risk_dataset_generation():
    df = generate_risk_dataset(n_samples=50, seed=123)
    assert len(df) == 50
    assert "deployment_result" in df.columns
    assert "cpu_increase" in df.columns
    assert set(df["deployment_result"].unique()).issubset({0, 1})


def test_risk_evaluation():
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0])
    y_pred = np.array([0, 1, 0, 0, 1, 0, 1, 0])
    y_prob = np.array([0.1, 0.9, 0.2, 0.4, 0.8, 0.3, 0.7, 0.1])

    metrics = evaluate_model(y_true, y_pred, y_prob)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "fpr" in metrics
    assert "fnr" in metrics
    assert "confusion_matrix" in metrics


def test_risk_all_models():
    models = get_all_models(random_state=42)
    assert "Logistic Regression" in models
    assert "Decision Tree" in models
    assert "Random Forest" in models
    assert "XGBoost" in models
    assert "SVM" in models
    assert "MLP Classifier" in models

    # Fit small dummy data
    X = np.random.randn(20, 5)
    y = np.array([0, 1] * 10)
    for name in ["Logistic Regression", "Decision Tree"]:
        m = models[name]
        m.fit(X, y)
        preds = m.predict(X)
        assert len(preds) == 20


def test_risk_visualizations():
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0])
    y_prob = np.array([0.1, 0.9, 0.2, 0.4, 0.8, 0.3, 0.7, 0.1])
    y_pred = (y_prob > 0.5).astype(int)

    plot_roc_curve(y_true, y_prob, "TestModel")
    plot_pr_curve(y_true, y_prob, "TestModel")
    plot_confusion_matrix(y_true, y_pred, "TestModel")
    plot_calibration_curve(y_true, y_prob, "TestModel")
    plot_prediction_distribution(y_prob, "TestModel")

    from sklearn.tree import DecisionTreeClassifier
    dt = DecisionTreeClassifier()
    dt.fit(np.random.randn(20, 3), np.random.randint(0, 2, 20))
    feature_names = ["f1", "f2", "f3"]
    plot_feature_importance(dt, feature_names)

    from app.ml_services.risk_prediction.visualization import plot_shap_summary
    plot_shap_summary(dt, np.random.randn(20, 3), feature_names)

    # Learning curve with small dummy 2D scores
    train_sizes = np.array([10, 20, 30])
    train_scores = np.random.rand(3, 5)
    test_scores = np.random.rand(3, 5)
    plot_learning_curve(train_sizes, train_scores, test_scores)


# ==========================================
# ROOT CAUSE ANALYSIS DEEP TESTS
# ==========================================
def test_sock_shop_graph_builder_and_fault_dataset():
    builder = SockShopGraphBuilder(seed=42)
    X, y = builder.generate_fault_dataset(num_samples=15)
    assert X.shape == (15, builder.num_nodes, 5)
    assert y.shape == (15,)
    assert y.max().item() < builder.num_nodes


def test_gnn_architectures():
    builder = SockShopGraphBuilder(seed=42)
    num_nodes = builder.num_nodes
    batch_x = torch.randn(4, num_nodes, 5)

    # 1. GCN
    gcn = GCN(num_node_features=5, hidden_dim=16, num_nodes=num_nodes)
    out_gcn = gcn(batch_x, builder.A_norm)
    assert out_gcn.shape == (4, num_nodes)

    # 2. GraphSAGE
    sage = GraphSAGE(num_node_features=5, hidden_dim=16, num_nodes=num_nodes)
    out_sage = sage(batch_x, builder.A_tensor)
    assert out_sage.shape == (4, num_nodes)

    # 3. GAT
    gat = GAT(num_node_features=5, hidden_dim=16, num_nodes=num_nodes)
    out_gat = gat(batch_x, builder.A_tensor)
    assert out_gat.shape == (4, num_nodes)


def test_gnn_trainer_and_metrics():
    builder = SockShopGraphBuilder(seed=42)
    X, y = builder.generate_fault_dataset(num_samples=10)

    gcn = GCN(num_node_features=5, hidden_dim=8, num_nodes=builder.num_nodes)
    train_time = train_gnn(gcn, X, y, builder.A_norm, epochs=2)
    assert train_time >= 0.0

    eval_metrics = evaluate_gnn(gcn, X, builder.A_norm, y)
    assert "top1_acc" in eval_metrics
    assert "top3_acc" in eval_metrics
    assert "mrr" in eval_metrics
    assert "precision" in eval_metrics
    assert "recall" in eval_metrics
    assert "f1" in eval_metrics
    assert "inference_time_ms" in eval_metrics

    # Test visualization
    sage = GraphSAGE(num_node_features=5, hidden_dim=8, num_nodes=builder.num_nodes)
    generate_visualizations(builder, sage, X, y)


# ==========================================
# ALERT CLUSTERING DEEP TESTS
# ==========================================
def test_clustering_models_and_benchmark():
    embeddings = np.random.randn(30, 8)
    labels_dict = run_clustering_benchmark(embeddings)

    assert "HDBSCAN" in labels_dict
    assert "KMeans" in labels_dict
    assert "DBSCAN" in labels_dict
    assert "Agglomerative" in labels_dict
    assert "Spectral" in labels_dict

    for name, labels in labels_dict.items():
        metrics = evaluate_clusters(embeddings, labels)
        assert "n_clusters" in metrics
        assert "n_noise" in metrics


def test_clustering_visualizations():
    embeddings = np.random.randn(50, 4)
    labels = np.random.choice([0, 1, 2], size=50)

    plot_umap(embeddings, labels, "TestUMAP")
    plot_tsne(embeddings, labels, "TestTSNE")
    generate_all_visualizations(embeddings, {"HDBSCAN": labels})


def test_clustering_models_schemas():
    req = AlertClusteringRequest(log_text="Pod failed to start")
    assert req.log_text == "Pod failed to start"

    batch_req = BatchAlertClusteringRequest(log_texts=["log 1", "log 2"])
    assert len(batch_req.log_texts) == 2

    resp = AlertClusterResponse(cluster_id=1, confidence=0.95, summary="Auth cluster")
    assert resp.cluster_id == 1
    assert resp.confidence == 0.95


def test_clustering_dataset_loader(monkeypatch, tmp_path):
    log_file = tmp_path / "HDFS_2k.log"
    log_file.write_text("081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_1\n081109 203519 145 INFO dfs.DataNode$DataXceiver: Receiving block blk_2\n")

    monkeypatch.setattr("app.ml_services.alert_clustering.dataset.DATA_DIR", str(tmp_path))
    df = download_and_load_dataset()
    assert len(df) == 2
    assert "raw_log" in df.columns


@pytest.mark.asyncio
async def test_run_clustering_on_db(monkeypatch):
    from unittest.mock import AsyncMock

    mock_alert1 = SimpleNamespace(id="a1", severity="CRITICAL", title="Out of Memory", description="Pod killed", serviceId="s1")
    mock_alert2 = SimpleNamespace(id="a2", severity="CRITICAL", title="Out of Memory", description="OOM 137", serviceId="s1")

    class MockAlertTable:
        async def find_many(self, **kwargs):
            return [mock_alert1, mock_alert2]

    class MockAlertClusterTable:
        async def find_first(self, **kwargs):
            return None
        async def create(self, **kwargs):
            return SimpleNamespace(id="c1", **kwargs.get("data", {}))

    class MockSituationTable:
        async def create(self, **kwargs):
            return SimpleNamespace(id="sit-1", **kwargs.get("data", {}))

    class MockPrismaClient:
        async def connect(self): pass
        async def disconnect(self): pass
        alert = MockAlertTable()
        alertcluster = MockAlertClusterTable()
        situation = MockSituationTable()

    monkeypatch.setattr("app.ml_services.alert_clustering.inference.Prisma", lambda: MockPrismaClient())

    res = await run_clustering_on_db()
    assert "alerts" in res
    assert "situations_created" in res


def test_run_risk_benchmark_e2e(monkeypatch):
    from sklearn.tree import DecisionTreeClassifier
    monkeypatch.setattr("app.ml_services.risk_prediction.trainer.generate_risk_dataset", lambda **kw: generate_risk_dataset(n_samples=50))
    monkeypatch.setattr("app.ml_services.risk_prediction.trainer.get_all_models", lambda **kw: {"Decision Tree": DecisionTreeClassifier()})
    monkeypatch.setattr("app.ml_services.risk_prediction.trainer.learning_curve", lambda *a, **kw: (np.array([10, 20]), np.ones((2, 3)), np.ones((2, 3))))
    from app.ml_services.risk_prediction.trainer import run_risk_benchmark
    res = run_risk_benchmark()
    assert "FINAL_TEST_EVAL" in res


def test_run_root_cause_benchmark_e2e(monkeypatch):
    from app.ml_services.root_cause.trainer import run_benchmarks
    orig_generate = SockShopGraphBuilder.generate_fault_dataset
    monkeypatch.setattr(SockShopGraphBuilder, "generate_fault_dataset", lambda self, n=20: orig_generate(self, 20))
    res = run_benchmarks()
    assert "GraphSAGE" in res


def test_run_alert_clustering_pipeline_e2e(monkeypatch, tmp_path):
    from app.ml_services.alert_clustering.trainer import run_pipeline
    words = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa",
             "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega"]
    logs = [f"service {w} disconnected database connection timeout" for w in words] + \
           [f"pod {w} crash failed with exception" for w in words]
    dummy_df = pd.DataFrame({"raw_log": logs})
    monkeypatch.setattr("app.ml_services.alert_clustering.trainer.MODEL_DIR", str(tmp_path))
    monkeypatch.setattr("app.ml_services.alert_clustering.trainer.download_and_load_dataset", lambda: dummy_df)
    monkeypatch.setattr("app.ml_services.alert_clustering.trainer.benchmark_embeddings", lambda texts: {
        "all-MiniLM-L6-v2": {"embeddings": np.random.randn(len(texts), 8), "time": 0.01}
    })
    run_pipeline()

