# Bizz AI on Windows — Deployment Guide

## Project Overview
**Bizz AI** is an AI-powered business intelligence and predictive customer analytics platform built with:
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + Python 3.11+ + SQLAlchemy + Pydantic
- **Database**: PostgreSQL (Docker Compose, containerized; backend runs locally)
- **Tooling**: `uv` for Python package management, `npm` for frontend

This guide assumes all necessary dependencies are already installed on the Windows machine.

---

## ⚠️ CRITICAL: Security Fix Required

**Real API key found committed in source control.**

The file `backend/.env` contains a real Gemini API key:
```
GEMINI_API_KEY=AQ.Ab8RN6KAvD9ocS9vEq2LGcA0F-vRB8SQk3POROIhpzAAAoVKZg
```

**This must be addressed immediately:**
1. **Rotate the Gemini API key** at the Google Cloud Console
2. **Remove the real key** from `backend/.env` — replace with a placeholder or empty value
3. **Never commit real `.env` files** — `.env`, `backend/.env`, and `frontend/.env*` are all gitignored
4. Use `.env.example` as the template for new developers

---

## 1. Prerequisites for Windows

Ensure these are installed and accessible from your terminal (Command Prompt or PowerShell):

| Dependency | Minimum Version | Verification Command |
|------------|----------------|---------------------|
| **Docker Desktop** | Latest | `docker --version` & `docker compose version` |
| **Python** | 3.11+ | `python --version` |
| **uv** (recommended) | Latest | `uv --version` |
| **Node.js** | 20+ | `node --version` |
| **Git** | Latest | `git --version` |

> **Docker Desktop**: Install and ensure it's running. The Kubernetes flag should be **disabled** for local dev.

---

## 2. Environment File Setup

### 2.1 Copy the `.env` template

From the repository root:

```cmd
copy .env.example .env
```

This creates a `.env` file with all documented variables using safe defaults.

### 2.2 Edit `.env` for Windows

Edit `backend/.env` (created from the template) with Windows-appropriate values:

| Variable | Windows Guidance | Default (from .env.example) |
|----------|-----------------|----------------------------|
| `DATABASE_URL` | `postgresql+psycopg://bizzai:bizzai@localhost:5432/bizzai` — works with Docker Desktop on localhost | `postgresql+psycopg://bizzai:bizzai@localhost:5432/bizzai` |
| `SECRET_KEY` | Generate a new random value **or** keep the dev placeholder | `change-me-to-a-long-random-value` |
| `ENVIRONMENT` | `development` (or `production`) | `development` |
| `BACKEND_CORS_ORIGINS` | Must include `http://localhost:3000` and `http://localhost:3001` (Next.js default dev ports) <br>Format: comma-separated or JSON list | `http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Keep default (10080 = 7 days) or adjust | `10080` (commented in example) |
| `LLM_PROVIDER` | `disabled` for MVP (core analytics work without LLM) | `disabled` |
| `GEMINI_API_KEY` | **Optional** — only if LLM features needed. Never commit real keys. | (commented out) |
| `NEXT_PUBLIC_API_URL` | Set in `frontend/.env.local` (not backend `.env`) | `http://localhost:8000` |

### 2.3 Frontend `.env.local`

The file `frontend/.env.local` already exists with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This is correct for local development. Do not change unless running the frontend on a different port.

---

## 3. Step-by-Step Windows Setup

### Step 1: Clone and open in terminal
```cmd
git clone <repository-url>
cd bizzai
```

### Step 2: Set up environment variables
```cmd
copy .env.example .env
```
Then edit `backend\.env` with your preferred text editor (Notepad++, VS Code, etc.).

### Step 3: Start PostgreSQL via Docker
```cmd
docker compose up -d postgres
```
Verify it's running:
```cmd
docker compose ps
```
You should see `bizzai-postgres` with status `Up`.

### Step 4: Install backend dependencies
```cmd
cd backend
uv sync --group dev
```
This installs all Python dependencies including dev tools (pytest, ruff, mypy).

### Step 5: Run database migrations
```cmd
uv run alembic upgrade head
```

### Step 6: Seed the demo dataset
```cmd
uv run python -m app.seed.run --reset
```
Expected: ~10,000 customers, 60+ products, 100,000+ transactions.

> **Why this stays correct over time:** the seeder defaults its anchor to
> *today* (UTC), matching the Overview dashboard, which computes KPI windows
> from *now*. Data and dashboards therefore agree automatically. Pass
> `--anchor YYYY-MM-DD` explicitly only when you need a byte-identical
> reproduction of a specific dataset run.

### Step 7: Train ML models
```cmd
uv run python -m app.ml.train
```
Artifacts land in `backend/app/ml/artifacts/` (gitignored).

### Step 8: Start the backend
```cmd
uv run uvicorn app.main:app --reload --port 8000
```
The backend will be available at `http://localhost:8000`.

### Step 9: Set up and start the frontend (new terminal window)

