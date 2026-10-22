from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.ml_services.anomaly_detection.service import anomaly_service

router = APIRouter(tags=["ML - Anomaly Detection"])

class AnomalyFeatures(BaseModel):
    value: float
    sin_hour: float
    cos_hour: float
    rolling_mean_5: float
    rolling_std_5: float
    lag_1: float

class BatchAnomalyFeatures(BaseModel):
    data: List[AnomalyFeatures]

@router.get("/ml/anomaly/health")
async def anomaly_health():
    if not anomaly_service.is_loaded:
        # Try reloading in case training just finished
        anomaly_service.load_model()
    
    return {
        "status": "ready" if anomaly_service.is_loaded else "not_trained",
        "model_type": anomaly_service.model_type
    }

@router.post("/ml/anomaly/predict")
async def predict_anomaly(payload: AnomalyFeatures):
    if not anomaly_service.is_loaded:
        anomaly_service.load_model()
        if not anomaly_service.is_loaded:
            raise HTTPException(status_code=503, detail="Model not loaded or trained yet.")
            
    is_anomaly = anomaly_service.predict(payload.dict())
    return {"is_anomaly": is_anomaly}

@router.post("/ml/anomaly/batch")
async def batch_predict_anomaly(payload: BatchAnomalyFeatures):
    if not anomaly_service.is_loaded:
        anomaly_service.load_model()
        if not anomaly_service.is_loaded:
            raise HTTPException(status_code=503, detail="Model not loaded or trained yet.")
            
    results = [anomaly_service.predict(item.dict()) for item in payload.data]
    return {"anomalies": results}
