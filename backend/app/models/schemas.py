"""Pydantic request/response models shared by every API route.

This is the single contract the frontend is built against. Nothing in
app/services/* should leak framework-specific shapes (DataFrames, st.*
objects) past this boundary -- routes convert to/from these models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ExperienceLevel = Literal[
    "Beginner (0-2 years)",
    "Intermediate (2-5 years)",
    "Advanced (5-10 years)",
    "Expert (10+ years)",
]

RiskTolerance = Literal[
    "Very Low Risk (Capital Preservation)",
    "Low Risk (Stable Growth)",
    "Medium Risk (Balanced Growth)",
    "High Risk (Aggressive Growth)",
    "Very High Risk (Maximum Returns)",
]

InvestmentTimeline = Literal["< 1 Year", "1-3 Years", "3-5 Years", "5-10 Years", "> 10 Years"]

FinancialGoal = Literal[
    "Retirement planning",
    "Wealth preservation",
    "Income generation",
    "Capital appreciation",
    "Education funding",
    "Emergency fund growth",
]

AnnualIncome = Literal["< $50K", "$50K - $100K", "$100K - $200K", "$200K - $500K", "> $500K"]

EsgPreference = Literal["No preference", "ESG-friendly preferred", "Strong ESG focus only"]

NewsRiskTolerance = Literal["CONSERVATIVE", "MEDIUM", "AGGRESSIVE"]

NewsRiskLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]

PortfolioMode = Literal["ai_optimized", "user_defined"]

JobState = Literal["pending", "running", "completed", "failed"]


class IndustryInfo(BaseModel):
    key: str
    icon: str
    description: str


class Questionnaire(BaseModel):
    experience_level: ExperienceLevel
    risk_tolerance: RiskTolerance
    investment_timeline: InvestmentTimeline
    investment_amount: float = Field(gt=0)
    financial_goal: FinancialGoal
    annual_income: AnnualIncome


class RiskScoreRequest(BaseModel):
    questionnaire: Questionnaire


class RiskScoreResponse(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: str
    risk_color: str


class ManualHolding(BaseModel):
    symbol: str
    weight: float = Field(gt=0, le=1)


class PortfolioRequest(BaseModel):
    mode: PortfolioMode
    industry_focus: List[str] = Field(default_factory=list)
    exclude_industries: List[str] = Field(default_factory=list)
    esg_preference: EsgPreference = "No preference"
    questionnaire: Questionnaire
    risk_score: int = Field(ge=0, le=100)
    news_risk_tolerance: NewsRiskTolerance = "MEDIUM"

    # ai_optimized mode
    target_volatility: Optional[float] = None
    target_return: Optional[float] = None
    num_stocks: int = Field(default=10, ge=3, le=30)

    # user_defined mode
    manual_holdings: Optional[List[ManualHolding]] = None


class StockHolding(BaseModel):
    symbol: str
    name: str
    sector: str
    weight: float
    current_price: float
    predicted_return: Optional[float] = None
    volatility: float
    dividend_yield: float = 0.0
    market_cap: float = 0.0
    score: Optional[float] = None


class NewsFilteringSummary(BaseModel):
    total_stocks_analyzed: int = 0
    stocks_rejected: int = 0
    total_articles: int = 0


class PortfolioResult(BaseModel):
    portfolio_id: str
    generated_at: datetime
    investment_amount: float
    risk_score: int
    expected_annual_return: float
    portfolio_volatility: float
    holdings: List[StockHolding]
    sector_allocation: Dict[str, float]
    news_filtering_summary: Optional[NewsFilteringSummary] = None


class JobStatus(BaseModel):
    job_id: str
    status: JobState
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    result: Optional[PortfolioResult] = None
    error: Optional[str] = None


class NewsArticleSentiment(BaseModel):
    symbol: str
    overall_sentiment: float
    risk_level: NewsRiskLevel
    total_articles: int
    summary: str


class EconomicIndicator(BaseModel):
    series_id: str
    name: str
    value: Optional[float]
    previous_value: Optional[float] = None
    change_pct: Optional[float] = None
    ytd_change_pct: Optional[float] = None
    volatility_pct: Optional[float] = None
    as_of: Optional[str] = None
    source: Literal["fred", "yfinance_proxy", "unavailable"]


class EconomicSnapshot(BaseModel):
    indicators: List[EconomicIndicator]
    fetched_at: datetime


class AIInsightRequest(BaseModel):
    portfolio: PortfolioResult
    language: Literal["ko", "en"] = "ko"


class AIInsightResponse(BaseModel):
    summary: str
