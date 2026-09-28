"""Risk questionnaire -> 0-100 risk score, and score -> risk-level label.

Ported from `calculate_risk_score()` / `get_risk_level()`. The scoring
weights and bands are unchanged, but one real bug is fixed here: the
original's `financial_goal` scoring dict used different strings
("Retirement Planning", "Wealth Accumulation", "Purchasing a Home", ...)
than the ones the risk-assessment questionnaire actually offered
("Retirement planning", "Wealth preservation", "Capital appreciation", ...)
-- different capitalization *and* different options entirely. Since none of
the dict keys could ever match what the UI actually sent, `.get(..., 12)`
silently fell through to the default every single time: the financial-goal
answer never affected the risk score at all. This version's keys match the
schema's `FinancialGoal` literal exactly.

The original also scored an `existing_portfolio_size` field that the
questionnaire never actually collected (always defaulting to 0, i.e. always
1 point) -- this version uses `investment_amount`, which the questionnaire
does collect, as the portfolio-size signal instead.
"""
from __future__ import annotations

from typing import Tuple

from app.models.schemas import Questionnaire

EXPERIENCE_SCORES = {
    "Beginner (0-2 years)": 5,
    "Intermediate (2-5 years)": 10,
    "Advanced (5-10 years)": 15,
    "Expert (10+ years)": 20,
}

RISK_TOLERANCE_SCORES = {
    "Very Low Risk (Capital Preservation)": 5,
    "Low Risk (Stable Growth)": 10,
    "Medium Risk (Balanced Growth)": 18,
    "High Risk (Aggressive Growth)": 25,
    "Very High Risk (Maximum Returns)": 30,
}

TIMELINE_SCORES = {
    "< 1 Year": 2,
    "1-3 Years": 6,
    "3-5 Years": 10,
    "5-10 Years": 16,
    "> 10 Years": 20,
}

FINANCIAL_GOAL_SCORES = {
    "Retirement planning": 15,
    "Wealth preservation": 10,
    "Income generation": 8,
    "Capital appreciation": 15,
    "Education funding": 12,
    "Emergency fund growth": 6,
}

INCOME_SCORES = {
    "< $50K": 3,
    "$50K - $100K": 5,
    "$100K - $200K": 7,
    "$200K - $500K": 9,
    "> $500K": 10,
}

RISK_LEVEL_BANDS = [
    (25, "Very Conservative", "#28a745"),
    (45, "Conservative", "#66bb6a"),
    (65, "Moderate", "#ffc107"),
    (80, "Aggressive", "#fd7e14"),
]
RISK_LEVEL_FALLBACK = ("Very Aggressive", "#dc3545")


def _investment_amount_score(amount: float) -> int:
    if amount < 10_000:
        return 1
    if amount < 100_000:
        return 2
    if amount < 1_000_000:
        return 4
    return 5


def calculate_risk_score(questionnaire: Questionnaire) -> int:
    total = 0
    total += EXPERIENCE_SCORES.get(questionnaire.experience_level, 5)
    total += RISK_TOLERANCE_SCORES.get(questionnaire.risk_tolerance, 18)
    total += TIMELINE_SCORES.get(questionnaire.investment_timeline, 10)
    total += FINANCIAL_GOAL_SCORES.get(questionnaire.financial_goal, 12)
    total += INCOME_SCORES.get(questionnaire.annual_income, 5)
    total += _investment_amount_score(questionnaire.investment_amount)
    return min(100, max(0, total))


def get_risk_level(score: int) -> Tuple[str, str]:
    for threshold, label, color in RISK_LEVEL_BANDS:
        if score <= threshold:
            return label, color
    return RISK_LEVEL_FALLBACK
