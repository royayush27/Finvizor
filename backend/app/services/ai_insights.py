"""NAVER CLOVA HCX-005 portfolio summary generation.

Ported from `summarize_text_with_clova_hcx()` and `generate_ai_insights()`.

Two things fixed during the port:
  * No hardcoded API key. The original had `NAVER_API_KEY = "nv-ec9637..."`
    as a module-level constant used directly in the Authorization header --
    committed straight to source. The key now comes only from
    app.core.config settings.
  * `generate_ai_insights` used to accept a `dict` shaped like
    `{'stocks': DataFrame with a 'Ticker' column, 'stock_allocation': ...,
    'bond_allocation': ...}`, but the only real caller passed the flat
    DataFrame `generate_personalized_portfolio()` actually returns (columns
    `Symbol`, `Weight`, no `stock_allocation`/`bond_allocation` keys at
    all). Every `.get()` silently fell through to a default, so the CLOVA
    summary always described a generic, data-free portfolio. This version
    takes the real `PortfolioResult` schema directly, so there's no shape
    to mismatch.
  * The original `print(f"Response Text: {response.text}")` debug line is
    dropped -- logging a raw API response body is an easy way to leak
    request/response details (including, in some failure modes, key
    material echoed back by the error message) into console/log output.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

import requests

from app.models.schemas import PortfolioResult

logger = logging.getLogger(__name__)

CLOVA_URL = "https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-005"

SYSTEM_PROMPT_KO = (
    "당신은 금융 포트폴리오 분석 전문가입니다. 주어진 포트폴리오 정보를 간결하고 이해하기 쉽게 요약해주세요. "
    "핵심 투자 정보와 리스크 특성, 그리고 투자자에게 도움이 될 수 있는 인사이트를 포함해주세요."
)
SYSTEM_PROMPT_EN = (
    "You are a financial portfolio analysis expert. Summarize the given portfolio information "
    "concisely and clearly, including key investment details, risk characteristics, and useful "
    "insights for the investor."
)


def _build_prompt(portfolio: PortfolioResult, language: str) -> str:
    top_holdings = sorted(portfolio.holdings, key=lambda h: h.weight, reverse=True)[:5]

    if language == "en":
        holdings_text = "\n".join(f"{h.symbol} ({h.name}) - {h.sector} - {h.weight * 100:.1f}%" for h in top_holdings)
        sector_text = "\n".join(f"{sector}: {weight * 100:.1f}%" for sector, weight in portfolio.sector_allocation.items())
        return f"""
        Portfolio Investment Analysis Report

        This portfolio has a risk score of {portfolio.risk_score}/100, with an expected annual
        return of {portfolio.expected_annual_return:.1f}% and a portfolio volatility of
        {portfolio.portfolio_volatility:.1f}%.

        Total investment amount: ${portfolio.investment_amount:,.0f}

        Top holdings:
        {holdings_text}

        Sector allocation:
        {sector_text}
        """

    holdings_text = "\n".join(f"{h.symbol} ({h.name}) - {h.sector} - {h.weight * 100:.1f}%" for h in top_holdings)
    sector_text = "\n".join(f"{sector}: {weight * 100:.1f}%" for sector, weight in portfolio.sector_allocation.items())
    return f"""
    포트폴리오 투자 분석 보고서

    이 포트폴리오는 리스크 점수 {portfolio.risk_score}점을 기록하며, 예상 연간 수익률은 {portfolio.expected_annual_return:.1f}%입니다.
    포트폴리오의 변동성은 {portfolio.portfolio_volatility:.1f}%로 측정되었습니다.

    총 투자 금액은 ${portfolio.investment_amount:,.0f}이며, 다음과 같은 주요 보유 종목들로 구성되어 있습니다:
    {holdings_text}

    섹터별 투자 배분 현황은 다음과 같습니다:
    {sector_text}
    """


def summarize_with_clova(text_to_summarize: str, api_key: str, system_prompt: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-NCP-CLOVASTUDIO-REQUEST-ID": str(uuid.uuid4()),
        "Accept": "application/json",
    }
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"다음 포트폴리오 정보를 분석하여 핵심 내용을 요약해주세요:\n\n{text_to_summarize}"},
        ],
        "topP": 0.8,
        "topK": 0,
        "maxTokens": 512,
        "temperature": 0.3,
        "repetitionPenalty": 1.1,
        "stop": [],
        "seed": 0,
        "includeAiFilters": True,
    }

    try:
        response = requests.post(CLOVA_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()

        result_data = result.get("result", {})
        message = result_data.get("message", {}) if isinstance(result_data, dict) else {}
        summary = message.get("content") or result_data.get("content") or result_data.get("text")
        return str(summary).strip() if summary else None
    except requests.exceptions.HTTPError as e:
        logger.error(f"CLOVA HCX HTTP error: {e}")
        return None
    except Exception as e:
        logger.error(f"CLOVA HCX API error: {e}")
        return None


def generate_ai_insights(portfolio: PortfolioResult, api_key: Optional[str], language: str = "ko") -> Optional[str]:
    if not api_key:
        logger.warning("NAVER_CLOVA_API_KEY not configured; skipping AI insight generation.")
        return None

    system_prompt = SYSTEM_PROMPT_EN if language == "en" else SYSTEM_PROMPT_KO
    prompt_text = _build_prompt(portfolio, language)
    return summarize_with_clova(prompt_text, api_key, system_prompt)
