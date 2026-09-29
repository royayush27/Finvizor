"""US macroeconomic indicator loading (FRED, with a yfinance-proxy fallback).

Ported from the `USEconomicIndicators` class. The 21-series FRED lookup table
and the yfinance fallback-symbol table are carried over unchanged; the
`st.cache_data`/`st.progress`/`st.warning` calls are replaced with a
`cachetools` TTL cache and plain logging, and the function now returns typed
`app.models.schemas.EconomicIndicator` objects instead of a raw dict.
"""
from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timedelta
from typing import List, Optional

import yfinance as yf
from cachetools import TTLCache, cached
from fredapi import Fred

from app.models.schemas import EconomicIndicator
from app.services.yf_session import get_yf_session

logger = logging.getLogger(__name__)

# 🔹 Interest Rates & Monetary Policy / Inflation / GDP / Labor / Housing /
# Market stress / Consumer / Trade -- unchanged from the original mapping.
FRED_INDICATORS: dict[str, str] = {
    "FEDFUNDS": "Fed Funds Rate",
    "DGS2": "2Y Treasury Yield",
    "DGS10": "10Y Treasury Yield",
    "T10Y2Y": "Yield Curve (10Y-2Y)",
    "CPIAUCSL": "CPI (All Items)",
    "CPILFESL": "Core CPI",
    "GDPDEF": "GDP Deflator",
    "PPIACO": "PPI (All Commodities)",
    "GDP": "GDP (Nominal)",
    "GDPC1": "Real GDP",
    "UNRATE": "Unemployment Rate",
    "PAYEMS": "Nonfarm Payrolls",
    "AWHMAN": "Avg Weekly Hours (Manufacturing)",
    "HOUST": "Housing Starts",
    "PERMIT": "Building Permits",
    "CSUSHPISA": "Case-Shiller Home Price Index",
    "VIXCLS": "VIX Volatility Index",
    "NFCI": "National Financial Conditions Index",
    "RSAFS": "Retail Sales",
    "UMCSENT": "Consumer Sentiment",
    "BOPGSTB": "Trade Balance",
    "DEXUSEU": "USD/EUR Exchange Rate",
}

YFINANCE_FALLBACK_SYMBOLS: dict[str, str] = {
    "^TNX": "10Y Treasury Yield",
    "^FVX": "5Y Treasury Yield",
    "^TYX": "30Y Treasury Yield",
    "^VIX": "VIX Volatility Index",
    "DX-Y.NYB": "US Dollar Index",
    "^GSPC": "S&P 500",
    "GLD": "Gold ETF",
    "TLT": "20+ Year Treasury Bond ETF",
    "HYG": "High Yield Corporate Bond ETF",
}

_economic_cache: TTLCache = TTLCache(maxsize=8, ttl=7200)  # 2 hours, matches original


def _metrics(current: Optional[float], previous: Optional[float], first: Optional[float], pct_std: Optional[float]):
    def change_from(baseline):
        if current is None or baseline is None or baseline == 0:
            return None
        result = (current / baseline - 1) * 100
        return result if math.isfinite(result) else None
    volatility = pct_std * 100 if pct_std is not None and math.isfinite(pct_std) else None
    return change_from(previous), change_from(first), volatility


def _year_start_value(data, year: int) -> Optional[float]:
    """YTD compares the latest observation with the last prior-year observation."""
    if data.empty or data.index[-1].year != year:
        return None
    prior_year = data[data.index.year == year - 1]
    return float(prior_year.iloc[-1]) if not prior_year.empty else None


def _load_from_fred(fred_client: Fred, lookback_years: int) -> List[EconomicIndicator]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_years * 365)
    results: List[EconomicIndicator] = []

    for series_id, name in FRED_INDICATORS.items():
        try:
            data = fred_client.get_series(series_id, observation_start=start_date, observation_end=end_date)
            if data is None or data.empty:
                logger.warning(f"No data returned for {name} ({series_id})")
                continue
            data = data.dropna().sort_index()
            if data.empty:
                continue
            current = float(data.iloc[-1])
            previous = float(data.iloc[-2]) if len(data) > 1 else None
            first = _year_start_value(data, end_date.year)
            pct_std = data.pct_change().std() if len(data) > 1 else None
            change, ytd_change, volatility = _metrics(current, previous, first, pct_std)
            results.append(
                EconomicIndicator(
                    series_id=series_id,
                    name=name,
                    value=current,
                    previous_value=previous,
                    change_pct=change,
                    ytd_change_pct=ytd_change,
                    volatility_pct=volatility,
                    as_of=data.index[-1].strftime("%Y-%m-%d") if len(data.index) else None,
                    source="fred",
                )
            )
            time.sleep(0.05)  # gentle rate limiting, same as original
        except Exception as e:
            logger.warning(f"Could not load FRED series {name} ({series_id}): {e}")
            continue

    return results


def _load_from_yfinance_fallback(lookback_years: int) -> List[EconomicIndicator]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_years * 365)
    results: List[EconomicIndicator] = []

    for symbol, name in YFINANCE_FALLBACK_SYMBOLS.items():
        try:
            hist = yf.Ticker(symbol, session=get_yf_session()).history(start=start_date, end=end_date)
            if hist.empty:
                continue
            prices = hist["Close"].dropna().sort_index()
            if prices.empty:
                continue
            current = float(prices.iloc[-1])
            previous = float(prices.iloc[-2]) if len(prices) > 1 else None
            first = _year_start_value(prices, end_date.year)
            pct_std = prices.pct_change().std() if len(prices) > 1 else None
            change, ytd_change, volatility = _metrics(current, previous, first, pct_std)
            results.append(
                EconomicIndicator(
                    series_id=symbol,
                    name=name,
                    value=current,
                    previous_value=previous,
                    change_pct=change,
                    ytd_change_pct=ytd_change,
                    volatility_pct=volatility,
                    as_of=prices.index[-1].strftime("%Y-%m-%d"),
                    source="yfinance_proxy",
                )
            )
        except Exception as e:
            logger.warning(f"Could not load fallback economic data for {name} ({symbol}): {e}")
            continue

    return results


@cached(_economic_cache)
def load_economic_snapshot(fred_api_key: Optional[str], lookback_years: int = 5) -> List[EconomicIndicator]:
    """Load US macro indicators from FRED, or a yfinance proxy set if no key is configured."""
    if fred_api_key:
        try:
            fred_client = Fred(api_key=fred_api_key)
            indicators = _load_from_fred(fred_client, lookback_years)
            if indicators:
                return indicators
            logger.warning("FRED returned no usable series; falling back to yfinance proxies.")
        except Exception as e:
            logger.warning(f"FRED client initialization failed: {e}. Falling back to yfinance proxies.")
    else:
        logger.info("No FRED API key configured; using yfinance proxy indicators.")

    return _load_from_yfinance_fallback(lookback_years)
