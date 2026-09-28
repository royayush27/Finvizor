from fastapi import APIRouter

from app.models.schemas import RiskScoreRequest, RiskScoreResponse
from app.services.risk_scoring import calculate_risk_score, get_risk_level

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/score", response_model=RiskScoreResponse)
def score_risk(request: RiskScoreRequest) -> RiskScoreResponse:
    score = calculate_risk_score(request.questionnaire)
    level, color = get_risk_level(score)
    return RiskScoreResponse(risk_score=score, risk_level=level, risk_color=color)
