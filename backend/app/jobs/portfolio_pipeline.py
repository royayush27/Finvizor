"""Background pipeline that backs POST /api/portfolio/generate.

Runs synchronously inside a thread-pool worker (see api/routes/portfolio.py)
and reports progress through JobManager as it goes -- this is what lets the
frontend show real progress while market-data requests and screening run.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from app.core.config import Settings
from app.jobs.job_manager import job_manager
from app.models.schemas import NewsFilteringSummary, PortfolioRequest, PortfolioResult, StockHolding
from app.services import portfolio_builder, stock_universe
from app.services.portfolio_metrics import historical_metrics
from app.services.risk_scoring import calculate_risk_score
from app.services.news_analyzer import NewsAnalyzer
from app.services.stock_universe import StockRecord, build_stock_record, fetch_stock_data_with_retry, get_spy_returns

logger = logging.getLogger(__name__)


def run_portfolio_job(job_id: str, request: PortfolioRequest, settings: Settings) -> None:
    try:
        job_manager.mark_running(job_id, "Starting portfolio generation...")
        request = request.model_copy(update={"risk_score": calculate_risk_score(request.questionnaire)})
        if request.mode == "user_defined":
            result = _run_user_defined(job_id, request)
        else:
            result = _run_ai_optimized(job_id, request, settings)
        job_manager.mark_completed(job_id, result)
    except portfolio_builder.PortfolioGenerationError as e:
        logger.warning(f"Portfolio generation rejected: {e}")
        job_manager.mark_failed(job_id, str(e))
    except Exception as e:
        logger.exception(f"Portfolio generation job {job_id} failed unexpectedly")
        job_manager.mark_failed(job_id, "Portfolio data could not be processed. Please retry; check the server log if the problem persists.")


def _run_ai_optimized(job_id: str, request: PortfolioRequest, settings: Settings) -> PortfolioResult:
    job_manager.update_progress(job_id, 10, "Loading stock universe...")

    def universe_progress(done: int, total: int, symbol: str) -> None:
        pct = 10 + (done / total) * 30 if total else 10
        job_manager.update_progress(job_id, pct, f"Loading {symbol} ({done}/{total})...")

    records, failed = stock_universe.load_stock_universe(limit=60, progress_callback=universe_progress, industry_focus=request.industry_focus, exclude_industries=request.exclude_industries)
    if not records:
        raise portfolio_builder.PortfolioGenerationError(
            "Unable to load any stock data. This may be a temporary Yahoo Finance rate-limit issue -- try again shortly."
        )
    if failed:
        logger.info(f"{len(failed)} symbols failed to load during universe fetch: {failed[:5]}...")

    news_summary = None
    rejected_symbols: set[str] = set()
    passed_records: List[StockRecord] = records

    if settings.news_api_key:
        job_manager.update_progress(job_id, 40, "Analyzing news sentiment...")

        def news_progress(done: int, total: int, symbol: str) -> None:
            pct = 40 + (done / total) * 20 if total else 40
            job_manager.update_progress(job_id, pct, f"Checking news for {symbol} ({done}/{total})...")

        analyzer = NewsAnalyzer(settings.news_api_key)
        outcome = analyzer.filter_stocks_by_news(records, risk_tolerance=request.news_risk_tolerance, progress_callback=news_progress)
        passed_records = outcome.passed
        rejected_symbols = set(outcome.rejected_symbols)
        news_summary = NewsFilteringSummary(
            total_stocks_analyzed=outcome.total_stocks_analyzed,
            stocks_rejected=len(outcome.rejected_symbols),
            total_articles=outcome.total_articles,
        )
        if not passed_records:
            raise portfolio_builder.PortfolioGenerationError("No stocks passed the news screen. Coverage may be unavailable, or the available headlines exceed your risk tolerance.")
    else:
        job_manager.update_progress(job_id, 60, "Skipping news filtering (no NewsAPI key configured)...")

    job_manager.update_progress(job_id, 85, "Screening historical returns and risk...")
    predicted_returns = {r.symbol: r.one_year_return for r in passed_records}

    result = portfolio_builder.generate_portfolio(
        stocks=passed_records,
        predicted_returns=predicted_returns,
        investment_amount=request.questionnaire.investment_amount,
        risk_score=request.risk_score,
        risk_tolerance=request.questionnaire.risk_tolerance,
        industry_focus=request.industry_focus,
        news_rejected_symbols=rejected_symbols,
        num_stocks_target=request.num_stocks,
        news_summary=news_summary,
        exclude_industries=request.exclude_industries,
    )
    if failed:
        result.warnings.append(f"Market data was unavailable for {len(failed)} symbols; screening used the available stocks.")
    if not settings.news_api_key:
        result.warnings.append("News screening was not applied because the news service is unavailable.")
    job_manager.update_progress(job_id, 100, "Done")
    return result


def _run_user_defined(job_id: str, request: PortfolioRequest) -> PortfolioResult:
    if not request.manual_holdings:
        raise portfolio_builder.PortfolioGenerationError("No manually selected holdings were provided.")

    spy_returns = get_spy_returns()
    holdings: List[StockHolding] = []
    records: List[StockRecord] = []
    total_weight = sum(h.weight for h in request.manual_holdings)

    for i, manual in enumerate(request.manual_holdings):
        job_manager.update_progress(job_id, (i / len(request.manual_holdings)) * 90, f"Loading {manual.symbol}...")
        ticker = fetch_stock_data_with_retry(manual.symbol)
        if ticker is None:
            raise portfolio_builder.PortfolioGenerationError(f"Could not load {manual.symbol}. Your allocation has not been changed. Please retry.")
        record = build_stock_record(manual.symbol, ticker, spy_returns)
        if record is None:
            raise portfolio_builder.PortfolioGenerationError(f"Insufficient history for {manual.symbol}. Your allocation has not been changed.")
        records.append(record)
        normalized_weight = manual.weight / total_weight if total_weight else 0.0
        holdings.append(StockHolding(
            symbol=record.symbol,
            name=record.name,
            sector=record.sector,
            weight=normalized_weight,
            current_price=record.current_price,
            predicted_return=record.one_year_return,
            volatility=record.volatility_1y,
            dividend_yield=record.dividend_yield,
            market_cap=record.market_cap,
        ))

    if not holdings:
        raise portfolio_builder.PortfolioGenerationError("None of the selected symbols could be loaded.")

    sector_totals: Dict[str, float] = {}
    for h in holdings:
        sector_totals[h.sector] = sector_totals.get(h.sector, 0.0) + h.weight

    expected_return, volatility, data_as_of = historical_metrics(records, [h.weight for h in holdings])

    job_manager.update_progress(job_id, 100, "Done")

    return PortfolioResult(
        portfolio_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc),
        investment_amount=request.questionnaire.investment_amount,
        risk_score=request.risk_score,
        expected_annual_return=expected_return,
        portfolio_volatility=volatility,
        holdings=holdings,
        sector_allocation=sector_totals,
        news_filtering_summary=None,
        data_as_of=data_as_of,
        warnings=["Manual allocation: industry, risk and news screens are not applied."],
    )
