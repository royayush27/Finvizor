from app.models.schemas import Questionnaire
from app.services.risk_scoring import calculate_risk_score, get_risk_level


def _questionnaire(**overrides) -> Questionnaire:
    defaults = dict(
        experience_level="Beginner (0-2 years)",
        risk_tolerance="Medium Risk (Balanced Growth)",
        investment_timeline="3-5 Years",
        investment_amount=10_000,
        financial_goal="Retirement planning",
        annual_income="$50K - $100K",
    )
    defaults.update(overrides)
    return Questionnaire(**defaults)


def test_risk_score_is_within_bounds():
    score = calculate_risk_score(_questionnaire())
    assert 0 <= score <= 100


def test_higher_risk_tolerance_increases_score():
    low = calculate_risk_score(_questionnaire(risk_tolerance="Very Low Risk (Capital Preservation)"))
    high = calculate_risk_score(_questionnaire(risk_tolerance="Very High Risk (Maximum Returns)"))
    assert high > low


def test_financial_goal_actually_affects_score():
    # Regression test for the original bug: the financial_goal scoring dict
    # keys never matched the questionnaire's actual option strings, so this
    # answer was silently ignored. It must now make a measurable difference.
    a = calculate_risk_score(_questionnaire(financial_goal="Emergency fund growth"))
    b = calculate_risk_score(_questionnaire(financial_goal="Capital appreciation"))
    assert a != b


def test_get_risk_level_bands():
    assert get_risk_level(10)[0] == "Very Conservative"
    assert get_risk_level(90)[0] == "Very Aggressive"
