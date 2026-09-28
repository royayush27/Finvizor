import numpy as np
import pandas as pd

from app.services.financial_calcs import (
    calculate_bollinger_bands,
    calculate_macd,
    calculate_max_drawdown,
    calculate_rsi,
    calculate_var_cvar,
)


def _rising_price_series(n: int = 300) -> pd.Series:
    return pd.Series(np.linspace(100, 200, n))


def test_rsi_is_bounded_and_high_for_uptrend():
    rsi = calculate_rsi(_rising_price_series())
    assert 0 <= rsi <= 100
    assert rsi > 60  # a steady uptrend should read as strong, not neutral 50


def test_rsi_defaults_to_neutral_on_insufficient_data():
    assert calculate_rsi(pd.Series([100.0, 101.0])) == 50.0


def test_macd_returns_zeros_on_insufficient_data():
    line, signal, hist = calculate_macd(pd.Series([100.0, 101.0]))
    assert (line, signal, hist) == (0.0, 0.0, 0.0)


def test_max_drawdown_is_negative_after_a_drop():
    prices = pd.Series([100.0, 120.0, 80.0, 90.0, 130.0])
    max_dd, duration = calculate_max_drawdown(prices)
    assert max_dd < 0
    assert duration >= 0


def test_bollinger_bands_upper_above_lower():
    upper, sma, lower, width = calculate_bollinger_bands(_rising_price_series())
    assert upper > sma > lower
    assert width > 0


def test_var_cvar_cvar_is_more_extreme_than_var():
    np.random.seed(0)
    returns = pd.Series(np.random.normal(0, 0.02, 500))
    var, cvar = calculate_var_cvar(returns)
    assert cvar <= var  # CVaR (tail mean) should be at or beyond the VaR cutoff


def test_var_cvar_returns_zero_on_too_little_data():
    var, cvar = calculate_var_cvar(pd.Series([0.01, -0.02]))
    assert (var, cvar) == (0.0, 0.0)
