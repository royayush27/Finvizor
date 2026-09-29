"""Historical stock screening and bounded weight allocation.

Risk preference affects the heuristic score. This is not a validated
forecast or a target-return optimizer. Statistics use shared daily history.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import numpy as np

from app.models.schemas import NewsFilteringSummary, PortfolioResult, StockHolding
from app.services.stock_universe import StockRecord
from app.services.portfolio_metrics import historical_metrics

logger = logging.getLogger(__name__)

SECTOR_ALIAS_MAP: Dict[str, List[str]] = {
    "Technology": ["Technology"],
    "Communication Services": ["Communication Services"],
    "Healthcare": ["Healthcare"],
    "Financials": ["Financials", "Financial Services"],
    "Consumer Discretionary": ["Consumer Discretionary", "Consumer Cyclical"],
    "Consumer Staples": ["Consumer Staples", "Consumer Defensive"],
    "Energy": ["Energy"],
    "Industrials": ["Industrials"],
    "Materials": ["Materials", "Basic Materials"],
    "Real Estate": ["Real Estate"],
    "Utilities": ["Utilities"],
}


class PortfolioGenerationError(Exception):
    """Raised when the portfolio cannot be generated from the given inputs."""


@dataclass
class _Candidate:
    record: StockRecord
    predicted_return: float
    score: float = 0.0
    weight: float = 0.0


def _apply_risk_volatility_filter(candidates: List[_Candidate], risk_tolerance: str) -> List[_Candidate]:
    if "Very Low Risk" in risk_tolerance or "Low Risk" in risk_tolerance:
        return [c for c in candidates if c.record.volatility_1y < 20]
    if "High Risk" in risk_tolerance or "Very High Risk" in risk_tolerance:
        return [c for c in candidates if c.record.volatility_1y > 10]
    return candidates


def _num_stocks_cap(risk_tolerance: str, requested: int) -> int:
    return requested


def generate_portfolio(
    stocks: List[StockRecord],
    predicted_returns: Dict[str, float],
    investment_amount: float,
    risk_score: int,
    risk_tolerance: str,
    industry_focus: Optional[List[str]] = None,
    news_rejected_symbols: Optional[Set[str]] = None,
    num_stocks_target: int = 10,
    max_single_position_pct: float = 0.10,
    news_summary: Optional[NewsFilteringSummary] = None,
    exclude_industries: Optional[List[str]] = None,
) -> PortfolioResult:
    if not stocks:
        raise PortfolioGenerationError("No stock data available for portfolio generation.")

    candidates = [_Candidate(record=s, predicted_return=predicted_returns.get(s.symbol, 0.0)) for s in stocks]

    if exclude_industries:
        excluded = {sector for focus in exclude_industries for sector in SECTOR_ALIAS_MAP.get(focus, [focus])}
        candidates = [c for c in candidates if c.record.sector not in excluded]

    if news_rejected_symbols:
        candidates = [c for c in candidates if c.record.symbol not in news_rejected_symbols]
        if not candidates:
            raise PortfolioGenerationError("All stocks were filtered out by news sentiment.")

    if industry_focus:
        target_sectors: List[str] = []
        for focus in industry_focus:
            target_sectors.extend(SECTOR_ALIAS_MAP.get(focus, [focus]))
        candidates = [c for c in candidates if c.record.sector in target_sectors]
        if not candidates:
            raise PortfolioGenerationError("No stocks match your industry focus criteria.")

    candidates = _apply_risk_volatility_filter(candidates, risk_tolerance)
    if not candidates:
        raise PortfolioGenerationError("No stocks match your risk tolerance criteria after filtering.")

    risk_fraction = min(1.0, max(0.0, risk_score / 100))
    for c in candidates:
        market_cap = max(c.record.market_cap, 1e6)
        c.score = (
            max(0.0, c.predicted_return) * (0.15 + 0.25 * risk_fraction)
            + max(0.0, 100 - c.record.volatility_1y) * (0.4 - 0.2 * risk_fraction)
            + c.record.dividend_yield * 0.1
            + float(np.log(market_cap)) * 0.3
        )

    capped_target = _num_stocks_cap(risk_tolerance, num_stocks_target)
    num_to_select = min(capped_target, len(candidates))
    selected = sorted(candidates, key=lambda c: c.score, reverse=True)[:num_to_select]

    if not selected:
        raise PortfolioGenerationError("No stocks could be selected for the portfolio.")

    total_score = sum(c.score for c in selected)
    if total_score > 0:
        weights = np.array([c.score / total_score for c in selected])
    else:
        weights = np.full(len(selected), 1.0 / len(selected))

    # A fully invested N-stock portfolio cannot have a cap below 1/N.
    # Make the effective limit explicit rather than silently breaking it by renormalizing.
    warnings = []
    if not 0 < max_single_position_pct <= 1:
        raise PortfolioGenerationError("Position cap must be between zero and one.")
    effective_cap = max(max_single_position_pct, 1.0 / len(selected))
    if effective_cap > max_single_position_pct:
        warnings.append(f"With {len(selected)} holdings, the position limit is {effective_cap:.1%}; a 10% limit requires at least 10 holdings.")
    if len(selected) < num_stocks_target:
        warnings.append(f"Only {len(selected)} of the requested {num_stocks_target} stocks passed the available data and screening criteria.")
    max_single_position_pct = effective_cap
    for _ in range(10):
        over_limit = weights > max_single_position_pct
        if not over_limit.any():
            break
        excess = (weights[over_limit] - max_single_position_pct).sum()
        weights[over_limit] = max_single_position_pct
        under_limit = weights < max_single_position_pct
        if under_limit.any():
            capacity = (max_single_position_pct - weights[under_limit]).sum()
            if capacity > 0:
                factor = min(1.0, excess / capacity)
                weights[under_limit] += (max_single_position_pct - weights[under_limit]) * factor

    weights = weights / weights.sum()

    holdings: List[StockHolding] = []
    sector_totals: Dict[str, float] = {}
    for candidate, weight in zip(selected, weights):
        record = candidate.record
        holdings.append(StockHolding(
            symbol=record.symbol,
            name=record.name,
            sector=record.sector,
            weight=float(weight),
            current_price=record.current_price,
            predicted_return=candidate.predicted_return,
            volatility=record.volatility_1y,
            dividend_yield=record.dividend_yield,
            market_cap=record.market_cap,
            score=candidate.score,
        ))
        sector_totals[record.sector] = sector_totals.get(record.sector, 0.0) + float(weight)

    expected_annual_return, portfolio_volatility, data_as_of = historical_metrics(
        [c.record for c in selected], [h.weight for h in holdings]
    )

    return PortfolioResult(
        portfolio_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc),
        investment_amount=investment_amount,
        risk_score=risk_score,
        expected_annual_return=expected_annual_return,
        portfolio_volatility=portfolio_volatility,
        holdings=holdings,
        sector_allocation=sector_totals,
        news_filtering_summary=news_summary,
        warnings=warnings,
        data_as_of=data_as_of,
        position_cap=effective_cap,
    )
