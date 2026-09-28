"""News fetching + multi-method sentiment analysis for stock risk filtering.

Ported from the `NewsAnalyzer` class. The sentiment math (TextBlob + VADER +
Loughran-McDonald word lists + keyword scoring, weighted 0.2/0.4/0.3/0.1) and
the risk-level thresholds are carried over unchanged -- that logic was
correct, just entangled with Streamlit progress bars.

Bug fixes applied during the port:
  * The constructor no longer accepts (or falls back to) a hardcoded API key.
    The original had `api_key or "<hardcoded-key>" or st.secrets.get(...)`,
    which meant the hardcoded literal always won via Python's `or`
    short-circuiting -- st.secrets was unreachable dead code. Here the key
    comes only from the caller (which gets it from app.core.config settings).
  * `fetch_newsapi_articles`'s non-200 branch used an undefined `symbol`
    variable inside a method whose parameter is `query` -- NameError on any
    API error response. Fixed to reference `query`.
  * Operates on a list of `StockRecord` (see stock_universe.py) instead of a
    pandas DataFrame, and returns typed results instead of a dict-in-dict
    structure, so the business logic no longer needs to know about
    DataFrame/dict shapes at all.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import requests
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.services.stock_universe import StockRecord

logger = logging.getLogger(__name__)

LM_POSITIVE_WORDS = {"good", "positive", "growth", "gain", "profit", "strong", "increase", "success", "opportunity", "expansion", "breakthrough"}
LM_NEGATIVE_WORDS = {"bad", "negative", "loss", "decline", "risk", "fraud", "crisis", "warning", "drop", "fall", "investigation", "lawsuit"}

NEGATIVE_KEYWORDS = [
    "fraud", "scam", "scandal", "investigation", "lawsuit", "SEC probe",
    "criminal charges", "embezzlement", "corruption", "insider trading",
    "accounting irregularities", "bankruptcy", "default", "whistleblower",
    "regulatory action", "fine", "penalty", "suspended", "delisted",
    "ponzi scheme", "money laundering", "market manipulation", "breach",
    "violation", "misconduct", "illegal", "criminal", "accused",
    "allegations", "indicted", "subpoena",
]

POSITIVE_KEYWORDS = [
    "breakthrough", "innovation", "partnership", "acquisition", "merger",
    "expansion", "growth", "profit", "earnings beat", "revenue growth",
    "new product", "FDA approval", "patent", "award", "recognition",
    "investment", "funding", "IPO", "upgrade", "outperform",
    "stocks worth watching", "next gen", "multibagger",
]

CRITICAL_KEYWORDS = {"fraud", "scam", "criminal charges", "SEC probe", "investigation", "bankruptcy"}

RISK_TOLERANCE_THRESHOLDS: Dict[str, List[str]] = {
    "CONSERVATIVE": ["NONE", "LOW"],
    "MEDIUM": ["NONE", "LOW", "MEDIUM"],
    "AGGRESSIVE": ["NONE", "LOW", "MEDIUM", "HIGH"],
}


@dataclass
class SentimentResult:
    overall_sentiment: float
    sentiment_std: float
    sentiment_indication: str
    negative_score: int
    positive_score: int
    flagged_keywords: List[str]
    risk_level: str
    is_high_risk: bool


@dataclass
class NewsAnalysis:
    symbol: str
    total_articles: int
    articles_analyzed: int
    average_sentiment: float
    sentiment_std: float
    sentiment_indication: str
    risk_level: str
    is_recommended: bool
    flagged_keywords: List[str] = field(default_factory=list)
    risk_reasons: List[str] = field(default_factory=list)


@dataclass
class NewsFilterOutcome:
    passed: List[StockRecord]
    analysis_by_symbol: Dict[str, NewsAnalysis]
    rejected_symbols: List[str]
    total_stocks_analyzed: int
    total_articles: int


ProgressCallback = Optional[Callable[[int, int, str], None]]


class NewsAnalyzer:
    """Comprehensive news sentiment analysis for stock filtering."""

    def __init__(self, api_key: Optional[str]):
        self.news_api_key = api_key
        self.base_url = "https://newsapi.org/v2/"
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self._news_cache: Dict[str, Tuple[datetime, List[dict]]] = {}

    def fetch_newsapi_articles(self, query: str, months_back: int = 1, max_articles: int = 100) -> List[dict]:
        if not self.news_api_key:
            logger.warning("NewsAPI key not configured. Cannot fetch news.")
            return []

        cache_key = f"{query}_{months_back}_{max_articles}"
        if cache_key in self._news_cache:
            cached_time, cached_data = self._news_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < 3600:
                return cached_data

        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)

        params = {
            "q": query,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(100, max_articles),
            "apiKey": self.news_api_key,
        }
        headers = {"User-Agent": "FinvizorBot/1.0"}

        try:
            response = requests.get(f"{self.base_url}everything", params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"NewsAPI error for '{query}': {response.status_code} {response.text}")
                return []

            articles_data = response.json().get("articles", [])
            articles = []
            for article in articles_data:
                try:
                    pub_time = datetime.strptime(article["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, TypeError, KeyError):
                    pub_time = datetime.now()
                articles.append({
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "publisher": (article.get("source") or {}).get("name", ""),
                    "link": article.get("url", ""),
                    "publish_time": pub_time,
                })

            self._news_cache[cache_key] = (datetime.now(), articles)
            return articles
        except requests.exceptions.Timeout:
            logger.error(f"NewsAPI request timed out for query '{query}'.")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news for '{query}': {e}")
            return []

    def get_stock_news(self, symbol: str, days_back: int = 30) -> List[dict]:
        months_back = max(1, days_back // 30)
        return self.fetch_newsapi_articles(symbol, months_back=months_back)

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"http\S+|www.\S+", "", text)
        text = re.sub(r"@\w+|#\w+", "", text)
        return " ".join(text.split()).strip()

    def loughran_mcdonald_sentiment(self, text: str) -> dict:
        words = text.lower().split()
        total_words = len(words)
        if total_words == 0:
            return {"score": 0.0, "positive_ratio": 0.0, "negative_ratio": 0.0}

        positive_count = sum(1 for w in words if w in LM_POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in LM_NEGATIVE_WORDS)
        positive_ratio = positive_count / total_words
        negative_ratio = negative_count / total_words
        return {"score": positive_ratio - negative_ratio, "positive_ratio": positive_ratio, "negative_ratio": negative_ratio}

    def analyze_sentiment(self, text: str) -> SentimentResult:
        try:
            cleaned = self.clean_text(text)
            if not cleaned:
                return self._empty_sentiment_result()

            textblob_polarity = TextBlob(cleaned).sentiment.polarity
            vader_compound = self.vader_analyzer.polarity_scores(cleaned)["compound"]
            lm_result = self.loughran_mcdonald_sentiment(cleaned)
            lm_score = lm_result["score"]

            negative_score = 0
            positive_score = 0
            flagged_keywords: List[str] = []
            text_lower = cleaned.lower()

            for keyword in NEGATIVE_KEYWORDS:
                if keyword in text_lower:
                    negative_score += 2
                    flagged_keywords.append(keyword)
            for keyword in POSITIVE_KEYWORDS:
                if keyword in text_lower:
                    positive_score += 1

            keyword_sentiment = (positive_score - negative_score) / 10 if (positive_score + negative_score) > 0 else 0

            sentiment_scores = [
                textblob_polarity * 0.2,
                vader_compound * 0.4,
                lm_score * 0.3,
                keyword_sentiment * 0.1,
            ]
            mean_sentiment = float(np.mean(sentiment_scores))
            std_sentiment = float(np.std([textblob_polarity, vader_compound, lm_score, keyword_sentiment]))

            if mean_sentiment > 0.05:
                indication = "POSITIVE"
            elif mean_sentiment < -0.05:
                indication = "NEGATIVE"
            else:
                indication = "NEUTRAL"

            risk_level = self._assess_risk_level(negative_score, flagged_keywords, mean_sentiment)

            return SentimentResult(
                overall_sentiment=mean_sentiment,
                sentiment_std=std_sentiment,
                sentiment_indication=indication,
                negative_score=negative_score,
                positive_score=positive_score,
                flagged_keywords=flagged_keywords,
                risk_level=risk_level,
                is_high_risk=risk_level in ("HIGH", "CRITICAL"),
            )
        except Exception as e:
            logger.warning(f"Error in sentiment analysis: {e}")
            return self._empty_sentiment_result()

    @staticmethod
    def _empty_sentiment_result() -> SentimentResult:
        return SentimentResult(0.0, 0.0, "NEUTRAL", 0, 0, [], "UNKNOWN", False)

    @staticmethod
    def _assess_risk_level(negative_score: int, flagged_keywords: List[str], sentiment: float) -> str:
        if any(keyword in flagged_keywords for keyword in CRITICAL_KEYWORDS):
            return "CRITICAL"
        if negative_score >= 4 or sentiment <= -0.5:
            return "HIGH"
        if negative_score >= 2 or sentiment <= -0.2:
            return "MEDIUM"
        if negative_score >= 1 or sentiment <= 0:
            return "LOW"
        return "NONE"

    def analyze_stock_news(self, symbol: str, days_back: int = 30) -> NewsAnalysis:
        try:
            articles = self.get_stock_news(symbol, days_back)
            if not articles:
                return NewsAnalysis(symbol, 0, 0, 0.0, 0.0, "NEUTRAL", "NONE", True)

            results: List[SentimentResult] = []
            all_flagged: List[str] = []
            risk_reasons: List[str] = []

            for article in articles:
                full_text = f"{article.get('title', '')} {article.get('summary', '')}"
                if len(full_text.strip()) < 10:
                    continue
                result = self.analyze_sentiment(full_text)
                results.append(result)
                all_flagged.extend(result.flagged_keywords)
                if result.is_high_risk:
                    risk_reasons.append(f"Article: '{article.get('title', '')[:50]}...' - {result.risk_level} risk")

            if not results:
                return NewsAnalysis(symbol, len(articles), 0, 0.0, 0.0, "NEUTRAL", "NONE", True)

            all_sentiments = [r.overall_sentiment for r in results]
            avg_sentiment = float(np.mean(all_sentiments))
            sentiment_std = float(np.std(all_sentiments))
            indication = "POSITIVE" if avg_sentiment > 0.1 else "NEGATIVE" if avg_sentiment < -0.1 else "NEUTRAL"
            avg_negative_score = float(np.mean([r.negative_score for r in results]))
            overall_risk = self._assess_risk_level(int(round(avg_negative_score)), list(set(all_flagged)), avg_sentiment)
            is_recommended = overall_risk not in ("CRITICAL", "HIGH")

            return NewsAnalysis(
                symbol=symbol,
                total_articles=len(articles),
                articles_analyzed=len(results),
                average_sentiment=avg_sentiment,
                sentiment_std=sentiment_std,
                sentiment_indication=indication,
                risk_level=overall_risk,
                is_recommended=is_recommended,
                flagged_keywords=list(set(all_flagged)),
                risk_reasons=risk_reasons[:3],
            )
        except Exception as e:
            logger.warning(f"Error analyzing news for {symbol}: {e}")
            return NewsAnalysis(symbol, 0, 0, 0.0, 0.0, "NEUTRAL", "UNKNOWN", True)

    def filter_stocks_by_news(
        self,
        stocks: List[StockRecord],
        risk_tolerance: str = "MEDIUM",
        progress_callback: ProgressCallback = None,
    ) -> NewsFilterOutcome:
        if not stocks:
            return NewsFilterOutcome([], {}, [], 0, 0)

        allowed_risks = RISK_TOLERANCE_THRESHOLDS.get(risk_tolerance, RISK_TOLERANCE_THRESHOLDS["MEDIUM"])

        passed: List[StockRecord] = []
        analysis_by_symbol: Dict[str, NewsAnalysis] = {}
        rejected: List[str] = []
        total_articles = 0

        for i, stock in enumerate(stocks):
            if progress_callback:
                progress_callback(i + 1, len(stocks), stock.symbol)

            analysis = self.analyze_stock_news(stock.symbol, days_back=60)
            analysis_by_symbol[stock.symbol] = analysis
            total_articles += analysis.total_articles

            if analysis.risk_level in allowed_risks and analysis.is_recommended:
                passed.append(stock)
            else:
                rejected.append(stock.symbol)

            time.sleep(0.1)  # gentle rate limiting, same as original

        return NewsFilterOutcome(
            passed=passed,
            analysis_by_symbol=analysis_by_symbol,
            rejected_symbols=rejected,
            total_stocks_analyzed=len(stocks),
            total_articles=total_articles,
        )
