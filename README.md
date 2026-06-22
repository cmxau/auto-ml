# ML-AutoPilot

AI-assisted machine learning workspace for students, analysts, and no-code ML beginners.

**Upload a dataset → AI analyzes it → clean it → build a pipeline → train a model → download results.**

**Core rule:** AI suggests → system validates → user approves → engine executes. The AI layer never mutates data directly.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running Locally — Docker (Recommended)](#running-locally--docker-recommended)
- [Running Locally — Native](#running-locally--native-no-docker-for-app-services)
- [Environment Variables Reference](#environment-variables-reference)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Troubleshooting](#troubleshooting)
- [Build Phases](#build-phases)
- [Known Limitations](#known-limitations)

---

## Features

| Area | What it does |
|---|---|
| Dataset upload | Upload CSV, XLSX, or JSON (up to 100 MB). Async profiling computes row count, column types, null rates, min/max/mean per column. |
| AI analysis | GPT-4o-mini infers task type (classification vs regression), recommends target column, flags data quality issues, ranks model candidates. |
| EDA | Distribution histograms, correlation matrix, missing value heatmap. AI writes plain-English commentary on each chart. |
| Cleaning | 9 transform types (drop column, fill nulls, rename, cast type, filter rows, normalize, one-hot encode, clip outliers, drop duplicates). Natural-language command interface. Every action goes through preview → confirm → apply. Each applied transform creates an immutable new dataset version. |
| Pipeline builder | React Flow drag-and-drop canvas. 8 node types: Input, Clean, Transform, Feature Engineering, Split, Train, Evaluate, Export. DAG validation before execute. |
| Model training | 6 model types via scikit-learn/XGBoost: Logistic Regression, Random Forest, XGBoost (classification); Linear Regression, Random Forest Regressor, XGBoost Regressor. 80/20 train/test split. Async Celery worker. Metrics: accuracy, F1, precision, recall, ROC-AUC (classification); R², RMSE, MAE, MSE (regression). |
| Feature importance | Extracted from tree models via `feature_importances_`, from linear models via `abs(coef_)`. Rendered as horizontal bar chart. |
| AI experiment summary | GPT-4o-mini explains results, gives assessment (excellent/good/fair/poor), suggests 2–3 improvements. Loaded on demand. |
| Model download | Presigned MinIO URL (5-minute TTL). Direct browser download of trained `.joblib` model file. |
| Error UX | Backend 422 validation errors (bad target column, column count >500) surfaced in UI. Failed training runs show error detail. |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | Next.js (App Router) | 14 |
| Language | TypeScript | 5 |
| Styling | Tailwind CSS | 3 |
| Server state | TanStack Query | v5 |
| Client state | Zustand | — |
| Charts | Recharts | — |
| Pipeline canvas | React Flow | — |
| Backend framework | FastAPI | 0.111 |
| Backend language | Python | 3.11 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13 |
| Schema validation | Pydantic | 2.7 |
| Database | PostgreSQL | 16 |
| Object storage | MinIO (S3-compatible) | — |
| Job queue broker | Redis | 7 |
| Task queue | Celery | 5.4 |
| ML | scikit-learn | 1.5 |
| ML (boosting) | XGBoost | 2.0 |
| Model serialization | joblib | 1.4 |
| Data processing | Pandas | 2.2 |
| AI | OpenAI API (GPT-4o-mini) | — |
| Auth | JWT (python-jose) + bcrypt (passlib) | — |

---

## Architecture Overview

```
Browser (Next.js)
    │
    │ HTTP/REST  Authorization: Bearer <jwt>
    ▼
FastAPI (port 8000)
    ├── Auth middleware → validates JWT on every protected route
    ├── Routers → thin HTTP layer, delegates to services
    ├── Services → business logic (no HTTP concerns)
    │    ├── storage_service.py  → MinIO (boto3)
    │    ├── ai_service.py       → OpenAI
    │    ├── training_service.py → pure sklearn/XGBoost functions (unit tested)
    │    └── ...
    ├── SQLAlchemy → PostgreSQL (sync, psycopg2)
    └── Celery task dispatch → Redis
            │
            ▼
    Celery Worker (same Docker image as backend)
        ├── profile_dataset_task   → runs pandas profiling, writes DatasetProfile to DB
        ├── ai_analysis_task       → calls OpenAI, writes AIInsight to DB
        ├── eda_task               → computes chart data, writes EDAResult to DB
        ├── cleaning_worker_task   → applies transform, writes new DatasetVersion to MinIO + DB
        └── train_model_task       → trains model, writes TrainingRun + metrics + artifact to DB/MinIO

Object Storage (MinIO, port 9000)
    Bucket: automl-files
    ├── datasets/{project_id}/{uuid}/{filename}          raw uploads and cleaned versions
    └── artifacts/{project_id}/models/{run_id}/model.joblib
```

**Key design decisions:**

- Every heavy operation (profiling, AI analysis, EDA, cleaning, training) is async. The API returns a `job_id` immediately. The frontend polls `GET /jobs/{jobId}` or waits for data to appear.
- Dataset versioning: raw upload = version 0. Every applied cleaning action creates a new immutable version. Training runs reference a specific version.
- The AI layer only produces JSON proposals. It never writes to the database directly.
- The Celery worker defers all imports inside the task function body to avoid forked-process import issues.

---

## Prerequisites

### Docker setup (recommended)

- **Docker Desktop** 4.x or later (includes Docker Compose v2)
- **OpenAI API key** — required for AI features (dataset analysis, EDA commentary, experiment summary)

That's it. Python and Node.js are not required on the host.

### Native setup

- **Python 3.11** (exact — `python3.11 --version`)
- **Node.js 20+** (`node --version`)
- **Docker** (for Postgres, Redis, MinIO only)
- **OpenAI API key**

---

## Environment Setup

The project uses a single `.env` file at the repo root. This file is read by:
- The backend FastAPI app (via `pydantic-settings`)
- `docker compose` (to resolve `${VARIABLE}` substitutions in `docker-compose.yml`)
- The Celery worker (same process as backend, same `.env`)

> **The `.env` file is gitignored** — it is never committed. `.env.example` is the source of truth for what variables are needed.

**Step 1: Copy the example file**

```bash
cp .env.example .env
```

**Step 2: Set your OpenAI API key**

Open `.env` in any editor and replace the placeholder:

```
OPENAI_API_KEY=sk-your-openai-api-key-here
```

with your real key:

```
OPENAI_API_KEY=sk-proj-abc123...
```

Get a key at https://platform.openai.com/api-keys

**All other values in `.env` work as-is for local development.** The only variable you must change is `OPENAI_API_KEY`.

The complete `.env` for local development looks like this:

```env
DATABASE_URL=postgresql://automl:automl@localhost:5432/automl
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_PUBLIC_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=automl-files
MINIO_USE_SSL=false
SECRET_KEY=change-me-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=development
MAX_UPLOAD_SIZE_MB=100
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Running Locally — Docker (Recommended)

All 5 services (Postgres, Redis, MinIO, backend, frontend) and the Celery worker run in containers. Nothing needs to be installed on the host beyond Docker.

### Step 1: Complete environment setup

Follow [Environment Setup](#environment-setup) above. The `.env` file must exist with your `OPENAI_API_KEY` before starting Docker services.

### Step 2: Start infrastructure services

Start the three stateful services first and wait for them to be healthy before proceeding:

```bash
docker compose up -d postgres redis minio
```

Check health status (all three should show `healthy`):

```bash
docker compose ps
```

Expected output:

```
NAME                STATUS
automl-minio-1   Up 30 seconds (healthy)
automl-postgres-1 Up 30 seconds (healthy)
automl-redis-1    Up 30 seconds (healthy)
```

If any service shows `starting` instead of `healthy`, wait another 10–15 seconds and check again. MinIO takes the longest.

### Step 3: Run database migrations

This creates all 10 tables (users, projects, datasets, dataset_versions, dataset_profiles, dataset_column_profiles, cleaning_actions, pipelines, training_runs, artifacts, etc.):

```bash
make migrate
```

This runs `alembic upgrade head` inside the backend container, applying all 5 migration files in order (001 → 005).

You should see output like:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, add ai_insights and eda_results
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, add cleaning and pipeline tables
INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, add training tables
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, add error_message to training_runs
```

### Step 4: Create the MinIO bucket

MinIO is running but the storage bucket does not yet exist. Create it:

```bash
make create-bucket
```

This sets up a `automl-files` bucket. All dataset uploads and trained model artifacts are stored here.

> **Note:** The backend also attempts to create this bucket automatically at startup (via `storage.ensure_bucket()` in `lifespan`). The `make create-bucket` step is a safety net in case the automatic creation fails.

### Step 5: Start all services

```bash
docker compose up -d
```

This starts the backend API server, the Celery worker, and the Next.js frontend.

Wait about 20 seconds for the frontend to compile (Next.js dev mode compiles on first request):

```bash
docker compose logs -f frontend
# Wait until you see: "Ready - started server on 0.0.0.0:3000"
```

### Step 6: Open the app

| Service | URL | Notes |
|---|---|---|
| **Frontend** | http://localhost:3000 | Main application |
| **Backend API** | http://localhost:8000 | FastAPI |
| **OpenAPI docs** | http://localhost:8000/docs | Interactive API explorer |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |
| **MinIO console** | http://localhost:9001 | Object storage browser |

MinIO console credentials: `minioadmin` / `minioadmin`

Register a new account at http://localhost:3000/register, then log in.

### Useful commands

```bash
# View logs from backend and Celery worker
make logs

# View logs from a specific service
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Open a shell inside the running backend container
make shell-backend

# Run all backend tests inside the container (requires running Postgres)
make test-backend

# Stop all services (data is preserved in Docker volumes)
make down

# Stop all services and delete all data (volumes)
docker compose down -v

# Rebuild images after changing requirements.txt or package.json
docker compose build
docker compose up -d
```

### How Docker Compose handles environment variables

`docker-compose.yml` hardcodes most values for local development. The only variable it reads from your `.env` file is `OPENAI_API_KEY`, using the `${OPENAI_API_KEY}` syntax. Docker Compose automatically reads `.env` from the project root.

This means: **you only need the `.env` file for `OPENAI_API_KEY` when using Docker.** All database, Redis, and MinIO credentials are hardcoded in `docker-compose.yml` for local dev.

---

## Running Locally — Native (No Docker for App Services)

Run Postgres, Redis, and MinIO via Docker. Run the backend API, Celery worker, and frontend directly on the host. Best for active backend or frontend development.

### Step 1: Start infrastructure only

```bash
docker compose up -d postgres redis minio
```

Verify all three are healthy:

```bash
docker compose ps
```

### Step 2: Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
- Set `OPENAI_API_KEY` to your real key
- The default `DATABASE_URL`, `REDIS_URL`, `MINIO_ENDPOINT` all point to `localhost` which is correct for native mode

### Step 3: Backend setup

```bash
cd backend

# Create and activate Python virtual environment
python3.11 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install all dependencies
pip install -r requirements.txt
```

Run database migrations:

```bash
# Still inside backend/ with venv active
alembic upgrade head
```

Start the API server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag restarts the server automatically when Python files change.

You should see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Start the Celery worker

Open a **second terminal**, activate the same virtualenv, and start the worker:

```bash
cd backend
source venv/bin/activate

celery -A app.workers.celery_app worker --loglevel=info -Q profiling,training,export
```

The worker handles all async jobs: profiling, AI analysis, EDA, cleaning transforms, and model training. Without the worker running, uploads will appear to hang.

You should see:

```
[tasks]
  . app.workers.profiling_worker.profile_dataset_task
  . app.workers.ai_worker.run_ai_analysis_task
  . app.workers.eda_worker.compute_eda_task
  . app.workers.cleaning_worker.apply_cleaning_task
  . app.workers.training_worker.train_model_task

[celery@hostname] ready.
```

### Step 5: Frontend setup

Open a **third terminal**:

```bash
cd frontend
npm install
npm run dev
```

The Next.js dev server starts on http://localhost:3000.

### Step 6: Create the MinIO bucket (one-time)

The backend will attempt to auto-create the bucket on startup, but if it fails:

**Option A: Via MinIO web console**
1. Open http://localhost:9001
2. Log in: `minioadmin` / `minioadmin`
3. Click "Create Bucket"
4. Name: `automl-files`
5. Click "Create Bucket"

**Option B: Via `mc` CLI (if installed)**
```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/automl-files
```

---

## Environment Variables Reference

These variables must be present in `.env` (native setup) or are hardcoded / passed via `docker-compose.yml` (Docker setup).

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://automl:automl@localhost:5432/automl` | PostgreSQL connection string. In Docker, this points to the `postgres` service hostname. |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection string. Used by Celery as both broker and result backend. In Docker, points to the `redis` service hostname. |
| `MINIO_ENDPOINT` | Yes | `localhost:9000` | MinIO address **without protocol**. Used by the backend and worker for server-side operations (upload, download, bucket creation). In Docker, this is `minio:9000` (internal hostname). |
| `MINIO_PUBLIC_ENDPOINT` | Yes | `localhost:9000` | MinIO address used when generating presigned download URLs for the browser. Must be reachable from the user's browser. In Docker local dev, this is `localhost:9000`. In production, set to your public CDN or domain (e.g., `storage.yourdomain.com`). If empty, falls back to `MINIO_ENDPOINT`. |
| `MINIO_ACCESS_KEY` | Yes | `minioadmin` | MinIO access key (username). |
| `MINIO_SECRET_KEY` | Yes | `minioadmin` | MinIO secret key (password). |
| `MINIO_BUCKET` | No | `automl-files` | Storage bucket name. Created automatically at backend startup. |
| `MINIO_USE_SSL` | No | `false` | Set to `true` if MinIO is behind HTTPS. |
| `SECRET_KEY` | Yes | — | JWT signing key. **Must be at least 32 characters. Never use the default in production.** Generate one: `openssl rand -hex 32` |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | JWT token lifetime (24 hours). |
| `ENVIRONMENT` | No | `development` | Used for logging and behavior flags. |
| `MAX_UPLOAD_SIZE_MB` | No | `100` | Maximum dataset file size. Files larger than this are rejected at upload. |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key. Required for AI analysis, cleaning suggestions, EDA commentary, and experiment summary. Without it, AI features return empty results but the rest of the app works. Get a key at platform.openai.com |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use for all AI features. |
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000/api/v1` | The URL the browser uses to reach the backend API. Must be reachable from the user's browser. In Docker, the frontend container uses this to build API requests that run in the browser (not in Node.js). |

> **`MINIO_ENDPOINT` vs `MINIO_PUBLIC_ENDPOINT`:**
> These solve a Docker networking problem. Inside Docker, the backend talks to MinIO at `minio:9000` (Docker internal hostname). But presigned download URLs are opened by the user's browser, which doesn't know about `minio:9000`. `MINIO_PUBLIC_ENDPOINT=localhost:9000` tells the backend to rewrite the host in presigned URLs before returning them to the frontend, so the browser can actually reach MinIO.

---

## Running Tests

### Backend unit tests (no database required)

These tests cover pure business logic functions and do not need Postgres running:

```bash
cd backend
source venv/bin/activate   # or activate your venv

pytest tests/test_training_service.py -v     # 20 tests: prepare_features, build_model, metrics, feature importance
pytest tests/test_profiling_service.py -v    # profiling pure functions
pytest tests/test_cleaning_service.py -v     # 9 transform types
pytest tests/test_eda_service.py -v          # chart data computation
pytest tests/test_ai_service.py -v           # OpenAI response parsing (mocked)
pytest tests/test_pipeline_service.py -v     # DAG validation
```

Run all pure unit tests at once:

```bash
pytest tests/test_training_service.py tests/test_profiling_service.py \
       tests/test_cleaning_service.py tests/test_eda_service.py \
       tests/test_ai_service.py tests/test_pipeline_service.py -v
```

Expected: **77 tests, all passing**, in ~3 seconds.

### Backend integration tests (requires Postgres)

These tests require a running PostgreSQL instance. They use a separate test database `automl_test` (defined in `conftest.py`):

```bash
# Create the test database first (one-time)
docker compose exec postgres createdb -U automl automl_test
# or natively:
psql -U automl -h localhost -c "CREATE DATABASE automl_test;"

# Run integration tests
pytest tests/test_auth.py tests/test_projects.py tests/test_datasets.py -v
```

Run all tests with coverage:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

Via Docker (no test database setup needed, uses the main DB):

```bash
make test-backend
```

### Frontend type checking

```bash
cd frontend
npx tsc --noEmit   # 0 errors expected
```

### Frontend build check

```bash
cd frontend
npm run build      # production build, catches any compilation errors
```

---

## Project Structure

```
automl/
│
├── .env                          ← your local config (gitignored, copy from .env.example)
├── .env.example                  ← template with all required variables
├── docker-compose.yml            ← all 6 services: postgres, redis, minio, backend, worker, frontend
├── Makefile                      ← shortcuts: up, down, logs, migrate, test-backend, shell-backend
├── .gitignore
│
├── backend/
│   ├── Dockerfile                ← python:3.11-slim, installs requirements, copies app
│   ├── requirements.txt          ← all Python dependencies pinned to exact versions
│   ├── alembic.ini               ← points Alembic to migrations/ directory
│   │
│   ├── app/
│   │   ├── main.py               ← FastAPI app factory; mounts all routers; creates MinIO bucket at startup
│   │   ├── config.py             ← pydantic-settings Settings class; reads from .env
│   │   ├── database.py           ← SQLAlchemy engine (sync, psycopg2); get_db() session dependency
│   │   │
│   │   ├── core/
│   │   │   ├── security.py       ← create_access_token(), verify_token(), hash_password(), verify_password()
│   │   │   └── deps.py           ← get_current_user() FastAPI dependency (validates JWT, loads User from DB)
│   │   │
│   │   ├── models/               ← SQLAlchemy ORM models (mapped_column / Mapped style)
│   │   │   ├── base.py           ← Base, TimestampMixin (created_at, updated_at), new_uuid()
│   │   │   ├── user.py           ← User (id, email, hashed_password, is_active)
│   │   │   ├── project.py        ← Project (id, user_id, name, description)
│   │   │   ├── dataset.py        ← Dataset (id, project_id, name, file_format, status) + DatasetVersion
│   │   │   ├── profile.py        ← DatasetProfile + DatasetColumnProfile (per-column stats)
│   │   │   ├── job.py            ← Job (id, project_id, job_type, status, input_json, output_json, error_message)
│   │   │   ├── ai_insight.py     ← AIInsight (analysis results, model recommendations)
│   │   │   ├── eda_result.py     ← EDAResult (chart data as JSONB)
│   │   │   ├── cleaning.py       ← CleaningAction + CleaningExecution
│   │   │   ├── pipeline.py       ← Pipeline + PipelineNode + PipelineEdge
│   │   │   └── training.py       ← TrainingRun + TrainingMetric + Artifact
│   │   │
│   │   ├── schemas/              ← Pydantic v2 request/response models
│   │   │   ├── auth.py
│   │   │   ├── project.py
│   │   │   ├── dataset.py
│   │   │   ├── cleaning.py
│   │   │   ├── pipeline.py
│   │   │   └── training.py
│   │   │
│   │   ├── routers/              ← FastAPI route handlers (thin HTTP layer only)
│   │   │   ├── auth.py           ← POST /auth/register, POST /auth/login, GET /auth/me
│   │   │   ├── projects.py       ← POST/GET/PATCH/DELETE /projects, GET /projects/{id}
│   │   │   ├── datasets.py       ← POST /datasets/upload, GET /datasets/{id}/preview, /profile, /versions
│   │   │   ├── ai.py             ← POST /ai/datasets/{id}/analyze, GET /ai/datasets/{id}/insights
│   │   │   ├── eda.py            ← GET /eda/datasets/{id}
│   │   │   ├── cleaning.py       ← POST /cleaning/propose, /apply, GET /cleaning/actions
│   │   │   ├── pipeline.py       ← POST/GET/PATCH /projects/{id}/pipelines, /validate, /execute
│   │   │   ├── training.py       ← POST /training/start, GET /training/runs/{id}, /download, /metrics, /summary, POST /training/compare
│   │   │   └── jobs.py           ← GET /jobs, GET /jobs/{id}
│   │   │
│   │   ├── services/             ← Business logic. No FastAPI imports. No HTTP concerns.
│   │   │   ├── auth_service.py   ← register_user(), authenticate_user()
│   │   │   ├── project_service.py ← get_project() (with ownership check)
│   │   │   ├── dataset_service.py ← create_dataset_with_version(), validate_extension()
│   │   │   ├── storage_service.py ← StorageService: upload_file(), download_file(), get_presigned_url()
│   │   │   ├── profiling_service.py ← profile_dataframe() → pure pandas, no DB/network, unit tested
│   │   │   ├── ai_service.py     ← OpenAI agents: analyze_dataset(), suggest_cleaning(), summarize_training_results()
│   │   │   ├── eda_service.py    ← compute_eda() → chart data as dicts, unit tested
│   │   │   ├── cleaning_service.py ← apply_action() → dispatches to 9 transform functions, unit tested
│   │   │   ├── pipeline_service.py ← validate_dag() → topological sort, cycle detection, unit tested
│   │   │   └── training_service.py ← prepare_features(), build_model(), compute_*_metrics(), extract_feature_importance(), serialize_model() — all pure functions, unit tested
│   │   │
│   │   └── workers/              ← Celery tasks. All imports deferred inside task bodies.
│   │       ├── celery_app.py     ← Celery instance; broker=Redis; queues: profiling, training, export
│   │       ├── profiling_worker.py ← profile_dataset_task(job_id): reads file from MinIO, runs profiling_service, writes DatasetProfile to DB
│   │       ├── ai_worker.py      ← run_ai_analysis_task(job_id): calls ai_service, writes AIInsight to DB
│   │       ├── eda_worker.py     ← compute_eda_task(job_id): calls eda_service, writes EDAResult to DB
│   │       ├── cleaning_worker.py ← apply_cleaning_task(job_id): reads version from MinIO, applies transform, writes new DatasetVersion
│   │       └── training_worker.py ← train_model_task(job_id): loads dataset, trains model, writes metrics + uploads .joblib to MinIO
│   │
│   ├── migrations/
│   │   ├── env.py                ← Alembic env; imports all ORM models so autogenerate works
│   │   └── versions/
│   │       ├── 001_initial_schema.py         ← users, projects, datasets, dataset_versions, dataset_profiles, dataset_column_profiles, jobs
│   │       ├── 002_add_ai_insights_eda_results.py ← ai_insights, eda_results
│   │       ├── 003_add_cleaning_pipeline.py  ← cleaning_actions, cleaning_executions, pipelines, pipeline_nodes, pipeline_edges
│   │       ├── 004_add_training_tables.py    ← training_runs, training_metrics, artifacts
│   │       └── 005_add_training_run_error_message.py ← adds error_message column to training_runs
│   │
│   └── tests/
│       ├── conftest.py           ← session-scoped engine on automl_test DB; per-test transaction rollback
│       ├── test_auth.py          ← register, login, JWT validation (integration)
│       ├── test_projects.py      ← project CRUD (integration)
│       ├── test_datasets.py      ← upload, profile, preview (integration)
│       ├── test_profiling_service.py ← pure unit tests, no DB
│       ├── test_cleaning_service.py  ← pure unit tests, no DB
│       ├── test_eda_service.py       ← pure unit tests, no DB
│       ├── test_ai_service.py        ← pure unit tests, no DB
│       ├── test_pipeline_service.py  ← pure unit tests, no DB
│       └── test_training_service.py  ← pure unit tests, no DB (20 tests)
│
├── frontend/
│   ├── Dockerfile                ← node:20-alpine, npm ci, EXPOSE 3000
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   │
│   └── src/
│       ├── app/                  ← Next.js App Router pages
│       │   ├── layout.tsx        ← root layout; wraps with QueryClientProvider + AuthProvider
│       │   ├── (auth)/
│       │   │   ├── login/page.tsx
│       │   │   └── register/page.tsx
│       │   ├── dashboard/page.tsx ← project grid; lists all user projects
│       │   └── projects/[projectId]/
│       │       ├── page.tsx      ← project overview: dataset list, pipeline list, recent training runs
│       │       ├── datasets/
│       │       │   ├── upload/page.tsx          ← file upload form
│       │       │   └── [datasetId]/page.tsx     ← dataset workspace: 6 tabs (Profile, EDA, Clean, Train, Data Preview, Pipeline)
│       │       ├── pipelines/
│       │       │   └── [pipelineId]/page.tsx    ← React Flow canvas
│       │       └── training/
│       │           ├── page.tsx                 ← training run list + start form
│       │           └── [runId]/page.tsx         ← run detail: metrics, feature importance chart, AI summary, download
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx  ← top nav + side nav wrapper
│       │   │   ├── TopNav.tsx
│       │   │   └── SideNav.tsx
│       │   ├── dataset/
│       │   │   ├── DatasetUploadCard.tsx
│       │   │   ├── PreviewTable.tsx
│       │   │   ├── ProfileSummaryPanel.tsx
│       │   │   ├── CleaningSuggestionList.tsx
│       │   │   └── CleaningCommandBox.tsx       ← natural-language cleaning input
│       │   ├── ai/
│       │   │   ├── AIInsightCard.tsx
│       │   │   ├── AIAssistantSidebar.tsx
│       │   │   └── ConfidenceBadge.tsx
│       │   ├── eda/
│       │   │   ├── ChartCard.tsx
│       │   │   ├── CorrelationMatrix.tsx
│       │   │   └── MissingHeatmap.tsx
│       │   ├── pipeline/
│       │   │   ├── PipelineCanvas.tsx           ← React Flow wrapper
│       │   │   ├── NodePalette.tsx
│       │   │   └── NodeInspector.tsx
│       │   ├── training/
│       │   │   ├── MetricsCard.tsx              ← grid of metric values with color coding
│       │   │   ├── FeatureImportanceChart.tsx   ← horizontal Recharts bar chart
│       │   │   └── RunComparisonTable.tsx       ← side-by-side metrics for multiple runs
│       │   └── shared/
│       │       ├── JobStatusBadge.tsx           ← queued/running/succeeded/failed badge
│       │       └── ErrorBanner.tsx              ← dismissible red error banner
│       │
│       └── lib/
│           ├── api/
│           │   ├── client.ts     ← single axios instance; attaches Bearer token from localStorage; base URL from NEXT_PUBLIC_API_URL
│           │   ├── auth.ts       ← authApi: login(), register(), me()
│           │   ├── projects.ts   ← projectsApi: list(), get(), create(), update(), delete()
│           │   ├── datasets.ts   ← datasetsApi: upload(), list(), get(), preview(), profile(), versions()
│           │   ├── ai.ts         ← aiApi: analyze(), getInsights()
│           │   ├── eda.ts        ← edaApi: get()
│           │   ├── cleaning.ts   ← cleaningApi: propose(), apply(), listActions()
│           │   ├── pipeline.ts   ← pipelineApi: create(), get(), save(), validate(), execute()
│           │   └── training.ts   ← trainingApi: start(), get(), listForProject(), download(), compare(), getSummary()
│           ├── hooks/
│           │   ├── useAuth.ts
│           │   ├── useProjects.ts
│           │   ├── useDatasets.ts
│           │   ├── useJobPoller.ts  ← polls GET /jobs/{id} every 2s while status is queued/running
│           │   ├── useAI.ts
│           │   ├── useEDA.ts
│           │   ├── useCleaning.ts
│           │   ├── usePipeline.ts
│           │   └── useTraining.ts   ← useTrainingRun polls every 3s while queued/running
│           └── store/
│               └── authStore.ts    ← Zustand: token + user stored in localStorage; hydrated on mount
│
└── docs/
    ├── design/                   ← original design documents
    │   ├── spec_doc.md           ← product requirements and user stories
    │   ├── system_design.md      ← architecture decisions
    │   ├── database_design.md    ← full schema with all fields, indexes, constraints
    │   ├── api-spec.md           ← REST API contract
    │   ├── ai_orchestration.md   ← AI agent roles and prompting strategy
    │   ├── frontend_architecture.md ← component hierarchy and UX rules
    │   └── implementation_plan.md ← phased build plan
    └── superpowers/
        ├── plans/                ← task-level implementation plans per phase
        └── specs/                ← phase design specs
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

All protected endpoints require: `Authorization: Bearer <token>`

Response envelope:

```json
{ "success": true, "data": { ... } }
```

Error response:

```json
{ "success": false, "detail": "Error message here" }
```

Async operations return immediately with a `job_id`. Poll `GET /jobs/{jobId}` until `status` is `succeeded` or `failed`.

### Auth

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/auth/register` | `{email, password}` | Create account. Returns `{token, user}` |
| `POST` | `/auth/login` | `{email, password}` | Login. Returns `{token, user}` |
| `GET` | `/auth/me` | — | Get current user |

### Projects

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects` | Create project |
| `GET` | `/projects` | List all user projects |
| `GET` | `/projects/{id}` | Get project |
| `PATCH` | `/projects/{id}` | Update name/description |
| `DELETE` | `/projects/{id}` | Delete project |

### Datasets

| Method | Path | Description |
|---|---|---|
| `POST` | `/datasets/upload` | Upload file (multipart). Body: `project_id` + `file`. Returns `{dataset_id, job_id}`. |
| `GET` | `/projects/{id}/datasets` | List datasets for project |
| `GET` | `/datasets/{id}` | Get dataset metadata |
| `GET` | `/datasets/{id}/versions` | List all versions (v0 = raw, v1+ = after cleaning) |
| `GET` | `/datasets/{id}/preview` | First 100 rows of latest version as JSON |
| `GET` | `/datasets/{id}/profile` | Profiling results (column stats) |

### AI Analysis

| Method | Path | Description |
|---|---|---|
| `POST` | `/ai/datasets/{id}/analyze` | Trigger AI analysis. Returns `{job_id}`. |
| `GET` | `/ai/datasets/{id}/insights` | Get analysis results (task type, target column, cleaning suggestions, model recommendations) |

### EDA

| Method | Path | Description |
|---|---|---|
| `POST` | `/eda/datasets/{id}/compute` | Trigger EDA computation. Returns `{job_id}`. |
| `GET` | `/eda/datasets/{id}` | Get chart data (distributions, correlation matrix, missing heatmap) |

### Cleaning

| Method | Path | Description |
|---|---|---|
| `POST` | `/cleaning/datasets/{id}/propose` | Propose a cleaning action (preview only, no data change). Body: `{action_type, parameters}` |
| `POST` | `/cleaning/actions/{id}/apply` | Apply an approved action. Creates new DatasetVersion. Returns `{job_id}`. |
| `GET` | `/cleaning/datasets/{id}/actions` | List all cleaning actions and their status |

### Pipelines

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/{id}/pipelines` | Create pipeline |
| `GET` | `/projects/{id}/pipelines` | List pipelines |
| `GET` | `/pipelines/{id}` | Get pipeline with nodes and edges |
| `PUT` | `/pipelines/{id}` | Save pipeline (nodes + edges) |
| `POST` | `/pipelines/{id}/validate` | Validate DAG (checks for cycles, disconnected nodes, missing required ports) |
| `POST` | `/pipelines/{id}/execute` | Execute pipeline. Returns `{job_id}`. |

### Training

| Method | Path | Description |
|---|---|---|
| `POST` | `/training/start` | Start training. Body: `{dataset_version_id, model_type, target_column, task_type}`. Validates target column exists before queuing. Returns `{training_run_id, job_id}`. |
| `GET` | `/projects/{id}/training/runs` | List all training runs for a project |
| `GET` | `/training/runs/{id}` | Get run with embedded metrics |
| `GET` | `/training/runs/{id}/metrics` | Get all metric records |
| `GET` | `/training/runs/{id}/feature-importance` | Get feature importance list (sorted descending) |
| `GET` | `/training/runs/{id}/summary` | Get AI experiment summary (calls OpenAI) |
| `GET` | `/training/runs/{id}/download` | Get presigned download URL for trained model `.joblib` file (5-minute TTL) |
| `POST` | `/training/compare` | Compare multiple runs. Body: `{run_ids: [...]}` (2–5 runs). |

### Jobs

| Method | Path | Description |
|---|---|---|
| `GET` | `/jobs` | List all jobs for current user |
| `GET` | `/jobs/{id}` | Get job status: `queued`, `running`, `succeeded`, `failed` |

Full interactive docs at http://localhost:8000/docs

---

## Database Schema

5 migrations, 15 tables total.

```
users
└── projects
    ├── datasets
    │   └── dataset_versions           ← v0 = raw upload; v1+ = post-cleaning
    │       ├── dataset_profiles       ← async profiling results
    │       │   └── dataset_column_profiles  ← per-column stats
    │       ├── cleaning_actions       ← proposed/approved/applied/rejected
    │       │   └── cleaning_executions
    │       └── (referenced by training_runs)
    ├── pipelines
    │   ├── pipeline_nodes
    │   └── pipeline_edges
    ├── training_runs                  ← one per model training job
    │   └── training_metrics           ← one row per metric (accuracy, f1, rmse, etc.)
    ├── artifacts                      ← model .joblib files stored in MinIO
    ├── jobs                           ← tracks all async operations
    └── ai_insights                    ← stores OpenAI analysis results
```

JSONB columns used for: profiling summaries, column profile distributions, AI metadata, cleaning parameters, pipeline node configs, model hyperparameters, feature importance lists.

---

## Troubleshooting

### Services won't start

```bash
# Check what's wrong
docker compose ps
docker compose logs postgres
docker compose logs redis
docker compose logs minio
```

Port conflicts: If 5432, 6379, 9000, 8000, or 3000 are in use on your machine, stop whatever is using them or edit the port mappings in `docker-compose.yml`.

### "automl-files" bucket not found

The backend tries to create the bucket at startup but may fail if MinIO isn't ready yet. Run:

```bash
make create-bucket
```

Then restart the backend:

```bash
docker compose restart backend worker
```

### AI features return empty / no suggestions

Check that `OPENAI_API_KEY` is set correctly in `.env`:

```bash
grep OPENAI_API_KEY .env
```

In Docker, the compose file reads this from the host shell environment. Verify it reached the container:

```bash
docker compose exec backend env | grep OPENAI
```

If empty, restart after setting the key:

```bash
docker compose up -d backend worker
```

### Training jobs fail immediately

Check the worker logs:

```bash
docker compose logs worker
```

Common causes:
- Target column name typo — the backend now validates this before queuing, but old runs may have failed silently
- Dataset format issue — open the dataset workspace and check the preview tab
- MinIO connectivity — verify `make create-bucket` succeeded

### Model download button opens unreachable URL

This happens when `MINIO_PUBLIC_ENDPOINT` is not set. The presigned URL uses the internal Docker hostname `minio:9000` which the browser can't reach.

Verify `.env` has:
```
MINIO_PUBLIC_ENDPOINT=localhost:9000
```

Then restart:
```bash
docker compose restart backend
```

### Frontend shows "Network Error" or blank pages

Check `NEXT_PUBLIC_API_URL` in `.env`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Verify the backend is running:
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### Database migration errors

If migrations fail (e.g., table already exists):

```bash
make shell-backend
alembic current       # see current revision
alembic history       # see all revisions
alembic upgrade head  # retry
```

To reset the database completely (destroys all data):

```bash
docker compose down -v     # removes volumes
docker compose up -d postgres redis minio
make migrate
make create-bucket
```

---

## Build Phases

| Phase | Status | Contents |
|---|---|---|
| Phase 1 | ✅ Complete | Auth, project management, dataset upload, async profiling, dataset workspace |
| Phase 2 | ✅ Complete | AI analysis (OpenAI gpt-4o-mini), EDA charts, AI sidebar |
| Phase 3A | ✅ Complete | Cleaning engine (9 transforms), NL command interface, preview/confirm/apply |
| Phase 3B | ✅ Complete | Pipeline builder (React Flow canvas, 8 node types, DAG validation) |
| Phase 4 | ✅ Complete | Model training (6 model types), metrics dashboard, feature importance, AI experiment summary |
| Phase 5 | ✅ Complete | Model download (presigned URL), input validation, frontend error UX |

---

## Known Limitations (MVP)

- **No SHAP explainability** — feature importance (from `feature_importances_` / `coef_`) is available; SHAP requires a separate worker pass
- **No hyperparameter tuning UI** — sensible defaults are used for all model types
- **No cleaned dataset export** — only the trained model artifact can be downloaded
- **Single train/test split** — 80/20, no cross-validation
- **No rate limiting** — not needed at local/demo scale
- **No audit log** — job history is available but not a dedicated audit trail
- **CORS locked to localhost:3000** — change `allow_origins` in `main.py` for other origins
