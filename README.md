# ForecastIQ

Retail intelligence web application — the **production serving layer** for an already-trained
Temporal Fusion Transformer (TFT) probabilistic demand-forecasting model built on the
Corporación Favorita dataset.

No training happens here. The app consumes pre-generated ML artifacts from `/artifacts` and, when
an artifact is missing, falls back to realistic synthetic demo data (54 stores × 33 categories =
1,612 product-store series) so the stack always runs out of the box.

## Features

| Page | What it shows |
| --- | --- |
| **Morning Brief** | Store health score (0–100), stockout-risk alerts, IsolationForest anomaly flags, top-10 P50 movers, yesterday actual vs predicted (MAPE + coverage). Mobile responsive. |
| **Forecast Explorer** | 16-day P10/P50/P90 Recharts chart with shaded band, historical actuals, LightGBM point overlay, holiday/oil event markers, 16-cell anomaly strip, D3 attention chart over the 90-day lookback (peaks at 7/14/21/28). |
| **Inventory Decision Engine** | Recommendation table with Lean/Balanced/Safe confidence modes, instant client + server recompute, row-level manager override with reason code (persisted for recalibration), Excel/PDF supplier-ready purchase-order export. |
| **Model Performance Monitor** | Weekly scorecards with trend arrows, coverage vs the 80% target, rolling TFT vs LightGBM vs ARIMA vs Chronos-Bolt-Base 2024 comparison, drift detector. |
| **Store & Category Analytics** | 54×33 D3 coverage heatmap (red = uncertain, green = confident), category MAPE leaderboard, store health ranking, PNG export. |

A yellow drift banner appears on every page when rolling MAPE degrades by more than 5 percentage
points across 3 consecutive weeks; the same rule triggers a retraining-recommendation email.

## Architecture

```
/backend        FastAPI (async), SQLAlchemy async ORM, Alembic, Celery + Beat, Redis cache
/frontend       React 18 + TypeScript + Vite + Tailwind, Recharts, D3, React Query, Zustand
/artifacts      ML artifact drop location (gitignored except .gitkeep)
/nginx          Nginx config: serves the built SPA and reverse-proxies the API
docker-compose.yml
.env.example
```

Backend layering: `app/api/routes` (thin routers) → `app/services` (business logic) →
`app/ml` (artifact loading + synthetic fallback) / `app/models` (ORM). All request and response
bodies are Pydantic v2 schemas; there is no raw SQL.

## Prerequisites

- Docker and Docker Compose v2 (the only requirement for the one-command startup)
- For local, non-Docker development: Python 3.11+ and Node.js 20+

## Quick start

```bash
cp .env.example .env
# Set a real JWT_SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up --build
```

Then open:

- Frontend: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

The backend container runs `alembic upgrade head` and the demo seed before starting Uvicorn, so
the database schema and demo users exist on first boot.

### Demo users

Seeded by `python -m app.seed` (idempotent). All use the password from `SEED_DEMO_PASSWORD`
(default `ForecastIQ!2024`) — development credentials only, never use them in production.

| Email | Role | Scope |
| --- | --- | --- |
| `manager@forecastiq.io` | `store_manager` | store 1 |
| `director@forecastiq.io` | `regional_director` | all stores |
| `hq@forecastiq.io` | `hq` | all stores |
| `admin@forecastiq.io` | `admin` | all stores + user creation |

## ML artifacts

Drop these files into `/artifacts` (bind-mounted read-only into the backend, worker and beat
containers). Each is loaded independently — whatever is missing falls back to synthetic data.

| File | Used for |
| --- | --- |
| `forecast_readable.csv` | Forecast rows: `product_id, store_nbr, family, forecast_date, p10, p50, p90, anomaly_score, is_holiday` |
| `lgbm_model.pkl` | LightGBM live point forecasts overlaid in the explorer |
| `metrics.pkl` | Monitor metrics: MAPE, coverage, 4-model comparison |
| `oil_scaler.pkl` | Oil-price feature scaling |
| `tsd_params.pkl` | Time-series decomposition / feature-engineering parameters |

### Synthetic fallback

`backend/app/ml/synthetic.py` deterministically (CRC32-seeded, stable across processes) generates
1,612 product-store series across 54 stores and 33 families with 16-day P10/P50/P90 paths,
seasonality and holiday uplift, oil-price event adjustments, LightGBM-style point forecasts,
IsolationForest-style anomaly scores, 90-day lookback attention with peaks at days 7/14/21/28, and
12 weeks of 4-model monitor metrics. `GET /api/v1/forecast/{product_id}/{store_nbr}` reports its
`data_source` so you can always tell artifact-backed data from synthetic data.

## Scheduled jobs

| Job | Schedule | What it does |
| --- | --- | --- |
| `run_nightly_batch` | 23:00 UTC daily | Recomputes 11 engineered features incl. IsolationForest anomaly scores with CV-based dynamic contamination, runs inference across all 1,612 series, writes to PostgreSQL, refreshes the Redis cache, and emails store managers about products scoring above `ANOMALY_ALERT_THRESHOLD`. |
| `check_model_drift` | Mondays 06:30 UTC | Rolling-MAPE drift test; persists a drift event and emails a retraining recommendation when the >5pp / 3-week rule fires. |

## Local development without Docker

```bash
# Backend
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export DATABASE_URL="sqlite+aiosqlite:///./forecastiq.db"
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (proxies /api to localhost:8000)
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run lint && npm run typecheck && npm run build
```

Redis is optional locally: cache failures degrade to direct computation rather than erroring.

## Configuration

Every variable is documented in [`.env.example`](.env.example) — database URL, Redis URL, Celery
broker/backend, JWT secret and expiry, auth rate limit, CORS origins, artifacts directory,
anomaly/coverage/drift thresholds, SMTP credentials, and ports. Secrets are read from the
environment only; nothing is hardcoded.

## Security

JWT bearer auth on every protected endpoint, bcrypt password hashing, four RBAC roles
(`store_manager` scoped to its own store, `regional_director`, `hq`, `admin`), `slowapi` rate
limiting on the auth endpoints, and CORS restricted to the configured frontend origins. Set a
strong `JWT_SECRET_KEY` and rotate the seeded demo passwords before any real deployment; enable
the HTTPS server block in [`nginx/default.conf`](nginx/default.conf) for production.

## License

This project retains the existing [`LICENSE`](LICENSE) (GNU GPL v3).
