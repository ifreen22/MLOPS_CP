from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
from app.ml_services.root_cause.service import RootCauseAnalysisService
from app.ml_services.orchestrator.service import orchestrator_service
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ML Root Cause Analysis"])
rca_service = RootCauseAnalysisService()
training_status = {"running": False, "error": None}
MINIMUM_FREE_MEMORY_BYTES = 2 * 1024**3
MAX_TELEMETRY_AGE = timedelta(minutes=2)


async def training_blocked_reason():
    from app.core.db import prisma

    telemetry = await prisma.hosttelemetry.find_first(order={"timestamp": "desc"})
    if telemetry is None:
        return "Recent host telemetry is required before RCA training."

    timestamp = telemetry.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - timestamp > MAX_TELEMETRY_AGE:
        return "Recent host telemetry is required before RCA training."

    free_memory = int(telemetry.memoryTotal) - int(telemetry.memoryUsed)
    if free_memory < MINIMUM_FREE_MEMORY_BYTES:
        return (
            "RCA training requires at least 2 GiB of free host memory; "
            f"the latest telemetry sample reports {free_memory / 1024**3:.2f} GiB."
        )
    return None

def train_root_cause_model():
    try:
        from app.ml_services.root_cause.trainer import run_benchmarks

        run_benchmarks()
        rca_service.load_model()
        if orchestrator_service.rca_service:
            orchestrator_service.rca_service.load_model()
        training_status["error"] = None
    except Exception as error:
        training_status["error"] = str(error)
        logger.exception("RCA benchmark training failed")
    finally:
        training_status["running"] = False

class PredictRequest(BaseModel):
    # Shape: (num_nodes, 5 features)
    telemetry_batch: List[List[float]]

@router.get("/ml/root-cause/health")
async def get_health():
    blocked_reason = await training_blocked_reason()
    return {
        **rca_service.get_health(),
        "training": training_status["running"],
        "training_error": training_status["error"],
        "training_available": blocked_reason is None,
        "training_blocked_reason": blocked_reason,
    }

@router.post("/ml/root-cause/train", status_code=202)
async def train_root_cause(background_tasks: BackgroundTasks):
    if training_status["running"]:
        raise HTTPException(status_code=409, detail="RCA model training is already running.")
    blocked_reason = await training_blocked_reason()
    if blocked_reason:
        raise HTTPException(status_code=409, detail=blocked_reason)
    training_status["running"] = True
    training_status["error"] = None
    background_tasks.add_task(train_root_cause_model)
    return {"status": "training", "dataset": "Synthetic Sock Shop fault-injection telemetry (2,000 samples)"}

@router.post("/ml/root-cause/predict")
def predict_root_cause(request: PredictRequest):
    try:
        return rca_service.predict_root_cause(request.telemetry_batch)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

@router.post("/ml/root-cause/batch")
def predict_root_cause_batch(requests: List[PredictRequest]):
    results = []
    for req in requests:
        results.append(rca_service.predict_root_cause(req.telemetry_batch))
    return results
