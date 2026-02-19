# Status Page

Full-stack status dashboard for products and components, with automated health checks, historical daily summaries, and a management UI.

## What this application does

- Registers products (for example: Payments, Auth, Website).
- Registers components under each product (backend/frontend services).
- Periodically checks each component health URL.
- Computes and stores component status (`OPERATIONAL`, `DEGRADED`, `OUTAGE`).
- Aggregates daily health metrics (uptime, latency, check counts).
- Exposes REST APIs through FastAPI.
- Displays everything in an Angular dashboard with search, pagination, and CRUD modals.

## Architecture

The repository contains three main parts:

1. `backend/`: FastAPI + SQLAlchemy + APScheduler + structlog.
2. `frontend/`: Angular standalone app + Tailwind CSS.
3. `db/`: PostgreSQL initialization SQL.

With Docker Compose, the runtime topology is:

1. `postgres` (PostgreSQL 18)
2. `status_page_backend` (FastAPI on `:8080`)
3. `status_page_frontend` (Nginx + Angular on host `:4200`)

Request flow:

1. Browser calls frontend on `http://localhost:4200`.
2. Frontend calls `/py-status-page/...`.
3. Nginx proxies `/py-status-page/` to backend.
4. Backend reads/writes PostgreSQL and runs background health checks.

## Key behaviors

### Health checking

- A global sync job runs every `SYNC_INTERVAL_SECONDS` (default `60`) to refresh active components from DB.
- Each active component gets its own scheduled check job, using its `checkIntervalSeconds`.
- A check is healthy only when:
  - HTTP status matches `expectedStatusCode`, and
  - response time is `<= maxResponseTimeMs`.
- Failure logic:
  - below `failuresBeforeOutage` => `DEGRADED`
  - at/above `failuresBeforeOutage` => `OUTAGE`
- Success resets the failure counter and sets `OPERATIONAL`.
- Every check writes a log row in `health_checks`.

### Frontend dashboard

- Loads products in pages (`PAGE_SIZE = 10`) and supports "Load more".
- Auto-refreshes every 30 seconds.
- Supports product/component create, edit, and delete flows.
- Search filters currently loaded products/components client-side.
- Shows daily health bars per component (up to 100 days).

## API base path and docs

Backend is mounted with `ROOT_PATH=/py-status-page`.

- OpenAPI JSON: `http://localhost:8080/py-status-page/openapi`
- Swagger UI: `http://localhost:8080/py-status-page/apidocs`

## API summary

All JSON fields are camelCase in request/response payloads.

### Stats

- `GET /py-status-page/stats/health`

### Product

- `POST /py-status-page/product`
- `GET /py-status-page/product`
  - query: `is_visible` (default `true`), `page` (default `1`), `page_size` (default `10`), `summary_days` (default `100`, max `365`)
- `GET /py-status-page/product/{product_id}`
- `GET /py-status-page/product/name/{product_name}`
- `PATCH /py-status-page/product/{product_id}`
- `DELETE /py-status-page/product/{product_id}`

### Component

- `POST /py-status-page/component`
- `GET /py-status-page/component`
  - query: `product_id` (required), `page`, `page_size`, `summary_days`
- `PATCH /py-status-page/component/{component_id}`
- `DELETE /py-status-page/component/{component_id}`

## Data model

Main tables created in `db/init.sql`:

1. `products`
- identity `id`, unique `name`, `description`, visibility flag, timestamps.

2. `components`
- identity `id`, `product_id` FK, unique `name`, unique `health_url`.
- monitoring config fields:
  - `check_interval_seconds`
  - `timeout_seconds`
  - `expected_status_code`
  - `max_response_time_ms`
  - `failures_before_outage`
- current status and activity fields.

3. `health_checks`
- one row per check execution with status transition and metrics.

## Run with Docker Compose (recommended)

Prerequisite: Docker + Docker Compose.

From repository root:

```bash
docker compose up --build
```

Available endpoints after startup:

- Frontend: `http://localhost:4200`
- Backend docs: `http://localhost:8080/py-status-page/apidocs`
- Backend health: `http://localhost:8080/py-status-page/stats/health`

Stop:

```bash
docker compose down
```

## Local development

### Backend

Prerequisites:

- Python `3.14`
- Pipenv

Install dependencies:

```bash
cd backend
pipenv install --dev
```

Create `.env` (in `backend/`) for SQLite local mode:

```env
ENVIRONMENT=dev
DATABASE_CONFIG__DRIVER=sqlite
DATABASE_CONFIG__SQLITE_PATH=./status_page.db
LOGGING_CONFIG__LEVEL=INFO
LOGGING_CONFIG__JSON_FORMAT=false
SYNC_INTERVAL_SECONDS=60
```

Run API:

```bash
pipenv run dev
```

Notes:

- In `ENVIRONMENT=dev` (or `loc`), schema is auto-created on startup.
- Default CORS allows `http://localhost:4200` and `http://localhost:8000`.

### Frontend

Prerequisites:

- Node `24+`
- npm

Install and run:

```bash
cd frontend
npm ci
npm start
```

Development environment points API to `http://localhost:8080/py-status-page`.

## Tests

Backend:

```bash
cd backend
pipenv run pytest
```

Frontend:

```bash
cd frontend
npm test
```

Backend `pytest.ini` enforces coverage floor: `--cov-fail-under=65`.

## Configuration reference (backend)

Important environment variables:

- `APP_NAME` (default `py-status-page`)
- `VERSION` (from `backend/version.py`)
- `ENVIRONMENT` (`loc|dev|pre|pro`)
- `ROOT_PATH` (default `/py-status-page`)
- `HOST` (default `0.0.0.0`)
- `PORT` (default `8080`)
- `SYNC_INTERVAL_SECONDS` (default `60`)
- `DATABASE_CONFIG__DRIVER` (`postgres` or `sqlite`)
- `DATABASE_CONFIG__SQLITE_PATH`
- `DATABASE_CONFIG__USER`
- `DATABASE_CONFIG__PASSWORD`
- `DATABASE_CONFIG__HOST`
- `DATABASE_CONFIG__PORT`
- `DATABASE_CONFIG__DATABASE`
- `DATABASE_CONFIG__ECHO`
- `LOGGING_CONFIG__LEVEL`
- `LOGGING_CONFIG__JSON_FORMAT`
- `LOGGING_CONFIG__LIBRARY_LOG_LEVELS` (JSON string)

## Troubleshooting

- `422` on `PATCH /product/{id}` with empty body:
  - At least one field must be provided.
- `409` on component create/update:
  - Component `name` or `healthUrl` already exists.
- Backend startup error about missing DB fields:
  - Set `DATABASE_CONFIG__...` vars or switch to SQLite mode.
- Frontend cannot reach API in non-Docker mode:
  - Ensure backend is running on `http://localhost:8080` and `ROOT_PATH` is `/py-status-page`.

## Security note

The Compose setup uses default local credentials (`1234`) intended for development only.
