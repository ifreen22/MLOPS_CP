import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app.core.db import prisma
from app.ml_services.registry import (
    get_model_registry_summary,
    get_model_detail,
    sync_all_models_to_mlflow,
    sync_experiments_to_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml/registry", tags=["ML Model Registry & Tracking"])


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
async def list_registered_models():
    """
    List all production machine learning models registered in the AIOps Sentinel Model Registry.
    Includes active stage, champion algorithm, dataset, features, and key evaluation metrics.
    """
    return get_model_registry_summary()


@router.get("/experiments", response_model=List[Dict[str, Any]])
async def list_ml_experiments():
    """
    List all tracked ML experiments and audit records from the database.
    """
    records = await prisma.mlexperiment.find_many(order={"createdAt": "desc"})
    return [
        {
            "id": r.id,
            "modelName": r.modelName,
            "version": r.version,
            "status": r.status,
            "parameters": r.parameters,
            "metrics": r.metrics,
            "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        }
        for r in records
    ]


@router.get("/{model_name}")
async def get_model_registry_detail(model_name: str):
    """
    Retrieve full registration details for a model, including hyperparameters,
    metrics (Precision, Recall, F1, ROC-AUC, Latency), confusion matrix, and artifacts.
    """
    detail = get_model_detail(model_name)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found in registry. Available: AnomalyDetector, AlertClusterer, RootCauseAnalyzer, ChangeRiskPredictor",
        )
    return detail


@router.post("/sync")
async def sync_registry():
    """
    Trigger end-to-end synchronization of model artifacts, metrics, and parameters
    into MLflow Tracking, the MLflow Model Registry, and the database MLExperiment table.
    """
    try:
        mlflow_results = sync_all_models_to_mlflow()
        db_results = await sync_experiments_to_db()
        return {
            "status": "success",
            "message": "Synchronized all models to MLflow Tracking, MLflow Model Registry, and database audit logs.",
            "mlflow_registered": [m["model_name"] for m in mlflow_results],
            "database_records_updated": len(db_results),
        }
    except Exception as e:
        logger.exception("Failed to sync MLflow registry")
        raise HTTPException(status_code=500, detail=str(e))
