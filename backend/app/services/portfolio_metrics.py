"""Historical portfolio statistics; all public return values are percentages."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.stock_universe import StockRecord


def historical_metrics(records: list[StockRecord], weights: list[float]) -> tuple[float, float, str | None]:
    series = {}
    for record in records:
        returns = record.returns_history.copy()
        if isinstance(returns.index, pd.DatetimeIndex):
            # Align exchange sessions by calendar date, including across DST changes.
            returns.index = returns.index.tz_localize(None).normalize()
        series[record.symbol] = returns[~returns.index.duplicated(keep="last")]
    aligned = pd.concat(series, axis=1).replace([np.inf, -np.inf], np.nan).dropna().tail(252)
    if len(aligned) < 2:
        raise ValueError("Insufficient overlapping price history to calculate portfolio risk.")
    w = np.asarray(weights, dtype=float)
    # Buy-and-hold return from the same start date for every holding.
    returns = (1 + aligned).prod().to_numpy() - 1
    historical_return = float(w @ returns * 100)
    covariance = aligned.cov().to_numpy() * 252
    volatility = float(np.sqrt(max(0.0, w @ covariance @ w)) * 100)
    as_of = aligned.index[-1].date().isoformat() if isinstance(aligned.index, pd.DatetimeIndex) else None
    return historical_return, volatility, as_of
