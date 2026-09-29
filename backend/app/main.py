from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import economic, industries, insights, news, portfolio, risk
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Finvizor API",
    description="Historical portfolio research, covariance-based risk analysis, "
    "economic data, and optional news sentiment screening.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(industries.router)
app.include_router(risk.router)
app.include_router(portfolio.router)
app.include_router(news.router)
app.include_router(economic.router)
app.include_router(insights.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok"}
