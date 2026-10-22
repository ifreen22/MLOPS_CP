import json
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import mlflow
from mlflow.tracking import MlflowClient

from app.core.db import prisma

logger = logging.getLogger(__name__)

# Determine tracking URI
DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mlflow.db")
)
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{DEFAULT_DB_PATH.replace(os.sep, '/')}")
mlflow.set_tracking_uri(TRACKING_URI)
client = MlflowClient(tracking_uri=TRACKING_URI)

REGISTRY_MODELS = {
    "AnomalyDetector": {
        "task": "Time-Series Anomaly Detection",
        "algorithm": "IsolationForest",
        "champion_type": "isolation_forest",
        "dataset": "NAB AWS CloudWatch ec2_cpu_utilization (4,032 samples, 6 features)",
        "features": ["value", "sin_hour", "cos_hour", "rolling_mean_5", "rolling_std_5", "lag_1"],
        "parameters": {
            "n_estimators": 100,
            "contamination": 0.01,
            "random_state": 42,
            "scaling": "StandardScaler",
        },
        "metrics": {
            "accuracy": 0.9802,
            "precision": 0.2941,
            "recall": 0.5556,
            "f1": 0.3846,
            "roc_auc": 0.9875,
            "pr_auc": 0.3520,
            "inference_latency_ms": 0.0451,
            "training_time_s": 0.2203,
            "fpr": 0.0150,
            "fnr": 0.4444,
        },
        "confusion_matrix": {"tn": 786, "fp": 12, "fn": 4, "tp": 5},
        "artifacts_dir": os.path.abspath(
            os.path.join(os.path.dirname(__file__), "anomaly_detection", "visualizations")
        ),
        "model_file": os.path.abspath(
            os.path.join(os.path.dirname(__file__), "anomaly_detection", "models", "best_model.pkl")
        ),
    },
    "AlertClusterer": {
        "task": "Unsupervised Log/Alert Clustering & Noise Reduction",
        "algorithm": "HDBSCAN",
        "champion_type": "hdbscan",
        "dataset": "HDFS 2k log dataset (2,000 log events, SentenceTransformer embeddings)",
        "features": ["sentence_embedding_dim_384"],
        "parameters": {
            "min_cluster_size": 5,
            "min_samples": 3,
            "metric": "euclidean",
            "embedding_model": "all-MiniLM-L6-v2",
        },
        "metrics": {
            "silhouette": 0.6185,
            "davies_bouldin": 0.6808,
            "calinski_harabasz": 157.78,
            "n_clusters": 14,
            "noise_pct": 5.21,
            "inference_latency_ms": 0.0006,
            "training_time_s": 0.2371,
        },
        "confusion_matrix": None,
        "artifacts_dir": os.path.abspath(
            os.path.join(os.path.dirname(__file__), "alert_clustering", "plots")
        ),
        "model_file": os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "alert_clustering",
                "saved_models",
                "alert_clustering_pipeline.pkl",
            )
        ),
    },
    "RootCauseAnalyzer": {
        "task": "Microservice Graph Neural Network Root Cause Analysis",
        "algorithm": "GraphSAGE",
        "champion_type": "graphsage",
        "dataset": "Sock Shop Microservices Dependency Graph (7 nodes, 5 telemetry metrics/node, 2,000 samples)",
        "features": ["cpu", "memory", "latency", "error_rate", "network_io"],
        "parameters": {
            "hidden_dim": 16,
            "num_nodes": 7,
            "num_features": 5,
            "epochs": 50,
            "learning_rate": 0.01,
            "graph_type": "Directed Dependency DAG",
        },
        "metrics": {
            "top1_accuracy": 1.0,
            "top3_accuracy": 1.0,
            "mrr": 1.0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "inference_latency_ms": 0.0028,
            "training_time_s": 0.3756,
            "memory_mb": 16.1,
        },
        "confusion_matrix": {"classes": 7, "overall_accuracy": 1.0},
        "artifacts_dir": os.path.abspath(
            os.path.join(os.path.dirname(__file__), "root_cause", "visualizations")
        ),
        "model_file": os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "root_cause", "saved_models", "graphsage_model.pt"
            )
        ),
    },
    "ChangeRiskPredictor": {
        "task": "Pre-Deployment & Change Failure Risk Scoring",
        "algorithm": "LGBMClassifier / XGBoost",
        "champion_type": "lightgbm",
        "dataset": "Historical Deployment Changes (5,000 records, 15 change & telemetry signals)",
        "features": [
            "deployment_size", "files_changed", "code_churn", "developer_experience",
            "deployment_time", "day_of_week", "rollback_count", "previous_incident_count",
            "cpu_increase", "memory_increase", "network_latency", "disk_io",
            "service_dependency_count", "anomaly_score", "root_cause_score"
        ],
        "parameters": {
            "n_estimators": 100,
            "learning_rate": 0.05,
            "max_depth": 6,
            "num_leaves": 31,
            "eval_metric": "logloss",
        },
        "metrics": {
            "accuracy": 0.8520,
            "precision": 0.7901,
            "recall": 0.3282,
            "f1": 0.4638,
            "roc_auc": 0.8608,
            "pr_auc": 0.6395,
            "balanced_accuracy": 0.6535,
            "mcc": 0.4459,
            "calibration_error": 0.1086,
            "inference_latency_ms": 0.1093,
            "training_time_s": 1.3715,
            "fpr": 0.0211,
            "fnr": 0.6718,
        },
        "confusion_matrix": {"tn": 788, "fp": 17, "fn": 131, "tp": 64},
        "artifacts_dir": os.path.abspath(
            os.path.join(os.path.dirname(__file__), "risk_prediction", "visualizations")
        ),
        "model_file": os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "risk_prediction", "saved_models", "risk_model.pkl"
            )
        ),
    },
}


