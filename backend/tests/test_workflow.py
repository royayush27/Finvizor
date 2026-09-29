from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.jobs.job_manager import job_manager
from app.jobs.portfolio_pipeline import _run_user_defined, run_portfolio_job
from app.main import app
from app.models.schemas import PortfolioRequest, Questionnaire
from app.services.news_analyzer import NewsAnalyzer
from app.services.portfolio_builder import PortfolioGenerationError, generate_portfolio
from app.services.portfolio_metrics import historical_metrics
from app.services.risk_scoring import calculate_risk_score
from app.services.stock_universe import all_symbols, SECTOR_UNIVERSE
from tests.test_portfolio_builder import _record


def request(**updates):
    data = dict(mode="user_defined", risk_score=0, questionnaire=dict(
        experience_level="Beginner (0-2 years)", risk_tolerance="Medium Risk (Balanced Growth)",
        investment_timeline="3-5 Years", investment_amount=10000,
        financial_goal="Retirement planning", annual_income="$50K - $100K"),
        manual_holdings=[dict(symbol=" aapl ", weight=0.5), dict(symbol="MSFT", weight=0.5)])
    data.update(updates)
    return PortfolioRequest(**data)


@pytest.mark.parametrize("holdings", [[], [{"symbol": "AAPL", "weight": 0.4}],
    [{"symbol": "AAPL", "weight": 0.5}, {"symbol": "aapl", "weight": 0.5}],
    [{"symbol": "AAPL", "weight": float("nan")}], [{"symbol": "=SUM(1)", "weight": 1}]])
def test_reject_invalid_manual_allocations(holdings):
    with pytest.raises(ValidationError):
        request(manual_holdings=holdings)


@pytest.mark.parametrize("updates", [dict(esg_preference="Strong ESG focus only"),
    dict(target_return=12), dict(industry_focus=["Made up"]),
    dict(industry_focus=["Energy"], exclude_industries=["Energy"])])
def test_reject_unsupported_or_conflicting_constraints(updates):
    with pytest.raises(ValidationError):
        request(**updates)


def test_covariance_accounts_for_diversification_and_aligned_dates():
    a, b = _record("A"), _record("B")
    dates = pd.date_range("2025-01-01", periods=252)
    a.returns_history = pd.Series(np.tile([0.01, -0.01], 126), index=dates)
    b.returns_history = -a.returns_history
    result, volatility, as_of = historical_metrics([a, b], [0.5, 0.5])
    assert volatility == pytest.approx(0, abs=1e-7)
    assert result == pytest.approx(((1.01 * 0.99) ** 126 - 1) * 100)
    assert as_of == dates[-1].date().isoformat()
    b.returns_history.index += pd.Timedelta(days=1000)
    with pytest.raises(ValueError, match="overlapping"):
        historical_metrics([a, b], [0.5, 0.5])


def test_exclusions_and_feasible_position_cap():
    result = generate_portfolio([_record("A"), _record("B", "Financial Services")],
        {"A": 10, "B": 90}, 10000, 50, "Medium Risk (Balanced Growth)", exclude_industries=["Financials"])
    assert [h.symbol for h in result.holdings] == ["A"]
    assert result.position_cap == 1
    assert result.warnings


def test_limited_universe_has_every_sector():
    symbols = set(all_symbols()[:60])
    assert all(symbols & set(group) for group in SECTOR_UNIVERSE.values())


def test_missing_manual_symbol_never_returns_partial_portfolio():
    job = job_manager.create_job()
    with patch("app.jobs.portfolio_pipeline.get_spy_returns", return_value=pd.Series(dtype=float)), \
         patch("app.jobs.portfolio_pipeline.fetch_stock_data_with_retry", side_effect=[object(), None]), \
         patch("app.jobs.portfolio_pipeline.build_stock_record", return_value=_record("AAPL")):
        with pytest.raises(PortfolioGenerationError, match="MSFT"):
            _run_user_defined(job, request())


def test_manual_pipeline_uses_server_risk_score():
    job = job_manager.create_job()
    payload = request()
    with patch("app.jobs.portfolio_pipeline.get_spy_returns", return_value=pd.Series(dtype=float)), \
         patch("app.jobs.portfolio_pipeline.fetch_stock_data_with_retry", return_value=object()), \
         patch("app.jobs.portfolio_pipeline.build_stock_record", side_effect=[_record("AAPL"), _record("MSFT")]):
        run_portfolio_job(job, payload, Settings(_env_file=None))
    status = job_manager.get(job)
    assert status.status == "completed"
    assert sum(h.weight for h in status.result.holdings) == pytest.approx(1)
    assert status.result.risk_score == calculate_risk_score(payload.questionnaire)
    assert status.result.return_basis == "historical"
    client = TestClient(app)
    assert client.get(f"/api/portfolio/jobs/{job}").status_code == 200
    csv = client.get(f"/api/portfolio/jobs/{job}/export.csv")
    assert csv.status_code == 200
    assert "Trailing Return %" in csv.text
    assert "AAPL" in csv.text


def test_news_missing_is_unknown_and_keywords_have_word_boundaries():
    analyzer = NewsAnalyzer(None)
    assert analyzer.analyze_stock_news("AAPL").risk_level == "UNKNOWN"
    assert "fine" not in analyzer.analyze_sentiment("Company refinements improve product quality").flagged_keywords
    assert analyzer.analyze_sentiment("Company faces SEC probe over its accounts").risk_level == "CRITICAL"


def test_api_validation_and_missing_job():
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/portfolio/jobs/missing").status_code == 404
    payload = request().model_dump()
    payload["manual_holdings"] = [{"symbol": "AAPL", "weight": 0.5}]
    assert client.post("/api/portfolio/generate", json=payload).status_code == 422
