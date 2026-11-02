# NEPSE Insight backend

Django REST Framework API for sourced company, market, and news records. It
does not ship fabricated prices, floorsheets, articles, or analysis.

## Architecture

- `apps/users`: Viewer/Analyst/Admin application roles and watchlists.
- `apps/companies`: company directory and company-level prices/analysis APIs.
- `apps/market_data`: OHLCV and transaction-level floorsheet storage/import.
- `apps/news`: articles, deterministic company tagging, corrections/history.
- `apps/crawlers`: source configuration, HTTPX/BeautifulSoup crawler, Celery
  jobs and crawl-run records.
- `apps/analytics`: VWAP, estimated close-location pressure, volume anomaly,
  broker, and news/price comparison services.
- `config`: Django settings, Celery, Channels consumer and JWT WebSocket auth.

## Local setup

From the repository root in PowerShell:

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up -d postgres redis
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Push-Location backend
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
Pop-Location
```

`createsuperuser` runs interactively; the repository contains no initial
administrator credentials. A new superuser has Django `is_staff` and
`is_superuser` privileges for Django Admin and receives the independent
application role `Admin` when its profile is created. Public registrations
remain `Viewer`.

Run Celery worker and Beat from `backend\` in separate terminals:

```powershell
.\.venv\Scripts\celery.exe -A config worker --pool=solo --loglevel=info
.\.venv\Scripts\celery.exe -A config beat --loglevel=info
```

For WebSockets, serve `config.asgi:application` with Daphne:

```powershell
.\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

SQLite is a local test fallback. PostgreSQL/Supabase and Redis are expected for
deployment.

## Environment and deployment

Copy `backend\.env.example` to `backend\.env`.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django signing secret; set a unique strong value. |
| `DEBUG` | Development only; production settings force it off. |
| `ALLOWED_HOSTS` | Comma-separated Django hosts. |
| `DATABASE_URL` | PostgreSQL/Supabase connection URL; use TLS in production. |
| `REDIS_URL` | Channels Redis URL. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery Redis URLs. |
| `FRONTEND_URL` | CORS and CSRF trusted frontend origin. |
| `CRAWLER_USER_AGENT` | Identifiable crawler contact information. |
| `LOG_LEVEL` | Root application log level. |

Never commit environment files or credentials. Production requires a strong
secret, explicit hosts, HTTPS origins, TLS database connections, protected
Redis/network access, secure cookies, and supervised Daphne/Celery processes.
Run migrations before deployment. `docker-compose.yml` supplies local data
services, not a production deployment.

## Authentication and roles

Before cookie-backed auth operations, request `GET /api/auth/csrf/` and send
the `csrftoken` cookie value as `X-CSRFToken`.

- `POST /api/auth/register/`: username, first name, email, password; always
  creates a Viewer. Client-supplied role and Django privilege fields are not
  writable.
- `POST /api/auth/token/`: username/password; returns a short-lived access JWT
  and sets the refresh JWT in an HttpOnly, SameSite=Lax cookie.
- `POST /api/auth/token/refresh/`: refresh cookie + CSRF header; rotates the
  cookie and returns a new access token.
- `POST /api/auth/logout/`: authenticated access JWT + refresh cookie + CSRF;
  blacklists the refresh token. Existing access tokens expire within 30
  minutes.
- `GET /api/users/me/`: current user and application role.

REST requests use `Authorization: Bearer <access-token>`. Application
permissions use `UserProfile.role`, not Django staff/superuser flags. Trusted
Django Admin users manage profiles; application Admins may also change
application roles through the protected `/api/admin/users/` endpoint.

| Role | Application permissions |
|---|---|
| Viewer | Authenticated read-only data and own watchlist. |
| Analyst | Viewer access plus news tag corrections. |
| Admin | Company/user/crawl management and verified market-data imports. |

## REST endpoints

