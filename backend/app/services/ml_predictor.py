"""ML ensemble + ARIMA return prediction.

Ported from the `MLStockPredictor` class -- the most legitimately solid part
of the original prototype: RandomForest + GradientBoosting (+ optional
XGBoost) trained with TimeSeriesSplit cross-validation, ensembled by R^2-
weighted averaging, blended 70/30 with a per-symbol auto-ARIMA forecast.

Two real bugs fixed during the port (beyond the `st.*` decoupling):
  * `_extract_economic_features` called `self._get_default_econ_feature(...)`
    on a missing indicator, but that method was never defined anywhere in
    the 4,234-line source file -- guaranteed AttributeError the first time
    any FRED series came back missing. Replaced with an inline defaults
    dict (the same values the surrounding code already used elsewhere).
  * `fit_arima_models` called `model.fit(disp=False)` on
    `statsmodels.tsa.arima.model.ARIMA` -- but that class's `.fit()` does
    not accept a `disp` kwarg (that belonged to the old, removed
    `statsmodels.tsa.arima_model.ARIMA`). Every ARIMA fit in the original
    app raised `TypeError`, was silently swallowed by the surrounding
    `except Exception`, and fell back to a default 0.0 prediction with a
    +/-5% confidence interval -- meaning the advertised "30% ARIMA blend"
    was, in practice, always noise. Fixed by dropping the invalid kwarg, so
    ARIMA actually contributes real forecasts now.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

from app.models.schemas import EconomicIndicator
from app.services.financial_calcs import calculate_macd, perform_adf_test
from app.services.stock_universe import StockRecord

logger = logging.getLogger(__name__)

NON_FEATURE_COLUMNS = {"symbol", "price_history", "return_history"}

FRED_NAME_TO_FEATURE = {
    "Fed Funds Rate": "fed_funds_rate",
    "10Y Treasury Yield": "treasury_10y",
    "Unemployment Rate": "unemployment_rate",
    "CPI (All Items)": "inflation_rate",
    "Real GDP": "gdp_growth",
    "VIX Volatility Index": "vix",
}

DEFAULT_ECON_FEATURES: Dict[str, float] = {
    "fed_funds_rate": 2.0,
    "treasury_10y": 3.0,
    "unemployment_rate": 4.0,
    "inflation_rate": 2.5,
    "gdp_growth": 2.0,
    "vix": 20.0,
}

EXPECTED_FEATURE_COLUMNS = [
    "current_price", "sma_20_ratio", "sma_50_ratio", "sma_200_ratio", "rsi", "macd", "macd_signal",
    "momentum_1m", "momentum_3m", "momentum_6m", "momentum_1y", "volatility", "volume_ratio",
    "market_cap_log", "beta", "pe_ratio", "dividend_yield",
    "sector_tech", "sector_finance", "sector_healthcare", "sector_consumer", "sector_energy",
    "sector_industrial", "sector_materials", "sector_utilities", "sector_real_estate", "sector_communication_services",
    *DEFAULT_ECON_FEATURES.keys(),
]

SECTOR_FEATURE_MAP = {
    "sector_tech": "Technology",
    "sector_finance": "Financials",
    "sector_healthcare": "Healthcare",
    "sector_energy": "Energy",
    "sector_industrial": "Industrials",
    "sector_utilities": "Utilities",
    "sector_real_estate": "Real Estate",
    "sector_communication_services": "Communication Services",
}


def _rsi_series(prices: pd.Series, window: int = 14) -> pd.Series:
    if prices.empty or len(prices) < window:
        return pd.Series([50.0] * len(prices), index=prices.index)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _extract_economic_features(indicators: Optional[List[EconomicIndicator]]) -> Dict[str, float]:
    if not indicators:
        return dict(DEFAULT_ECON_FEATURES)

    by_name = {ind.name: ind.value for ind in indicators}
    features: Dict[str, float] = {}
    for fred_name, feature_name in FRED_NAME_TO_FEATURE.items():
        value = by_name.get(fred_name)
        features[feature_name] = float(value) if value is not None else DEFAULT_ECON_FEATURES[feature_name]
    return features


class MLStockPredictor:
    def __init__(self) -> None:
        self.models: Dict[str, Any] = {
            "RandomForest": RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_split=5, random_state=42, n_jobs=-1),
            "GradientBoosting": GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=6, random_state=42),
            "XGBoost": None,
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        self.ensemble_weights: Dict[str, float] = {}
        self.feature_importance: Dict[str, pd.DataFrame] = {}
        self.model_performance: Dict[str, Any] = {}
        self.arima_models: Dict[str, ARIMA] = {}

        try:
            import xgboost as xgb
            self.models["XGBoost"] = xgb.XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=6, random_state=42, n_jobs=-1)
        except ImportError:
            logger.info("XGBoost not available; using RandomForest and GradientBoosting only.")

    def prepare_features(
        self,
        stocks: List[StockRecord],
        economic_indicators: Optional[List[EconomicIndicator]] = None,
    ) -> pd.DataFrame:
        econ_features = _extract_economic_features(economic_indicators)
        rows: List[Dict[str, Any]] = []

        for stock in stocks:
            try:
                hist = yf.Ticker(stock.symbol).history(period="5y")
                if hist.empty or len(hist) < 100:
                    logger.warning(f"Insufficient historical data for {stock.symbol}. Skipping feature prep.")
                    continue

                hist["Returns"] = hist["Close"].pct_change()
                hist["SMA_20"] = hist["Close"].rolling(20).mean()
                hist["SMA_50"] = hist["Close"].rolling(50).mean()
                hist["SMA_200"] = hist["Close"].rolling(200).mean()
                hist["RSI"] = _rsi_series(hist["Close"], 14)
                macd_line, macd_signal, _ = calculate_macd(hist["Close"])
                hist["Volatility"] = hist["Returns"].rolling(30).std() * np.sqrt(252)
                hist["Price_Change_1M"] = hist["Close"].pct_change(21)
                hist["Price_Change_3M"] = hist["Close"].pct_change(63)
                hist["Price_Change_6M"] = hist["Close"].pct_change(126)
                hist["Price_Change_1Y"] = hist["Close"].pct_change(252)
                hist["Volume_SMA"] = hist["Volume"].rolling(20).mean()
                hist["Volume_Ratio"] = hist.apply(
                    lambda r: r["Volume"] / r["Volume_SMA"] if pd.notna(r["Volume_SMA"]) and r["Volume_SMA"] != 0 else 1,
                    axis=1,
                )

                latest = hist.iloc[-1].fillna(0)
                features: Dict[str, Any] = {
                    "symbol": stock.symbol,
                    "current_price": latest["Close"],
                    "sma_20_ratio": latest["Close"] / latest["SMA_20"] if pd.notna(latest["SMA_20"]) and latest["SMA_20"] != 0 else 1,
                    "sma_50_ratio": latest["Close"] / latest["SMA_50"] if pd.notna(latest["SMA_50"]) and latest["SMA_50"] != 0 else 1,
                    "sma_200_ratio": latest["Close"] / latest["SMA_200"] if pd.notna(latest["SMA_200"]) and latest["SMA_200"] != 0 else 1,
                    "rsi": latest["RSI"] if pd.notna(latest["RSI"]) else 50,
                    "macd": macd_line,
                    "macd_signal": macd_signal,
                    "momentum_1m": latest["Price_Change_1M"] if pd.notna(latest["Price_Change_1M"]) else 0,
                    "momentum_3m": latest["Price_Change_3M"] if pd.notna(latest["Price_Change_3M"]) else 0,
                    "momentum_6m": latest["Price_Change_6M"] if pd.notna(latest["Price_Change_6M"]) else 0,
                    "momentum_1y": latest["Price_Change_1Y"] if pd.notna(latest["Price_Change_1Y"]) else 0,
                    "volatility": latest["Volatility"] if pd.notna(latest["Volatility"]) else 0.2,
                    "volume_ratio": latest["Volume_Ratio"] if pd.notna(latest["Volume_Ratio"]) else 1,
                    "market_cap_log": float(np.log(stock.market_cap + 1e-9)) if stock.market_cap > 0 else float(np.log(1e9)),
                    "beta": stock.beta,
                    "pe_ratio": stock.pe_ratio,
                    "dividend_yield": stock.dividend_yield,
                }
                for feature_key, sector_name in SECTOR_FEATURE_MAP.items():
                    features[feature_key] = 1 if stock.sector == sector_name else 0
                features.update(econ_features)
                features["price_history"] = hist["Close"].tolist()
                features["return_history"] = hist["Returns"].dropna().tolist()

                rows.append(features)
            except Exception as e:
                logger.warning(f"Error preparing features for {stock.symbol}: {e}")
                continue

        df = pd.DataFrame(rows)
        for col in EXPECTED_FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0
        return df.fillna(0)

    def fit_arima_models(self, features_df: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
        predictions: Dict[str, float] = {}
        confidence_intervals: Dict[str, Dict[str, float]] = {}

        for _, row in features_df.iterrows():
            symbol = row["symbol"]
            price_history = row["price_history"]

            if not price_history or len(price_history) < 504:
                predictions[symbol] = 0.0
                confidence_intervals[symbol] = {"lower": -5.0, "upper": 5.0}
                continue

            try:
                recent_prices = pd.Series(price_history[-504:])
                optimal_d = 0
                temp = recent_prices.copy()
                for d_candidate in range(3):
                    if d_candidate > 0:
                        temp = temp.diff().dropna()
                    if len(temp) < 10:
                        break
                    if perform_adf_test(temp) <= 0.05:
                        optimal_d = d_candidate
                        recent_prices = temp
                        break

                if recent_prices.empty or len(recent_prices) < 2:
                    predictions[symbol] = 0.0
                    confidence_intervals[symbol] = {"lower": -5.0, "upper": 5.0}
                    continue

                best_aic = np.inf
                best_order = (1, optimal_d, 0)
                for p in range(3):
                    for q in range(3):
                        if p == 0 and q == 0 and optimal_d == 0:
                            continue
                        if len(recent_prices.dropna()) < (p + optimal_d + q + 1):
                            continue
                        try:
                            fitted = ARIMA(recent_prices, order=(p, optimal_d, q)).fit()
                            if fitted.aic < best_aic:
                                best_aic = fitted.aic
                                best_order = (p, optimal_d, q)
                        except Exception:
                            continue

                if best_aic == np.inf:
                    predictions[symbol] = 0.0
                    confidence_intervals[symbol] = {"lower": -5.0, "upper": 5.0}
                    continue

                fitted_arima = ARIMA(recent_prices, order=best_order).fit()
                forecast = fitted_arima.get_forecast(steps=21)
                forecast_mean = forecast.predicted_mean
                conf_int = forecast.conf_int()

                current_price = price_history[-1]
                if current_price:
                    predicted_return = (forecast_mean.iloc[-1] / current_price - 1) * 100
                    ci_lower = (conf_int.iloc[-1, 0] / current_price - 1) * 100
                    ci_upper = (conf_int.iloc[-1, 1] / current_price - 1) * 100
                else:
                    predicted_return, ci_lower, ci_upper = 0.0, -5.0, 5.0

                predictions[symbol] = predicted_return
                confidence_intervals[symbol] = {"lower": ci_lower, "upper": ci_upper}
                self.arima_models[symbol] = fitted_arima
            except Exception as e:
                logger.warning(f"ARIMA prediction failed for {symbol}: {e}")
                predictions[symbol] = 0.0
                confidence_intervals[symbol] = {"lower": -5.0, "upper": 5.0}

        return predictions, confidence_intervals

    def train(self, features_df: pd.DataFrame, targets: pd.Series) -> None:
        if features_df.empty or len(features_df) < 20:
            logger.warning("Insufficient data for ML training (need >= 20 rows). Skipping.")
            self.is_trained = False
            return

        feature_cols = [c for c in features_df.columns if c not in NON_FEATURE_COLUMNS]
        X = features_df[feature_cols].fillna(0)
        X_scaled = pd.DataFrame(self.scaler.fit_transform(X), columns=X.columns)

        n_splits = max(1, min(5, len(X_scaled) // 5))
        tscv = TimeSeriesSplit(n_splits=n_splits)

        model_scores: Dict[str, float] = {}
        for name, model in self.models.items():
            if model is None:
                continue
            try:
                cv_scores = cross_val_score(model, X_scaled, targets, cv=tscv, scoring="r2", n_jobs=-1)
                model_scores[name] = float(cv_scores.mean())

                model.fit(X_scaled, targets)
                predictions = model.predict(X_scaled)

                self.model_performance[name] = {
                    "MSE": float(mean_squared_error(targets, predictions)),
                    "MAE": float(mean_absolute_error(targets, predictions)),
                    "R2": float(r2_score(targets, predictions)),
                    "CV_R2_Mean": float(cv_scores.mean()),
                    "CV_R2_Std": float(cv_scores.std()),
                }

                if hasattr(model, "feature_importances_"):
                    self.feature_importance[name] = pd.DataFrame(
                        {"feature": feature_cols, "importance": model.feature_importances_}
                    ).sort_values("importance", ascending=False)
            except Exception as e:
                logger.warning(f"Error training {name}: {e}")
                self.model_performance[name] = {"error": str(e)}
                continue

        if model_scores:
            total = sum(max(0, s) for s in model_scores.values())
            if total > 0:
                self.ensemble_weights = {name: max(0, s) / total for name, s in model_scores.items()}
            else:
                self.ensemble_weights = {name: 1.0 / len(model_scores) for name in model_scores}

        self.is_trained = True

    def predict_with_confidence(self, features_df: pd.DataFrame) -> Tuple[List[float], List[Dict[str, Any]]]:
        if not self.is_trained or features_df.empty:
            logger.warning("Model not trained or no features provided; returning default 8% predictions.")
            default_pred = 0.08
            rows = features_df.to_dict("records") if not features_df.empty else [{"symbol": "N/A"}]
            return (
                [default_pred] * len(rows),
                [{"symbol": r.get("symbol", "N/A"), "prediction": default_pred, "ci_lower": default_pred - 0.05, "ci_upper": default_pred + 0.05} for r in rows],
            )

        feature_cols = [c for c in features_df.columns if c not in NON_FEATURE_COLUMNS]
        X = features_df[feature_cols].fillna(0)
        X_scaled = pd.DataFrame(self.scaler.transform(X), columns=X.columns)

        arima_preds, arima_conf = self.fit_arima_models(features_df)

        ml_predictions: Dict[str, np.ndarray] = {}
        for name, model in self.models.items():
            if model is None or name not in self.ensemble_weights:
                continue
            try:
                ml_predictions[name] = model.predict(X_scaled)
            except Exception as e:
                logger.error(f"Prediction with {name} failed: {e}")
                ml_predictions[name] = np.full(len(X_scaled), 0.0)

        ensemble_predictions: List[float] = []
        confidence_intervals: List[Dict[str, Any]] = []

        for idx, row in features_df.reset_index(drop=True).iterrows():
            symbol = row["symbol"]
            ml_pred, total_weight = 0.0, 0.0
            individual_preds: List[float] = []

            for name, preds in ml_predictions.items():
                if name in self.ensemble_weights and idx < len(preds):
                    weight = self.ensemble_weights[name]
                    ml_pred += preds[idx] * weight
                    total_weight += weight
                    individual_preds.append(float(preds[idx]))

            ml_pred = ml_pred / total_weight if total_weight > 0 else 0.0
            arima_pred = arima_preds.get(symbol, ml_pred)
            final_pred = (0.7 * ml_pred + 0.3 * arima_pred) if total_weight > 0 else arima_pred

            if individual_preds and symbol in arima_conf:
                ml_std = float(np.std(individual_preds)) if len(individual_preds) > 1 else abs(ml_pred) * 0.1
                arima_ci_width = (arima_conf[symbol]["upper"] - arima_conf[symbol]["lower"]) / 2
                combined_std = float(np.sqrt(0.7**2 * ml_std**2 + 0.3**2 * arima_ci_width**2))
                ci_lower, ci_upper = final_pred - 1.96 * combined_std, final_pred + 1.96 * combined_std
            else:
                std_error = abs(final_pred) * 0.15
                ci_lower, ci_upper = final_pred - 1.96 * std_error, final_pred + 1.96 * std_error

            confidence_intervals.append({
                "symbol": symbol,
                "prediction": final_pred,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "ml_prediction": ml_pred,
                "arima_prediction": arima_pred,
            })
            ensemble_predictions.append(final_pred)

        return ensemble_predictions, confidence_intervals
