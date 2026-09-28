import asyncio
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.jobs.job_manager import job_manager
from app.jobs.portfolio_pipeline import run_portfolio_job
from app.models.schemas import JobStatus, PortfolioRequest

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.post("/generate", response_model=JobStatus, status_code=202)
async def generate_portfolio(request: PortfolioRequest, settings: Settings = Depends(get_settings)) -> JobStatus:
    job_id = job_manager.create_job()
    asyncio.create_task(run_in_threadpool(run_portfolio_job, job_id, request, settings))
    return job_manager.get(job_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/jobs/{job_id}/export.csv")
async def export_job_csv(job_id: str) -> StreamingResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "completed" or job.result is None:
        raise HTTPException(status_code=409, detail="Portfolio is not ready yet.")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Symbol", "Name", "Sector", "Weight %", "Current Price", "Predicted Return %", "Volatility %"])
    for h in job.result.holdings:
        writer.writerow([h.symbol, h.name, h.sector, f"{h.weight * 100:.2f}", h.current_price, h.predicted_return, h.volatility])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=my_portfolio.csv"},
    )
