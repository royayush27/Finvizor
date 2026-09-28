"""Pure, framework-agnostic financial math utilities.

Ported from the original Streamlit prototype's module-level helper functions
(calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_beta,
calculate_max_drawdown, calculate_ytd_return, calculate_annualized_return,
perform_adf_test). These were already correctly separated from Streamlit in
the original -- no st.* calls, no session state -- so the logic carries over
essentially unchanged, just with `logger.warning` on the failure paths
instead of being silently absorbed, and a new `calculate_var_cvar` helper
that replaces the ad-hoc VaR/CVaR math that used to live inline inside the
310-line `load_us_stocks_enhanced` function.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


def calculate_ytd_return(hist_data: pd.DataFrame) -> float:
    """Calculate year-to-date return from a Close-indexed price history."""
    try:
        current_year = datetime.now().year
        if hist_data.empty or len(hist_data) < 2:
            return 0.0

        hist_data_indexed = hist_data.copy()
        hist_data_indexed.index = pd.to_datetime(hist_data_indexed.index)

        year_data = hist_data_indexed[hist_data_indexed.index.year == current_year]
        if year_data.empty:
            return 0.0

        start_price = year_data["Close"].iloc[0]
        current_price = year_data["Close"].iloc[-1]
        return ((current_price / start_price) - 1) * 100
    except Exception as e:
        logger.warning(f"Error calculating YTD return: {e}")
        return 0.0


def calculate_annualized_return(hist_data: pd.DataFrame, years: float) -> float:
    """Calculate annualized return over the trailing `years` window."""
    try:
        if hist_data.empty or len(hist_data) < 252 * years:
            return 0.0

        start_price = hist_data["Close"].iloc[-int(252 * years)]
        end_price = hist_data["Close"].iloc[-1]
        return (((end_price / start_price) ** (1 / years)) - 1) * 100
    except Exception as e:
        logger.warning(f"Error calculating {years}Y annualized return: {e}")
        return 0.0


def calculate_max_drawdown(prices: pd.Series) -> Tuple[float, int]:
    """Calculate maximum drawdown (%) and its recovery duration in trading days."""
    try:
        if prices.empty or len(prices) < 2:
            return 0.0, 0
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak * 100
        max_dd = drawdown.min()
        max_dd_start = drawdown.idxmin()
        max_dd_start_idx = prices.index.get_loc(max_dd_start)
        recovery_idx = max_dd_start_idx
        recovery_price = peak.iloc[max_dd_start_idx]
        for i in range(max_dd_start_idx + 1, len(prices)):
            if prices.iloc[i] >= recovery_price:
                recovery_idx = i
                break
        duration = recovery_idx - max_dd_start_idx
        return float(max_dd), int(duration)
    except Exception as e:
        logger.warning(f"Error calculating max drawdown: {e}")
        return 0.0, 0


def calculate_beta(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    """Calculate beta coefficient against a market series (e.g. SPY returns)."""
    try:
        if stock_returns.empty or market_returns.empty:
            return 1.0

        aligned = pd.DataFrame({"stock": stock_returns, "market": market_returns}).dropna()
        if len(aligned) < 50:
            return 1.0

        covariance = aligned["stock"].cov(aligned["market"])
        market_variance = aligned["market"].var()
        if market_variance == 0:
            return 1.0

        beta = covariance / market_variance
        return float(beta) if abs(beta) <= 5 else 1.0
    except Exception as e:
        logger.error(f"Error calculating beta: {e}")
        return 1.0


def calculate_rsi(prices: pd.Series, window: int = 14) -> float:
    """Calculate the latest RSI value (0-100)."""
    try:
        if len(prices) < window + 1:
            return 50.0

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    except Exception as e:
        logger.warning(f"Error calculating RSI: {e}")
        return 50.0


def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[float, float, float]:
    """Calculate (macd_line, macd_signal, macd_histogram) latest values."""
    try:
        if len(prices) < slow_period:
            return 0.0, 0.0, 0.0
        ema_fast = prices.ewm(span=fast_period).mean()
        ema_slow = prices.ewm(span=slow_period).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal_period).mean()
        macd_histogram = macd_line - macd_signal
        return (
            float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0,
            float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else 0.0,
            float(macd_histogram.iloc[-1]) if not pd.isna(macd_histogram.iloc[-1]) else 0.0,
        )
    except Exception as e:
        logger.warning(f"Error calculating MACD: {e}")
        return 0.0, 0.0, 0.0


def calculate_bollinger_bands(prices: pd.Series, period: int = 20) -> Tuple[float, float, float, float]:
    """Calculate (upper, sma, lower, band_width_pct) latest Bollinger Band values."""
    try:
        if len(prices) < period:
            current_price = float(prices.iloc[-1]) if not prices.empty else 0.0
            return current_price * 1.02, current_price, current_price * 0.98, 4.0

        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = (upper - lower) / sma * 100

        return (
            float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else float(prices.iloc[-1]) * 1.02,
            float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else float(prices.iloc[-1]),
            float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else float(prices.iloc[-1]) * 0.98,
            float(width.iloc[-1]) if not pd.isna(width.iloc[-1]) else 4.0,
        )
    except Exception as e:
        logger.warning(f"Error calculating Bollinger Bands: {e}")
        return 0.0, 0.0, 0.0, 4.0


def calculate_var_cvar(returns: pd.Series, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate historical Value-at-Risk and Conditional VaR (%) at the given confidence level."""
    try:
        clean_returns = returns.dropna()
        if len(clean_returns) < 20:
            return 0.0, 0.0
        var = float(np.percentile(clean_returns, (1 - confidence) * 100))
        tail = clean_returns[clean_returns <= var]
        cvar = float(tail.mean()) if not tail.empty else var
        return var, cvar
    except Exception as e:
        logger.warning(f"Error calculating VaR/CVaR: {e}")
        return 0.0, 0.0


def perform_adf_test(series: pd.Series) -> float:
    """Augmented Dickey-Fuller stationarity test -- returns the p-value."""
    try:
        clean = series.dropna()
        if len(clean) < 10:
            return 1.0
        result = adfuller(clean)
        return float(result[1])
    except Exception as e:
        logger.warning(f"ADF test failed for series (length {len(series.dropna())}): {e}")
        return 1.0