From the repository root:
```cmd
cd frontend
npm install
cp .env.example .env.local    # optional; defaults to http://localhost:8000
npm run dev
```
The frontend will be available at `http://localhost:3000`.

### Step 10: Verify everything works
```cmd
# From any terminal, from repo root:
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok"}
```

---

## 4. Common Windows Issues & Fixes

| Problem | Solution |
|---------|----------|
| **Docker not running** | Start Docker Desktop. Wait for the whale icon to appear in the system tray. |
| **Port 5432 conflict** | If another app uses port 5432, change `POSTGRES_PORT` in `.env` and `docker-compose.yml` to another port (e.g., 5433), then restart Docker. |
| **CORS errors** | Ensure `BACKEND_CORS_ORIGINS` in `backend\.env` includes `http://localhost:3000` and `http://localhost:3001`. These are the default Next.js dev ports on Windows. |
| **`uv` not recognized** | Add `uv` to PATH, or use `pip install -r backend/requirements.txt` as fallback (though `uv` is preferred). |
| **Node modules fail (ARM64 Windows)** | Try: `npm config set legacy-peer-versions true` then `npm install`. Or use an x64 Node.js build. |
| **Frontend can't reach backend** | Verify `NEXT_PUBLIC_API_URL` in `frontend\.env.local` is `http://localhost:8000`. Both Docker and frontend must be running. |
| **Python version mismatch** | `pyproject.toml` requires `>=3.11,<3.15`. Ensure `python --version` returns a compatible version. |

---

## 5. Environment File (.env) Best Practices

### 5.1 Structure

```
# Repository root .env (from .env.example)
DATABASE_URL=postgresql+psycopg://bizzai:bizzai@localhost:5432/bizzai
SECRET_KEY=change-me-to-a-long-random-value
ENVIRONMENT=development
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001
# LLM (optional)
LLM_PROVIDER=disabled
# Docker compose overrides (read by compose, not directly by code)
POSTGRES_USER=bizzai
POSTGRES_PASSWORD=bizzai
POSTGRES_DB=bizzai
POSTGRES_PORT=5432
# Frontend public URL (read by Next.js, NOT by backend)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5.2 What must NEVER be committed

- `backend/.env` with real `GEMINI_API_KEY` or any real secret
- `frontend/.env` with real secrets (Next.js strips `NEXT_PUBLIC_` prefix; non-public vars are safe)
- Any `.env` file checked into git (all are gitignored)

### 5.3 How to add a new secret

1. Add the variable to `.env.example` with a descriptive comment
2. **Do not** add real values to the repo
3. Each developer creates their own local `.env` from the template
4. In production, use a secrets manager (Azure Key Vault, AWS Secrets Manager, etc.)

### 5.4 Windows-specific notes on `.env`

- Forward slashes work fine in Windows paths for Docker: `localhost:5432` is fine
- If you edit `.env` in Notepad, be aware it may add CRLF line endings. The Python `pydantic_settings` library handles both, but `git diff` may show `^M` characters. You can normalize with:
  ```cmd
  git checkout .  # reset line endings
  ```
- PowerShell and CMD both work for setting env vars, but use `set VAR=value` in CMD and `$env:VAR = "value"` in PowerShell (temporary only). For persistent changes, edit the `.env` file directly.

---

## 6. Technical Build Checks

After setup, run these checks to verify the project builds correctly:

### 6.1 Backend checks (from `backend/` directory)

```cmd
uv run pytest          # Run test suite
uv run ruff check app tests  # Lint check
uv run ruff format --check app tests  # Format check
uv run mypy app        # Type checking
```

### 6.2 Frontend checks (from `frontend/` directory)

```cmd
npm run typecheck      # TypeScript check
npm run lint           # ESLint
npm run build          # Production build (Next.js)
```

### 6.3 Known technical issues to watch

| Issue | Status | Impact |
|-------|--------|--------|
| Real Gemini API key in `backend/.env` | ❌ **CRITICAL** - Must fix before any LLM-dependent features | Security risk; key exposure |
| `backend/.env` has dev placeholder mixed with real key | ❌ Must reset from `.env.example` | Cleanup needed |
| README typo: `docker compose -d pstgr` | ❌ Minor | Documentation fix only |
| No `Dockerfile` for frontend/backend | ✅ Expected | Per architecture doc: "containerizing them is a later-phase decision" |
| `uv sync` may be slow on first run | ✅ Normal | First-time dependency installation |

---

## 7. Quick Reference Commands (Windows CMD)

```cmd
:: From repository root
copy .env.example .env

:: Start PostgreSQL
docker compose up -d postgres

:: Backend (from backend/)
uv sync --group dev
uv run alembic upgrade head

:: Seed demo data (anchor defaults to today) then retrain
uv run python -m app.seed.run --reset
uv run python -m app.ml.train
uv run uvicorn app.main:app --reload --port 8000

:: Frontend (from frontend/, new terminal)
npm install
npm run dev

:: Verify
curl http://localhost:8000/api/v1/health
```

---