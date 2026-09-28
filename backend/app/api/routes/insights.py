from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.models.schemas import AIInsightRequest, AIInsightResponse
from app.services.ai_insights import generate_ai_insights

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.post("", response_model=AIInsightResponse)
async def get_ai_insights(request: AIInsightRequest, settings: Settings = Depends(get_settings)) -> AIInsightResponse:
    if not settings.naver_clova_api_key:
        raise HTTPException(status_code=503, detail="NAVER_CLOVA_API_KEY is not configured on the server.")

    summary = await run_in_threadpool(
        generate_ai_insights, request.portfolio, settings.naver_clova_api_key, request.language
    )
    if summary is None:
        raise HTTPException(status_code=502, detail="CLOVA summary generation failed. See server logs.")
    return AIInsightResponse(summary=summary)
