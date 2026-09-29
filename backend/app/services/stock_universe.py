"""US stock universe loading and enrichment.

Ported from the original `load_us_stocks_enhanced()` (a 310-line function that
mixed yfinance fetching, feature computation, and Streamlit progress-bar/
success/error rendering all in one place). Here the data logic is separated
from any UI concern entirely: `load_stock_universe()` is a plain function that
optionally reports progress through a callback, logs failures instead of
`st.error`-ing them, and never touches a UI framework.

Bug fixes applied during the port:
  * The original deduplicated the sector universe with `list(set(...))`,
    whose iteration order is not stable across process restarts -- combined
    with a `[:limit]` slice, that meant a different ~60-stock subset could
    silently be analyzed on different runs. This version uses
    `sorted(set(...))` for a deterministic, reproducible universe.
  * The original called `load_us_stocks_fallback()` in two places as a
    graceful-degradation path, but that function was never defined anywhere
    in the file -- guaranteed NameError if ever hit. `load_stock_universe`
    now degrades honestly instead: it returns whatever subset it could load
    plus the list of failures, and callers decide what "too little data"
    means for them.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from cachetools import TTLCache, cached

from app.services.financial_calcs import (
    calculate_annualized_return,
    calculate_beta,
    calculate_bollinger_bands,
    calculate_macd,
    calculate_max_drawdown,
    calculate_rsi,
    calculate_var_cvar,
    calculate_ytd_return,
)
from app.services.yf_session import get_yf_session

logger = logging.getLogger(__name__)

# Sector -> ticker universe, carried over verbatim from the original prototype.
# Tickers intentionally overlap sectors (e.g. AMZN appears in both Technology-
# adjacent Consumer Discretionary and its own listing) exactly as before.
SECTOR_UNIVERSE: Dict[str, List[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "CRM", "ADBE", "NFLX", "ORCL", "INTC", "CSCO", "AVGO", "QCOM"],
    "Healthcare": ["JNJ", "PFE", "UNH", "ABBV", "TMO", "ABT", "LLY", "BMY", "MRK", "GILD", "AMGN", "ISRG", "VRTX", "REGN", "BIIB"],
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK", "SPGI", "ICE", "CME", "MCO", "TRV", "AIG", "USB"],
    "Consumer Discretionary": ["AMZN", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "TJX", "F", "GM", "BKNG", "LULU", "ETSY", "RCL", "CCL"],
    "Consumer Staples": ["KO", "PEP", "WMT", "PG", "COST", "CL", "KMB", "GIS", "K", "CAG", "CPB", "HSY", "MKC", "SJM", "CHD"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "PXD", "HAL", "BKR", "VLO", "MPC", "PSX", "KMI", "WMB", "OKE"],
    "Industrials": ["BA", "CAT", "GE", "HON", "MMM", "UPS", "RTX", "LMT", "DE", "EMR", "NOC", "FDX", "CSX", "UNP", "NSC"],
    "Materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "DOW", "DD", "PPG", "VMC", "MLM", "NUE", "STLD", "PKG", "IP"],
    "Utilities": ["NEE", "DUK", "SO", "D", "EXC", "XEL", "AEP", "SRE", "PCG", "ED", "EIX", "PPL", "ES", "DTE", "AES"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "SPG", "O", "PSA", "WELL", "AVB", "EQR", "DLR", "BXP", "VTR", "ESS", "MAA"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "CHTR", "TMUS", "ATVI", "EA", "TTWO", "LUMN", "DISH", "FOXA"],
}

# A smaller, liquid, cross-sector fallback set used only if the full universe
# load comes back with too little data to be useful -- a real, defined
# implementation of what the original's dangling `load_us_stocks_fallback()`
# call was supposed to be.
FALLBACK_SYMBOLS: List[str] = sorted({
    "AAPL", "MSFT", "GOOGL", "AMZN", "JPM", "JNJ", "PG", "XOM", "HD", "UNH",
    "KO", "DIS", "BA", "CAT", "NEE",
})

MANUAL_SELECT_SYMBOLS: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "V", "PG", "JNJ",
    "UNH", "HD", "MA", "BAC", "KO", "PEP", "DIS", "NFLX", "ADBE", "CRM",
]

ProgressCallback = Optional[Callable[[int, int, str], None]]


@dataclass
class StockRecord:
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: float
    current_price: float
    ytd_return: float
    one_year_return: float
    three_year_return: float
    five_year_return: float
    volatility_1y: float
    beta: float
    var_95: float
    cvar_95: float
    max_drawdown_1y: float
    rsi: float
    macd_histogram: float
    dividend_yield: float
    pe_ratio: float
    debt_to_equity: float
    roe: float
    revenue_growth: float
    price_history: pd.Series = field(repr=False)
    returns_history: pd.Series = field(repr=False)


def all_symbols() -> List[str]:
    """Deterministic, deduplicated flat symbol list across all sectors."""
    flat: List[str] = []
    for tickers in SECTOR_UNIVERSE.values():
        flat.extend(tickers)
    # Round-robin preserves sector coverage when the caller limits the universe.
    return list(dict.fromkeys(symbol for row in zip(*SECTOR_UNIVERSE.values()) for symbol in row))


def determine_sector(symbol: str) -> str:
    for sector, tickers in SECTOR_UNIVERSE.items():
        if symbol in tickers:
            return sector
    return "Other"


def safe_get_ratio(info: dict, primary_key: str, fallback_key: Optional[str], default_value: float) -> float:
    try:
        value = info.get(primary_key)
        if value is None and fallback_key:
            value = info.get(fallback_key)
        if value is None or not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
            return default_value
        return float(value)
    except (TypeError, ValueError):
        return default_value


def fetch_stock_data_with_retry(symbol: str, max_retries: int = 2, delay: float = 0.5) -> Optional[yf.Ticker]:
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(symbol, session=get_yf_session())
            test_data = ticker.history(period="5d", interval="1d")
            if not test_data.empty:
                return ticker
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
    return None


_spy_cache: TTLCache = TTLCache(maxsize=1, ttl=60 * 60 * 24)  # 1 day, mirrors original


@cached(_spy_cache)
def get_spy_returns() -> pd.Series:
    try:
        spy_hist = yf.Ticker("SPY", session=get_yf_session()).history(period="5y")
        if spy_hist.empty:
            return pd.Series(dtype=float)
        return spy_hist["Close"].pct_change().dropna()
    except Exception as e:
        logger.error(f"Failed to load SPY data: {e}")
        return pd.Series(dtype=float)


def build_stock_record(symbol: str, ticker: yf.Ticker, spy_returns: pd.Series) -> Optional[StockRecord]:
    hist_5y = ticker.history(period="5y", interval="1d")
    hist_1y = ticker.history(period="1y", interval="1d")

    if hist_5y.empty or len(hist_5y) < 253 or hist_1y.empty:
        logger.warning(f"Insufficient history for {symbol}")
        return None

    try:
        info = ticker.info
        if not info or len(info) < 5:
            info = {"longName": symbol, "shortName": symbol}
    except Exception as e:
        logger.warning(f"Info fetch failed for {symbol}: {e}")
        info = {"longName": symbol, "shortName": symbol}

    current_price = float(hist_5y["Close"].iloc[-1])
    returns_1d = hist_5y["Close"].pct_change().dropna()
    if not np.isfinite(current_price) or current_price <= 0 or not np.isfinite(returns_1d).all():
        logger.warning("Invalid price history for %s", symbol)
        return None

    ytd_return = calculate_ytd_return(hist_1y)
    one_year_return = (
        ((hist_1y["Close"].iloc[-1] / hist_1y["Close"].iloc[0]) - 1) * 100 if len(hist_1y) > 1 else 0.0
    )
    three_year_return = calculate_annualized_return(hist_5y, 3)
    five_year_return = calculate_annualized_return(hist_5y, 5)

    volatility_1y = float(returns_1d.tail(252).std() * np.sqrt(252) * 100) if len(returns_1d) >= 252 else 0.0
    var_95, cvar_95 = calculate_var_cvar(returns_1d.tail(252) if len(returns_1d) >= 252 else returns_1d)
    max_dd_1y, _ = calculate_max_drawdown(hist_1y["Close"])
    beta = calculate_beta(returns_1d.tail(504), spy_returns)
    rsi = calculate_rsi(hist_5y["Close"].tail(100))
    _, _, macd_histogram = calculate_macd(hist_5y["Close"])

    # yfinance >=1.x returns dividendYield already as a percent (e.g. 2.5 for 2.5%),
    # unlike the 0.2.x series which returned a fraction (0.025) -- no *100 here.
    dividend_yield = safe_get_ratio(info, "dividendYield", None, 0.0)
    pe_ratio = safe_get_ratio(info, "trailingPE", "forwardPE", 15.0)
    debt_to_equity = safe_get_ratio(info, "debtToEquity", None, 50.0)
    roe = safe_get_ratio(info, "returnOnEquity", None, 0.1) * 100
    revenue_growth = safe_get_ratio(info, "revenueGrowth", None, 0.05) * 100

    return StockRecord(
        symbol=symbol,
        name=info.get("longName", info.get("shortName", symbol)),
        sector=info.get("sector") or determine_sector(symbol),
        industry=info.get("industry", "Unknown"),
        market_cap=safe_get_ratio(info, "marketCap", None, 0.0),
        current_price=current_price,
        ytd_return=ytd_return,
        one_year_return=one_year_return,
        three_year_return=three_year_return,
        five_year_return=five_year_return,
        volatility_1y=volatility_1y,
        beta=beta,
        var_95=var_95,
        cvar_95=cvar_95,
        max_drawdown_1y=max_dd_1y,
        rsi=rsi,
        macd_histogram=macd_histogram,
        dividend_yield=dividend_yield,
        pe_ratio=pe_ratio,
        debt_to_equity=debt_to_equity,
        roe=roe,
        revenue_growth=revenue_growth,
        price_history=hist_5y["Close"],
        returns_history=returns_1d,
    )


def load_stock_universe(
    limit: int = 60,
    progress_callback: ProgressCallback = None,
    industry_focus: Optional[List[str]] = None,
    exclude_industries: Optional[List[str]] = None,
) -> Tuple[List[StockRecord], List[str]]:
    """Load and enrich up to `limit` stocks from the sector universe.

    Returns (records, failed_symbol_messages). Falls back to a smaller,
    known-liquid symbol set if the primary universe yields nothing at all --
    a real implementation of the graceful-degradation path the original
    prototype referenced but never defined.
    """
    # Prioritize the selected sectors before applying the request budget.
    # Actual provider sectors are checked again by portfolio_builder.
    preferred = {s for sector in (industry_focus or []) for s in SECTOR_UNIVERSE.get(sector, [])}
    ordered = all_symbols()
    if preferred:
        ordered = [s for s in ordered if s in preferred] + [s for s in ordered if s not in preferred]
    symbols_to_process = ordered[:limit]
    spy_returns = get_spy_returns()
    if spy_returns.empty:
        logger.warning("Could not load SPY data for beta calculation; beta will default to 1.0.")

    records: List[StockRecord] = []
    failed: List[str] = []

    for i, symbol in enumerate(symbols_to_process):
        if progress_callback:
            progress_callback(i + 1, len(symbols_to_process), symbol)
        try:
            ticker = fetch_stock_data_with_retry(symbol)
            if ticker is None:
                failed.append(f"{symbol}: failed to fetch data")
                continue
            record = build_stock_record(symbol, ticker, spy_returns)
            if record is None:
                failed.append(f"{symbol}: insufficient history")
                continue
            records.append(record)
            time.sleep(0.05)  # gentle rate limiting, same as original
        except Exception as e:
            logger.error(f"Error loading {symbol}: {e}")
            failed.append(f"{symbol}: {str(e)[:100]}")

    if not records:
        logger.warning("Primary universe load returned nothing; falling back to core liquid symbol set.")
        for symbol in FALLBACK_SYMBOLS:
            try:
                ticker = fetch_stock_data_with_retry(symbol)
                if ticker is None:
                    continue
                record = build_stock_record(symbol, ticker, spy_returns)
                if record:
                    records.append(record)
            except Exception as e:
                logger.error(f"Fallback load failed for {symbol}: {e}")

    return records, failed
