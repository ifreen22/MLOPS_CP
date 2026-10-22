from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.ml_services.risk_prediction.service import RiskPredictionService

router = APIRouter(tags=["ML Risk Prediction"])
risk_service = RiskPredictionService()

class RiskRequest(BaseModel):
    deployment_size: float = 0.0
    files_changed: float = 0.0
    code_churn: float = 0.0
    developer_experience: float = 0.0
    deployment_time: float = 0.0
    day_of_week: float = 0.0
    rollback_count: float = 0.0
    previous_incident_count: float = 0.0
    cpu_increase: float = 0.0
    memory_increase: float = 0.0
    network_latency: float = 0.0
    disk_io: float = 0.0
    service_dependency_count: float = 0.0
    anomaly_score: float = 0.0
    root_cause_score: float = 0.0

@router.get("/ml/risk/health")
def get_health():
    return risk_service.get_health()

@router.post("/ml/risk/predict")
def predict_risk(request: RiskRequest):
    try:
        return risk_service.predict(request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ml/risk/batch")
def predict_risk_batch(requests: List[RiskRequest]):
    try:
        results = []
        for req in requests:
            results.append(risk_service.predict(req.model_dump()))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