def sync_all_models_to_mlflow():
    """
    Synchronizes all 4 trained models, parameters, evaluation metrics,
    and visual artifacts into MLflow tracking and the MLflow Model Registry.
    """
    synced = []
    for model_name, info in REGISTRY_MODELS.items():
        exp_name = f"AIOps_{model_name}"
        mlflow.set_experiment(exp_name)

        with mlflow.start_run(run_name=f"{model_name}_Production_Run") as run:
            run_id = run.info.run_id

            # Log tags
            mlflow.set_tags({
                "model_name": model_name,
                "task": info["task"],
                "algorithm": info["algorithm"],
                "stage": "Production",
                "framework": "scikit-learn/pytorch/lightgbm",
            })

            # Log params
            mlflow.log_params(info["parameters"])
            mlflow.log_param("dataset", info["dataset"])
            mlflow.log_param("num_features", len(info["features"]))

            # Log metrics
            mlflow.log_metrics(info["metrics"])

            # Log artifacts if directory exists
            if os.path.exists(info["artifacts_dir"]):
                for file_name in os.listdir(info["artifacts_dir"]):
                    file_path = os.path.join(info["artifacts_dir"], file_name)
                    if os.path.isfile(file_path):
                        mlflow.log_artifact(file_path, artifact_path="eval_plots")

            # Log model artifact if exists
            if os.path.exists(info["model_file"]):
                mlflow.log_artifact(info["model_file"], artifact_path="model")

            # Register in MLflow Model Registry
            try:
                try:
                    client.create_registered_model(model_name)
                except Exception:
                    pass  # Already registered

                artifact_uri = f"runs:/{run_id}/model"
                mv = client.create_model_version(
                    name=model_name,
                    source=artifact_uri,
                    run_id=run_id,
                    description=f"{info['task']} champion model ({info['algorithm']})",
                )
                try:
                    client.transition_model_version_stage(
                        name=model_name,
                        version=mv.version,
                        stage="Production",
                        archive_existing_versions=True,
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Could not register model {model_name} in registry: {e}")

            synced.append({
                "model_name": model_name,
                "run_id": run_id,
                "algorithm": info["algorithm"],
                "status": "REGISTERED",
                "metrics": info["metrics"],
            })

    return synced


async def sync_experiments_to_db():
    """
    Syncs MLflow experiment runs to the Prisma MLExperiment table.
    """
    synced_records = []
    for model_name, info in REGISTRY_MODELS.items():
        try:
            existing = await prisma.mlexperiment.find_first(
                where={"modelName": model_name}
            )
            data = {
                "modelName": model_name,
                "version": "1.0.0",
                "parameters": json.dumps(info["parameters"]),
                "metrics": json.dumps(info["metrics"]),
                "status": "PRODUCTION",
            }
            if existing:
                record = await prisma.mlexperiment.update(
                    where={"id": existing.id},
                    data=data,
                )
            else:
                record = await prisma.mlexperiment.create(data=data)
            synced_records.append(record)
        except Exception as e:
            logger.warning(f"Could not sync {model_name} to MLExperiment table: {e}")

    return synced_records


def get_model_registry_summary() -> List[Dict[str, Any]]:
    """
    Returns high-level metadata for all models in the registry.
    """
    summary = []
    for model_name, info in REGISTRY_MODELS.items():
        summary.append({
            "model_name": model_name,
            "task": info["task"],
            "algorithm": info["algorithm"],
            "version": "1.0.0",
            "stage": "Production",
            "dataset": info["dataset"],
            "features": info["features"],
            "metrics": info["metrics"],
            "has_confusion_matrix": info["confusion_matrix"] is not None,
            "has_model_artifact": os.path.exists(info["model_file"]),
            "artifacts_dir": info["artifacts_dir"],
        })
    return summary


def get_model_detail(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Returns full metrics, hyperparameters, and artifacts for a model.
    """
    info = REGISTRY_MODELS.get(model_name)
    if not info:
        return None

    # Discover artifact files
    artifacts = []
    if os.path.exists(info["artifacts_dir"]):
        artifacts = os.listdir(info["artifacts_dir"])

    return {
        "model_name": model_name,
        "task": info["task"],
        "algorithm": info["algorithm"],
        "version": "1.0.0",
        "stage": "Production",
        "dataset": info["dataset"],
        "features": info["features"],
        "parameters": info["parameters"],
        "metrics": info["metrics"],
        "confusion_matrix": info["confusion_matrix"],
        "artifacts": artifacts,
        "tracking_uri": TRACKING_URI,
    }
