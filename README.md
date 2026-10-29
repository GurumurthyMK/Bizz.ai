# Bizz AI

AI-powered business intelligence and predictive customer analytics platform.
See `Product.md` for the product definition.

> **Status: complete MVP.** The full product is implemented: authentication,
> deterministic demo dataset, analytics, ML (churn/purchase/segmentation/
> opportunities), overview dashboard, customer/segment/prediction/opportunity
> workflows, LLM intelligence layer (Gemini/Groq, optional), CSV import,
> alerts, and reports.
>
> `Build_plan.md` and the phase structure are **historical planning records** —
> not a to-do list. Do not re-implement anything described there.

## Repository layout

```text
bizz-ai/
├── frontend/          # Next.js + TypeScript + Tailwind + shadcn/ui
├── backend/           # FastAPI + Pydantic + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/       # routes (versioned under /api/v1)
│   │   ├── core/      # configuration / shared concerns
│   │   ├── db/        # engine, sessions, Base
│   │   ├── models/    # ORM models (from Phase 2B)
│   │   ├── schemas/   # Pydantic request/response schemas
│   │   ├── services/  # business logic (from Phase 2)
│   │   ├── analytics/ # deterministic metrics (Phase 3A)
│   │   ├── ml/        # training + inference (Phase 3A)
│   │   └── llm/       # provider abstraction (Phase 4B)
│   ├── tests/
│   └── alembic/       # migrations
├── docs/
├── docker-compose.yml # PostgreSQL
├── .env.example
└── README.md
```

## Prerequisites

- Docker + Docker Compose (PostgreSQL)
- Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with npm

## Local setup

```bash
# 1. Environment
cp .env.example .env   # no real secrets; dev placeholders only

# 2. PostgreSQL
docker compose up -d postgres
# If port 5432 is already taken by a local PostgreSQL, use another host port:
# POSTGRES_PORT=5433 docker compose up -d postgres
# and point the backend at it via DATABASE_URL (host port 5433).

# 3. Backend
cd backend
uv sync --group dev            # install deps (incl. pytest/ruff/mypy)
uv run uvicorn app.main:app --reload --port 8000

# 4. Frontend (new terminal, from repo root)
cd frontend
npm install
cp .env.example .env.local     # optional; defaults to http://localhost:8000
npm run dev
```

## Verify

```bash
curl http://localhost:8000/api/v1/health      # {"status":"ok",...}
curl http://localhost:8000/api/v1/health/db   # {"status":"ok","database":"connected"}

# Auth (cookie jar keeps the HttpOnly session cookie)
curl -c jar.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@company.com","password":"at-least-8-chars"}'
curl -b jar.txt http://localhost:8000/api/v1/auth/me
```

Apply database migrations after pulling (from `backend/`, with `DATABASE_URL` set):

```bash
uv run alembic upgrade head
```

Seed the deterministic demo dataset (refuses when business data exists; `--reset` replaces it explicitly):

```bash
uv run python -m app.seed.run            # ~10k customers, 60+ products, 100k+ transactions
uv run python -m app.seed.run --audit    # report counts and integrity without inserting
uv run python -m app.seed.run --reset    # delete business rows (never users) and reseed
```

Train the ML models (artifacts land in `backend/app/ml/artifacts/`, gitignored — retrain after reseeding):

```bash
uv run python -m app.ml.train
```

Frontend: <http://localhost:3000>

## Checks

```bash
# Backend (from backend/)
uv run pytest
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app

# Frontend (from frontend/)
npm run typecheck
npm run lint
npm run build
```

## Docs

- `Product.md` — product definition (historical)
- `Design.md` — design system & UX direction
- `Architecture.md` — system architecture (historical/reference)
- `Build_plan.md` — phased execution plan (historical — do NOT re-implement)
- `WINDOWS_DEPLOYMENT_GUIDE.md` — running Bizz AI on Windows

## Run guide

```bash
# Terminal 1 — database (from repo root)
docker compose up -d postgres

# Terminal 2 — backend (from backend/)
uv run uvicorn app.main:app --reload --port 8000

# Terminal 3 — frontend (from frontend/)
npm run dev
```

> **Important — dashboard reference date:** the Overview computes windows from
> *today*, so the dataset anchor must be at/near the current date. If KPIs are
> all flat zeros, re-seed and retrain with a fresh anchor:
>
> ```bash
> cd backend
> uv run python -m app.seed.run --reset --anchor <today: YYYY-MM-DD>
> uv run python -m app.ml.train
> ```
> Then restart the backend.