Except public auth issuance/registration/CSRF and OpenAPI docs, REST routes
require an access JWT. List endpoints use DRF page-number pagination:
`{"count":...,"next":...,"previous":...,"results":[...]}`. Invalid fields
return standard DRF validation errors.

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/companies/` | Authenticated | Paginated companies; search, sector, active filters. |
| `GET` | `/api/companies/{id}/` | Authenticated | Company details. |
| `POST/PATCH/DELETE` | `/api/companies/`, `/api/companies/{id}/` | Admin | Company directory administration. |
| `GET` | `/api/companies/{id}/prices/?range=30d` | Authenticated | Historical OHLCV; `range` supports day ranges, `1y`, `all`, optional `from`/`to`. |
| `GET` | `/api/companies/{id}/behavior-summary/?range=30d` | Authenticated | Recorded price, VWAP, pressure estimate, anomaly, broker, and news observations. |
| `GET` | `/api/companies/compare/?ids=1,2&range=30d` | Authenticated | Compare 2–10 companies. |
| `GET` | `/api/market-data/prices/?company_id=1` | Authenticated | Paginated daily price rows. |
| `GET` | `/api/market-data/floorsheet/?company_id=1` | Authenticated | Paginated transaction/broker rows. |
| `POST` | `/api/market-data/admin/prices/import/` | Admin | Import validated OHLCV; `(company,date)` upserts. |
| `POST` | `/api/market-data/admin/floorsheet/import/` | Admin | Import transaction rows with deduplication by source record ID. |
| `GET` | `/api/news/?company_id=1&search=...` | Authenticated | Paginated articles and multi-company tags. |
| `GET` | `/api/news/{id}/` | Authenticated | Article and tag details. |
| `POST` | `/api/news/{id}/classify/` | Analyst/Admin | Run deterministic symbol/name/alias matcher. |
| `POST` | `/api/news/{id}/recategorize/` | Analyst/Admin | Replace tags and append correction history. |
| `GET` | `/api/news/{id}/corrections/` | Authenticated | Paginated correction history. |
| `GET/POST/DELETE` | `/api/users/watchlists/` | Authenticated | Caller-owned watchlists; admin can filter by user. |
| `GET/POST/PATCH/DELETE` | `/api/admin/users/` | Admin | User and application-role management. |
| `GET/POST` | `/api/admin/crawl-runs/` | Admin | List runs or queue enabled sources; POST accepts `{"source_ids":[1,2]}`. |
| `GET` | `/api/admin/crawl-runs/{id}/` | Admin | Run status, counters, and error details. |
| `GET/POST/PATCH/DELETE` | `/api/admin/crawl-sources/` | Admin | Configure source URLs and article URL patterns. |
| `GET` | `/api/schema/`, `/api/docs/`, `/api/redoc/` | Public | OpenAPI schema, Swagger UI, and ReDoc. |

Correction request:

```json
{
  "tags": [{"company_id": 1, "confidence_score": "0.850"}],
  "note": "The article names this issuer in the body."
}
```

News article responses include `id`, `url`, `source`, `headline`, `body`,
`published_at`, `collected_at`, and `company_tags`. A tag contains company
details, `confidence_score`, `method` (`rule` or `analyst`), and
`updated_at`. Missing publication dates are `null`.

## Crawling and source restrictions

Migrations register Merolagani, ShareSansar, NEPSE Alpha, and Bizmandu as
**disabled** sources. Verify current publisher terms and `robots.txt` before
enabling; configure the true listing URL, narrow article URL pattern, and
operator contact. The crawler checks robots rules, fails closed, enforces
same-host links/redirects, honors crawl delay, bounds article count, extracts
headline/body/date when present, and deduplicates canonical article URLs.
New articles are classified and emitted as Channels events.

Celery Beat schedules enabled sources every four hours. Source-specific listing
URLs/selectors are intentionally not guessed. No one-month OHLCV or sample
floorsheet provider/data is configured; import only verified, licensed
records. The frontend and APIs report unavailable data rather than making it
up.

## Market calculations and limits

- **VWAP:** `sum(price × quantity) / sum(quantity)` over recorded
  transaction-level floorsheet rows. No rows => unavailable; OHLCV is not a
  substitute.
- **Pressure:** `(2 × close − high − low) / (high − low)`, bounded to `[-1,1]`.
  This is a close-location estimate, not actual buy/sell quantity.
- **Volume anomaly:** flag only when current volume is strictly over 2× the
  mean of the prior 20 recorded trading-day rows. Fewer rows => unavailable.
- **Broker breakdown:** aggregates supplied buyer/seller codes in recorded
  floorsheet rows only.
- **News/trading comparison:** compares prior and next recorded sessions around
  publication; observational only and not causal.

Rule-based categorization checks word-boundary occurrences in headline/body:
symbol matches score `0.980`, company-name matches `0.900`, aliases `0.800`.
These deterministic weights are not calibrated probabilities. Corrections
record previous/current tags, analyst, note, and timestamp.

## WebSocket event contract

Connect through Daphne to `ws://localhost:8000/ws/updates/` with an access token in the
WebSocket subprotocols `nepse-insight` and
`nepse-insight.bearer.<access-token>`; use `wss://` in production. Do not send
tokens in the URL. Invalid/expired tokens are rejected with close code `4401`.

```json
{
  "event": "news.article.created",
  "occurred_at": "2026-11-02T08:00:00+00:00",
  "data": {"article_id": 12, "headline": "Article headline"}
}
```

Events: `news.article.created`, `news.categorization.updated`,
`crawl.run.updated`, `market.prices.updated`, and
`market.floorsheet.updated`. Consumers should invalidate corresponding
news/company/crawl queries after receiving an event.

## Tests and checks

Run from the repository root:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe manage.py test tests
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
Pop-Location
```

Tests use isolated databases and mocked crawler HTTP. They do not crawl public
sites or insert production/sample market data. Run tests against PostgreSQL as
well before deployment.
