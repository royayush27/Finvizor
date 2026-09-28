from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.models.schemas import NewsArticleSentiment
from app.services.news_analyzer import NewsAnalyzer

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/{symbol}", response_model=NewsArticleSentiment)
async def get_news_sentiment(symbol: str, settings: Settings = Depends(get_settings)) -> NewsArticleSentiment:
    if not settings.news_api_key:
        raise HTTPException(status_code=503, detail="NEWS_API_KEY is not configured on the server.")

    analyzer = NewsAnalyzer(settings.news_api_key)
    analysis = await run_in_threadpool(analyzer.analyze_stock_news, symbol.upper(), 14)

    summary = (
        f"{analysis.articles_analyzed} article(s) analyzed, sentiment {analysis.sentiment_indication.lower()}, "
        f"risk {analysis.risk_level.lower()}"
    )
    return NewsArticleSentiment(
        symbol=analysis.symbol,
        overall_sentiment=analysis.average_sentiment,
        risk_level=analysis.risk_level if analysis.risk_level != "UNKNOWN" else "NONE",
        total_articles=analysis.total_articles,
        summary=summary,
    )
