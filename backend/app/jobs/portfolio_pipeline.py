"""Background pipeline that backs POST /api/portfolio/generate.

Runs synchronously inside a thread-pool worker (see api/routes/portfolio.py)
and reports progress through JobManager as it goes -- this is what lets the
frontend show real progress instead of a frozen page while ~60 yfinance
pulls + ML training + ARIMA fitting happen.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd

from app.core.config import Settings
from app.jobs.job_manager import job_manager
from app.models.schemas import NewsFilteringSummary, PortfolioRequest, PortfolioResult, StockHolding
from app.services import economic_data, portfolio_builder, stock_universe
from app.services.ml_predictor import MLStockPredictor
from app.services.news_analyzer import NewsAnalyzer
from app.services.stock_universe import StockRecord, build_stock_record, fetch_stock_data_with_retry, get_spy_returns

logger = logging.getLogger(__name__)


def run_portfolio_job(job_id: str, request: PortfolioRequest, settings: Settings) -> None:
    try:
        job_manager.mark_running(job_id, "Starting portfolio generation...")
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
        job_manager.mark_failed(job_id, f"Unexpected error: {e}")


def _run_ai_optimized(job_id: str, request: PortfolioRequest, settings: Settings) -> PortfolioResult:
    job_manager.update_progress(job_id, 5, "Loading economic indicators...")
    indicators = economic_data.load_economic_snapshot(settings.fred_api_key)

    job_manager.update_progress(job_id, 10, "Loading stock universe...")

    def universe_progress(done: int, total: int, symbol: str) -> None:
        pct = 10 + (done / total) * 30 if total else 10
        job_manager.update_progress(job_id, pct, f"Loading {symbol} ({done}/{total})...")

    records, failed = stock_universe.load_stock_universe(limit=60, progress_callback=universe_progress)
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
            raise portfolio_builder.PortfolioGenerationError("All stocks were filtered out by news sentiment.")
    else:
        job_manager.update_progress(job_id, 60, "Skipping news filtering (no NewsAPI key configured)...")

    job_manager.update_progress(job_id, 65, "Engineering ML features...")
    predictor = MLStockPredictor()
    features_df = predictor.prepare_features(passed_records, indicators)
    if features_df.empty:
        raise portfolio_builder.PortfolioGenerationError("Failed to prepare features for portfolio generation.")

    job_manager.update_progress(job_id, 80, "Training ML ensemble...")
    records_by_symbol: Dict[str, StockRecord] = {r.symbol: r for r in passed_records}
    targets = pd.Series([records_by_symbol[s].one_year_return for s in features_df["symbol"]])
    predictor.train(features_df, targets)

    job_manager.update_progress(job_id, 90, "Generating predictions and building portfolio...")
    _, confidence_intervals = predictor.predict_with_confidence(features_df)
    predicted_returns = {ci["symbol"]: ci["prediction"] for ci in confidence_intervals}

    features_symbols = set(features_df["symbol"])
    candidate_records = [r for r in passed_records if r.symbol in features_symbols]

    result = portfolio_builder.generate_portfolio(
        stocks=candidate_records,
        predicted_returns=predicted_returns,
        investment_amount=request.questionnaire.investment_amount,
        risk_score=request.risk_score,
        risk_tolerance=request.questionnaire.risk_tolerance,
        industry_focus=request.industry_focus,
        news_rejected_symbols=rejected_symbols,
        num_stocks_target=request.num_stocks,
        news_summary=news_summary,
    )
    job_manager.update_progress(job_id, 100, "Done")
    return result


def _run_user_defined(job_id: str, request: PortfolioRequest) -> PortfolioResult:
    if not request.manual_holdings:
        raise portfolio_builder.PortfolioGenerationError("No manually selected holdings were provided.")

    spy_returns = get_spy_returns()
    holdings: List[StockHolding] = []
    total_weight = sum(h.weight for h in request.manual_holdings)

    for i, manual in enumerate(request.manual_holdings):
        job_manager.update_progress(job_id, (i / len(request.manual_holdings)) * 90, f"Loading {manual.symbol}...")
        ticker = fetch_stock_data_with_retry(manual.symbol)
        if ticker is None:
            logger.warning(f"Could not load data for manually selected symbol {manual.symbol}; skipping.")
            continue
        record = build_stock_record(manual.symbol, ticker, spy_returns)
        if record is None:
            continue
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

    expected_return = sum(h.weight * (h.predicted_return or 0.0) for h in holdings)
    volatility = sum(h.weight * h.volatility for h in holdings)

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
    )
