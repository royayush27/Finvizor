# Finvizor

A US equity research workspace built with FastAPI and Next.js. Choose sectors, complete a risk questionnaire, then screen stocks or enter your own weights. Reports show historical returns, covariance-based portfolio volatility, allocation charts and CSV exports.

## Run locally

Backend (Python 3.11 or 3.12 recommended):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend in a second terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.local.example .env.local
npm run dev
```

Open http://localhost:3000. The browser calls same-origin `/api` routes, which Next.js forwards to `API_BASE_URL` (default `http://127.0.0.1:8000`). This also avoids browser CORS and remote-device localhost mistakes. In a hosted deployment, set `API_BASE_URL` to the backend's internal URL and rebuild the frontend. The old `NEXT_PUBLIC_API_BASE_URL` setting is accepted as a server-side fallback.

API documentation: http://127.0.0.1:8000/docs.

## What the numbers mean

- **Screened allocation:** a transparent heuristic ranks stocks using trailing returns, volatility, dividend yield and company size. The questionnaire score adjusts the return/risk emphasis. Conservative risk settings additionally exclude stocks with trailing annualized volatility of 20% or more. This is an all-equity screen; it does not establish suitability or guarantee capital preservation.
- **Universe:** at most 60 stocks per request, drawn in sector round-robin order with selected sectors prioritized. This is a curated universe, not the whole US market. Provider-reported sectors determine the final inclusion/exclusion rules.
- **Weights:** positive scores are normalized and capped. A fully invested portfolio with fewer than ten holdings cannot satisfy a 10% cap, so the effective cap is raised to `1 / holding_count` and disclosed in the report. Unavailable candidates can reduce the requested count; that is also disclosed.
- **Manual allocations:** 1–30 unique symbols with strictly positive weights totaling 100%. If any holding cannot be loaded, generation fails instead of silently dropping it. Manual selections bypass sector, news and risk screens.
- **Trailing portfolio return:** weighted buy-and-hold total return over up to 252 shared trading sessions, using adjusted price histories. Individual holding returns use their own trailing-year window. This is an illustration using today's selected holdings, not an out-of-sample strategy backtest.
- **Volatility:** `sqrt(w.T @ covariance(daily_returns) @ w * 252) * 100`, using dates shared by all holdings. This assumes fixed daily weights and captures cross-stock covariance. It is not the weighted average of individual volatilities.
- **Prices:** latest available closing data, potentially delayed. Allocations assume fractional shares and omit fees, taxes and transaction costs.
- **Risk score:** a questionnaire heuristic, recomputed on the server. It is not a calibrated probability of loss.

The old ML/ARIMA code remains in `backend/app/services/ml_predictor.py` for research, but is **not used by portfolio generation**. It trained on trailing returns and predicted on those same stocks, so its output could not support claims of future-return accuracy. The active pipeline deliberately reports historical results. A future forecasting model requires dated training samples, forward targets, leakage-free preprocessing and held-out evaluation before activation.

For API compatibility the legacy fields `expected_annual_return` and `predicted_return` remain; their values are historical percentages. `return_basis: "historical"`, `methodology`, `data_as_of`, `position_cap` and `warnings` make this explicit. The UI and CSV use historical labels.

## Optional integrations

Keys are loaded from `backend/.env`; never commit them.

| Key | Purpose |
| --- | --- |
| `NEWS_API_KEY` | Optional headline sentiment screening. Missing coverage is unknown, not a positive or neutral signal. |
| `FRED_API_KEY` | Economic-data endpoint, with labeled market-data proxies when unavailable. |
| `NAVER_CLOVA_API_KEY` | Optional explanation of a generated report. |

ESG and target-return/volatility constraints are rejected rather than silently ignored, since the application has no verified ESG dataset or target optimizer. News sentiment is a keyword/model heuristic and is not a verified risk assessment.

## Validation

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd frontend
npm run build
# With both servers running and Chrome installed:
node scripts/browser-smoke.mjs
```

The browser smoke test exercises sector selection, risk scoring, live manual portfolio generation, chart rendering and desktop/mobile overflow. It writes screenshots to the ignored `.artifacts/` directory. Set `CHROME_PATH` for a non-default Chrome installation. It uses live Yahoo data and can fail if the provider is unavailable.

## Deployment limits

Run the API with **one worker**. Jobs currently live in process memory: restart loses job status and server CSV exports; the browser retains its last report. Before a multi-worker or public deployment, use a durable shared job store/queue, authentication, rate limits and provider quotas. External provider failures are surfaced rather than replaced with invented market data.

## Design

Warm paper, dark green, serif headings and compact research tables replace gradient-heavy cards and decorative emoji. The direction follows the relevant recommendations in [Mateusz Sikora's design article](https://sikora.software/blog/ai-website-design), with emphasis on content, hierarchy and clear product language.

Educational research only. No trades are placed.
