from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.ml_services.alert_clustering.service import alert_clustering_service
from app.ml_services.alert_clustering.inference import run_clustering_on_db

router = APIRouter(tags=["ML - Alert Clustering"])

class ClusteringRequest(BaseModel):
    log_text: str

class BatchClusteringRequest(BaseModel):
    log_texts: List[str]

@router.get("/ml/cluster/health")
async def cluster_health():
    if not alert_clustering_service.is_loaded:
        alert_clustering_service.load_model()
    return alert_clustering_service.health()

@router.post("/ml/cluster")
async def predict_cluster(payload: ClusteringRequest):
    if not alert_clustering_service.is_loaded:
        alert_clustering_service.load_model()
        if not alert_clustering_service.is_loaded:
            raise HTTPException(status_code=503, detail="Clustering model not loaded or trained yet.")
            
    result = alert_clustering_service.predict(payload.log_text)
    return result

@router.post("/ml/cluster/batch")
async def batch_predict_cluster(payload: BatchClusteringRequest):
    if not alert_clustering_service.is_loaded:
        alert_clustering_service.load_model()
        if not alert_clustering_service.is_loaded:
            raise HTTPException(status_code=503, detail="Clustering model not loaded or trained yet.")
            
    results = alert_clustering_service.batch_predict(payload.log_texts)
    return {"clusters": results}

@router.post("/ml/cluster/train")
async def trigger_training(background_tasks: BackgroundTasks):
    background_tasks.add_task(alert_clustering_service.train)
    return {"status": "Training pipeline initiated in the background."}

@router.post("/ml/cluster/run")
async def run_alert_clustering(background_tasks: BackgroundTasks):
    if not alert_clustering_service.is_loaded:
        alert_clustering_service.load_model()
    if not alert_clustering_service.is_loaded:
        raise HTTPException(status_code=503, detail="Alert clustering model is not loaded.")
    background_tasks.add_task(run_clustering_on_db)
    return {"status": "started", "message": "Clustering open alerts in the background."}

@router.get("/ml/cluster/statistics")
async def get_statistics():
    from app.core.db import prisma

    return {
        "open_alerts": await prisma.alert.count(where={"status": "OPEN"}),
        "open_situations": await prisma.situation.count(where={"status": "OPEN"}),
        "open_clusters": await prisma.alertcluster.count(where={"status": "OPEN"}),
    }
