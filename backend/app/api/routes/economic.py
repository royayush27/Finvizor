from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.models.schemas import EconomicSnapshot
from app.services.economic_data import load_economic_snapshot

router = APIRouter(prefix="/api/economic-data", tags=["economic"])


@router.get("", response_model=EconomicSnapshot)
async def get_economic_data(settings: Settings = Depends(get_settings)) -> EconomicSnapshot:
    indicators = await run_in_threadpool(load_economic_snapshot, settings.fred_api_key)
    return EconomicSnapshot(indicators=indicators, fetched_at=datetime.now(timezone.utc))
