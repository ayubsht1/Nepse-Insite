# NEPSE Insight backend

Django REST Framework API for sourced company, market, and news records. It
does not ship fabricated prices, floorsheets, articles, or analysis.

## Architecture

- `apps/users`: Viewer/Analyst/Admin application roles and watchlists.
- `apps/companies`: company directory and company-level prices/analysis APIs.
- `apps/market_data`: source-backed NEPSE Alpha, ShareSansar, and Merolagani
  market snapshots, plus OHLCV and transaction-level floorsheet storage/import.
- `apps/news`: articles, deterministic company tagging, corrections/history.
- `apps/crawlers`: source configuration, HTTPX/BeautifulSoup crawler, Celery
  jobs and crawl-run records.
- `apps/analytics`: VWAP, estimated close-location pressure, volume anomaly,
  broker, and news/price comparison services.
- `config`: Django settings, Celery, Channels consumer and JWT WebSocket auth.

## Docker Compose stack

The root `docker-compose.yml` runs PostgreSQL, Redis, the Django/Daphne API,
Next.js, two Celery workers, and one Celery Beat scheduler. From the repository
root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f backend celery-worker-1 celery-worker-2 celery-beat
```

The backend runs migrations before serving. Create an initial Django
administrator with:

```powershell
docker compose exec backend python manage.py createsuperuser
```

The Compose stack uses development defaults from `.env.example`. Replace the
development Django key, database password, and crawler contact before using
outside a private development environment. The frontend API/WebSocket URLs are
build arguments, so rebuild the frontend after changing them:

```powershell
docker compose build frontend
docker compose up -d frontend
```

Services are available at `http://localhost:3000` (frontend),
`http://localhost:8000` (API/Admin), PostgreSQL port `5432`, and Redis port
`6379`. Compose runs two independent workers, each with concurrency 2, and one
Beat scheduler. Only one Beat service should run against this schedule.

## Native local setup

For running Django and Next.js outside Compose, start only PostgreSQL/Redis
from the repository root:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
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

In separate terminals, run the API with Daphne, two workers, and Beat from
`backend\`:

```powershell
.\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
.\.venv\Scripts\celery.exe -A config worker --loglevel=info --concurrency=2 --hostname=worker1@%h
.\.venv\Scripts\celery.exe -A config worker --loglevel=info --concurrency=2 --hostname=worker2@%h
.\.venv\Scripts\celery.exe -A config beat --loglevel=info
```

Run the frontend from another terminal:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

SQLite is a local test fallback. PostgreSQL/Supabase and Redis are expected for
deployment.

## Development demo seed

From `backend\`, after applying migrations to a development database:

```powershell
.\.venv\Scripts\python.exe manage.py seed
```

The command requires `DEBUG=True`, runs atomically, is repeatable, and uses
create-only defaults so existing rows are not overwritten or deleted. It adds
eight companies and 22 weekday OHLCV rows per company, six fictional news
articles and tags, 24 fictional floorsheet transactions, three demo role
accounts, and four sample crawl runs. Every sample is marked with a `DEMO`
source, `[DEMO]` headline, `.invalid` URL, or crawl-run message; none represents
a real price, transaction, publisher article, or network crawl. Demo users
have unusable passwords by default and do not receive Django staff or
superuser privileges. `--password` optionally sets a validated password for
new demo users only; it never changes existing credentials.

Do not run the seed against production. The development-only guard is not a
substitute for checking the selected database before running management
commands.

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
Run migrations before deployment. The Compose configuration and Dockerfiles are development deployment
conveniences, not production hardening.

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
| `GET` | `/api/market-data/analysis/` | Authenticated | Latest sourced market summary, index history, indices/sectors, provider-specific stock quotes, leaders, and available technical indicators. |
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

Migrations register the four requested sources as **disabled**, using these
listing URLs and article patterns:

| Source | Listing URL / template | Article URL pattern |
|---|---|---|
| Merolagani | `https://merolagani.com/NewsList.aspx` | `https://merolagani\.com/NewsDetail\.aspx\?newsID=\d+` |
| ShareSansar | `https://www.sharesansar.com/news-page` | `https://www\.sharesansar\.com/(index\.php/)?newsdetail/[\w-]+` |
| Bizmandu | `https://bizmandu.com/content/category/news.html` | `https://bizmandu\.com/content/\d+\.html` |
| NEPSE Alpha | `https://www.nepsealpha.com/all-news?cid=1&page={page}` | `https://(www\.)?nepsealpha\.com/news(-article\|/article)/[\w-]+` |

NEPSE Alpha pagination starts at page 1 and stops at the configured maximum
(10 by default), the article cap, or the first later listing page that adds no
new article links. The admin crawl-source API exposes the pagination template
and maximum pages. The migration updates only known prior defaults or blank
values, preserving custom source settings. These supplied patterns and paths
are configuration requests, not confirmation of current publisher terms,
robots permissions, page structure, or successful extraction. Verify the
publisher's terms, `robots.txt`, contact requirements, and page behavior before
enabling a source. The crawler checks robots rules on each listing and article
URL, supports the www/apex pair for one publisher host, enforces same-site
redirects, waits between requests, bounds pages and articles, extracts
headline/body/date when present, and deduplicates canonical article URLs.
Runs fail explicitly when no URLs match or no headline can be extracted;
permanent 4xx errors are not retried (429 and server/network errors may retry).
New articles are classified and emitted as Channels events.

Celery Beat schedules enabled sources every four hours. Redis connectivity and
task autodiscovery were verified locally; no real source crawl was run and no
live article persistence is claimed. Import genuine OHLCV and floorsheet data
only from verified, licensed providers. The seed command's demo records are
fictional and separately marked. The frontend and APIs report unavailable
genuine data rather than making it up.

## Market collection

Market-data collection is independent of the news crawler. It reads
`https://www.nepsealpha.com/live/stocks` for index/sector values, stock market
rows, breadth, turnover, leaders, and intraday NEPSE index points, and
`https://www.nepsealpha.com/trading-ta?frame=1D&symbol=NEPSE` for available
technical indicators. It also reads ShareSansar's `/market` and
`/today-share-price` pages for indices, market totals, and stock quotes, and
Merolagani's `/LatestMarket.aspx` page for stock quotes and leaders. The JSON
endpoints and HTML pages are public website resources, not documented or
guaranteed APIs; terms and response formats may change. Collection checks each
HTML provider's `robots.txt` before requesting its market pages.

Celery Beat schedules collection every 15 minutes Sunday–Thursday from 11:00
through 15:00 Asia/Kathmandu. Tasks avoid requests outside that window and the
ShareSansar/Merolagani tasks also stop for the day after NEPSE Alpha reports the
market closed. Technical indicators are retained across closed snapshots and
fetched when needed. Snapshot uniqueness and timestamp uniqueness prevent
duplicate daily/index-history records. The live endpoint currently provides
intraday history; daily history accumulates from collected snapshots rather
than being backfilled with invented values. The authenticated overview and
market ticker show sourced index/sector data, quote rows, and last-updated time.

The inspected Merolagani market page did not expose a populated index table, so
its index, sector, and whole-market totals are not collected. Bizmandu is
configured as a news source only; no structured public quote/index endpoint was
confirmed. ShareSansar/Merolagani HTML parsing is limited to fields present in
their market pages. Stock snapshots remain separate by provider and date; the
overview presents each provider's latest quotes without merging conflicting
prices.

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
