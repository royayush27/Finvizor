import pandas as pd
import pytest

from app.services.portfolio_builder import PortfolioGenerationError, generate_portfolio
from app.services.stock_universe import StockRecord


def _record(symbol: str, sector: str = "Technology", volatility: float = 25.0, market_cap: float = 5e11) -> StockRecord:
    return StockRecord(
        symbol=symbol,
        name=f"{symbol} Inc.",
        sector=sector,
        industry="Software",
        market_cap=market_cap,
        current_price=100.0,
        ytd_return=5.0,
        one_year_return=12.0,
        three_year_return=10.0,
        five_year_return=9.0,
        volatility_1y=volatility,
        beta=1.1,
        var_95=-3.0,
        cvar_95=-4.5,
        max_drawdown_1y=-15.0,
        rsi=55.0,
        macd_histogram=0.2,
        dividend_yield=1.5,
        pe_ratio=22.0,
        debt_to_equity=40.0,
        roe=18.0,
        revenue_growth=8.0,
        price_history=pd.Series([100.0, 101.0, 102.0]),
        returns_history=pd.Series([0.01, 0.01]),
    )


def test_generate_portfolio_weights_sum_to_one():
    stocks = [_record(s) for s in ["AAA", "BBB", "CCC", "DDD"]]
    predictions = {"AAA": 15.0, "BBB": 8.0, "CCC": 20.0, "DDD": 5.0}

    result = generate_portfolio(
        stocks=stocks,
        predicted_returns=predictions,
        investment_amount=10_000,
        risk_score=50,
        risk_tolerance="Medium Risk (Balanced Growth)",
        num_stocks_target=4,
    )

    assert len(result.holdings) == 4
    assert sum(h.weight for h in result.holdings) == pytest.approx(1.0, abs=1e-6)


def test_generate_portfolio_respects_max_single_position():
    # One stock dominates the score; the cap-and-redistribute loop should still bound it.
    stocks = [_record(s) for s in ["AAA", "BBB", "CCC"]]
    predictions = {"AAA": 100.0, "BBB": 1.0, "CCC": 1.0}

    result = generate_portfolio(
        stocks=stocks,
        predicted_returns=predictions,
        investment_amount=10_000,
        risk_score=50,
        risk_tolerance="Medium Risk (Balanced Growth)",
        num_stocks_target=3,
        max_single_position_pct=0.5,
    )

    assert all(h.weight <= 0.5 + 1e-6 for h in result.holdings)


def test_generate_portfolio_raises_on_empty_input():
    with pytest.raises(PortfolioGenerationError):
        generate_portfolio(
            stocks=[],
            predicted_returns={},
            investment_amount=10_000,
            risk_score=50,
            risk_tolerance="Medium Risk (Balanced Growth)",
        )


def test_generate_portfolio_raises_when_industry_focus_excludes_everything():
    stocks = [_record("AAA", sector="Energy")]
    with pytest.raises(PortfolioGenerationError):
        generate_portfolio(
            stocks=stocks,
            predicted_returns={"AAA": 10.0},
            investment_amount=10_000,
            risk_score=50,
            risk_tolerance="Medium Risk (Balanced Growth)",
            industry_focus=["Healthcare"],
        )


def test_generate_portfolio_news_rejection_filters_symbol():
    stocks = [_record("AAA"), _record("BBB")]
    result = generate_portfolio(
        stocks=stocks,
        predicted_returns={"AAA": 10.0, "BBB": 10.0},
        investment_amount=10_000,
        risk_score=50,
        risk_tolerance="Medium Risk (Balanced Growth)",
        news_rejected_symbols={"AAA"},
    )
    assert all(h.symbol != "AAA" for h in result.holdings)
