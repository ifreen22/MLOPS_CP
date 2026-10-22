from fastapi import APIRouter
from typing import List
from app.schemas.extended import RiskScoreCreate, RiskScoreResponse
from app.core.db import prisma
import json

router = APIRouter(prefix="/risk-scores", tags=["RiskScores"])


@router.post("/", response_model=RiskScoreResponse)
async def create_risk_score(data: RiskScoreCreate):
    score = await prisma.riskscore.create(
        data={
            "deploymentId": data.deploymentId,
            "score": data.score,
            "factors": json.dumps(data.factors),
        }
    )
    return RiskScoreResponse(
        id=score.id,
        deploymentId=score.deploymentId,
        score=score.score,
        factors=data.factors,
        createdAt=score.createdAt,
    )


@router.get("/", response_model=List[RiskScoreResponse])
async def get_risk_scores():
    scores = await prisma.riskscore.find_many(order={"createdAt": "desc"})
    return [
        RiskScoreResponse(
            id=score.id,
            deploymentId=score.deploymentId,
            score=score.score,
            factors=_parse_factors(score.factors),
            createdAt=score.createdAt,
        )
        for score in scores
    ]


def _parse_factors(factors: str):
    try:
        return json.loads(factors)
    except json.JSONDecodeError:
        return factors
