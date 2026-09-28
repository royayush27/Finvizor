# Finvizor Pro

AI-powered portfolio construction: a machine-learning return-prediction ensemble (RandomForest +
GradientBoosting + XGBoost, blended with per-symbol ARIMA forecasts), live FRED economic data, and
multi-method news-sentiment risk filtering, wrapped in a 5-step portfolio wizard.

Originally built as **US Finvizor Pro** for the **9th Mirae Asset Securities AI Festival** (2025) as
a single-file Streamlit app. This version is a full rewrite: a **FastAPI** backend exposing the
ML/data pipeline as a REST API, and a **Next.js + TypeScript + Tailwind** frontend, so the wizard UI
no longer full-page-reruns on every click and the app can be deployed like a normal web service.

> Educational project only. Nothing here is financial advice -- always consult a qualified financial
> advisor before making investment decisions.

## Architecture

```
backend/    FastAPI service -- ML models, FRED/yfinance/NewsAPI integration, portfolio scoring
frontend/   Next.js app -- 5-step wizard UI, polls the backend for async portfolio generation
```

The original prototype trained ML models and pulled ~60 stocks' worth of data synchronously inside
a single Streamlit script run, which is a large part of why it felt slow. Here, portfolio generation
runs as a background job on the backend (`POST /api/portfolio/generate` returns a job ID immediately;
the frontend polls `GET /api/portfolio/jobs/{id}` and shows real progress) instead of freezing the UI.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # fill in your own API keys -- see below
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The app is now at `http://localhost:3000`.

### API keys

All keys are optional but unlock more of the app -- get your own free keys, nothing is bundled:

| Key                    | Used for                                  | Get one at                                              |
|-------------------------|--------------------------------------------|----------------------------------------------------------|
| `FRED_API_KEY`          | Macro indicators (falls back to yfinance)  | https://fred.stlouisfed.org/docs/api/api_key.html         |
| `NEWS_API_KEY`          | News-sentiment stock filtering             | https://newsapi.org/                                      |
| `NAVER_CLOVA_API_KEY`   | Optional Korean-language AI portfolio summary | https://www.ncloud.com/product/aiService/clovaStudio   |

**Never commit `.env` or `.env.local`.** Both are gitignored; only the `.env.example` /
`.env.local.example` templates (placeholders only) are checked in.

## What changed from the original prototype

The original 4,234-line Streamlit script had two hardcoded, leaked API keys (one of which also had a
logic bug that made it silently override a correctly-configured `secrets.toml`), ~500 lines of dead
code (an entire unused bond/fund portfolio engine, a never-routed Settings page), and several real
bugs that would crash the app in production paths (undefined functions/variables reached only under
specific failure conditions) plus a couple of quieter ones (an ARIMA call using a removed
`statsmodels` API, and a risk-questionnaire scoring table whose keys never matched the UI's actual
option strings, silently ignoring the user's stated financial goal). This rewrite fixes all of them
during the port -- see inline docstrings in `backend/app/services/*.py` for exactly what changed and
why, function by function.

The legitimately solid part of the original -- the ML ensemble, the FRED integration, and the
financial-math utilities (RSI/MACD/Bollinger/beta/drawdown/VaR/CVaR) -- carried over with the same
logic, just decoupled from Streamlit and given proper types.

## Testing

```bash
cd backend
pytest
```

Covers the pure-function services (financial math, portfolio scoring, risk scoring) including a
regression test for the financial-goal scoring bug mentioned above.
