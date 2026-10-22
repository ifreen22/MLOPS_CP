from pydantic import BaseModel
from typing import List, Optional

class AlertClusteringRequest(BaseModel):
    log_text: str

class BatchAlertClusteringRequest(BaseModel):
    log_texts: List[str]

class AlertClusterResponse(BaseModel):
    cluster_id: int
    confidence: float
    summary: Optional[str] = None
