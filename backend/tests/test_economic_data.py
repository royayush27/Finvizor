import pandas as pd
import pytest

from app.services.economic_data import _metrics, _year_start_value


def test_ytd_uses_prior_year_close_instead_of_entire_lookback():
    series = pd.Series([50, 100, 105, 110], index=pd.to_datetime([
        "2021-01-01", "2025-12-31", "2026-01-02", "2026-09-28"]))
    baseline = _year_start_value(series, 2026)
    assert baseline == 100
    assert _metrics(110, 105, baseline, 0.01)[1] == pytest.approx(10)


def test_missing_year_baseline_or_stale_data_is_unavailable():
    series = pd.Series([100, 110], index=pd.to_datetime(["2026-01-02", "2026-09-28"]))
    assert _year_start_value(series, 2026) is None
    assert _year_start_value(series, 2027) is None


def test_missing_or_invalid_metrics_do_not_become_zero_or_nan():
    assert _metrics(100, 0, None, float("nan")) == (None, None, None)
