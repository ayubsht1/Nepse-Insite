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
  jobs, synchronous collection commands, and crawl-run records.
- `apps/analytics`: VWAP, estimated close-location pressure, volume anomaly,
  broker, and news/price comparison services.
- `config`: Django settings, Celery, Channels consumer and JWT WebSocket auth.

## Docker Compose stack

The root `docker-compose.yml` runs Nginx, Next.js, Django/Daphne, Redis, two
Celery workers, and one Celery Beat scheduler. Nginx is the only published
service; PostgreSQL is external Supabase. Follow the environment preparation
and deployment steps in the root [README](../README.md). From the repository
root:

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f nginx backend celery-worker-1 celery-worker-2 celery-beat
```

The backend runs migrations and collects static assets before Daphne serves
requests. The frontend calls `/api/` and opens WebSockets at `/ws/` on the same
origin. Nginx routes `/api/` and `/admin/` to Django, `/static/` and `/media/`
to shared volumes, `/ws/` to Daphne with upgrade headers, and all other paths
to Next.js. Redis, frontend, backend, and Celery services are not published.
Create an initial Django administrator with:

```powershell
docker compose exec backend python manage.py createsuperuser
```

Only one Beat instance should run. Redis data, Beat's schedule, and uploaded
media use named volumes; production hosts must retain these volumes across
container replacements. The frontend API base is relative and requires no
backend URL build configuration. With the example local port mapping, the
application is at `http://localhost:8080`; use the platform's HTTPS domain in
production. No backend or Redis port is publicly mapped.

## Native local setup

For native backend-only development, supply a development `DATABASE_URL` (or
omit it to use the local SQLite fallback) and start a local Redis instance:

```powershell
Copy-Item backend\.env.example backend\.env
docker run --rm --name nepse-redis -p 6379:6379 redis:7-alpine
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

SQLite is a local test fallback. PostgreSQL/Supabase and Redis are expected for
deployment. For the integrated browser experience, use the Compose Nginx
entry point so same-origin API and WebSocket routing is available.

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

## Listed company directory

The `sync_sharesansar_company_directory` service adds actual company names,
symbols, and sectors from ShareSansar's public company list; it does not create
prices or floorsheet transactions. It is included in `historical_market`,
before company-history collection, and remains callable through the legacy
`company-directory` operation. This public page is not a documented API;
review its terms and robots directives before production use.

## Environment and deployment

| Variable | Purpose |
|---|---|
| Root `.env` `DJANGO_SECRET_KEY` | Unique random signing key; production requires at least 50 characters. |
| Root `.env` `DATABASE_URL` | Supabase Session Pooler URI (`aws-0-ap-northeast-1.pooler.supabase.com:5432`) with `sslmode=require`; URL-encode special password characters. |
| Root `.env` `REDIS_PASSWORD` | URL-safe password for internal Redis and its Celery/Channels URLs. |
| Root `.env` `PUBLIC_APP_URL` | Public HTTPS origin for the single-domain deployment. |
| Root `.env` `ALLOWED_HOSTS` | Comma-separated public hostname(s), including localhost for health checks. |
| Root `.env` `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | Allowed origin(s), including scheme. Same-origin browser requests need no cross-site CORS. |
| Root `.env` `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_HSTS_SECONDS`, `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD` | Production HTTPS and HSTS policy; enable subdomain/preload policies only when appropriate for the domain. |
| Root `.env` `CRAWLER_USER_AGENT` | Identifiable crawler contact information. |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Internal URLs assembled by Compose; do not publish Redis. |

Never commit environment files or credentials. Production requires a strong
secret, explicit hosts, TLS-terminated HTTPS, trusted forwarded-protocol
headers, TLS database connections, internal Redis, secure cookies, and
persistent media/Redis/Beat volumes. Compose runs migrations and static-file
collection at backend startup.

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
| `GET` | `/api/companies/{id}/prices/?range=30d` | Authenticated | Historical OHLCV and provider-reported daily changes; `range` supports day ranges, `1y`, `all`, optional `from`/`to`. |
| `GET` | `/api/companies/{id}/behavior-summary/?range=30d` | Authenticated | Recorded price, VWAP, pressure estimate, anomaly, broker, and news observations. |
| `GET` | `/api/companies/compare/?ids=1,2&range=30d` | Authenticated | Compare 2–10 companies. |
| `GET` | `/api/market-data/prices/?company_id=1` | Authenticated | Paginated daily price rows. |
| `GET` | `/api/market-data/floorsheet/?company_id=1` | Authenticated | Paginated transaction/broker rows. |
| `GET` | `/api/market-data/analysis/?range=30d` | Authenticated | Latest sourced market summary and daily NEPSE history; `range` supports `7d`, `15d`, `30d`, `90d`, `180d`, `1y`, and `all`. |
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

On Render, GitHub Actions invokes
`python manage.py run_collection news`; the command executes crawler tasks
synchronously and does not enqueue through Redis. The admin crawl endpoint
dispatches that workflow and the command updates its `CrawlRun` records.
Scheduled news does not depend on stored run IDs: it executes queued runs and
creates new `CrawlRun` rows for enabled sources that have no queued run.
Explicit `--run-ids` values remain supported for admin/manual operations and
must identify existing queued records; missing IDs are reported explicitly.
The workflow omits `--run-ids` when its input is blank, so database resets do
not leave scheduled jobs tied to stale IDs.
Local Compose retains the existing Celery Beat schedule for enabled sources.
Redis connectivity and task autodiscovery were verified locally; no real source
crawl was run and no live article persistence is claimed. Import genuine OHLCV and floorsheet data
only from verified, licensed providers. The seed command's demo records are
fictional and separately marked. The frontend and APIs report unavailable
genuine data rather than making it up.

## Market collection

The unified command executes the existing services directly and synchronously;
it does not enqueue tasks or require a Render Celery worker. Supported
operations are:

| Operation | Work performed |
|---|---|
| `news` | Enabled news crawlers; reuses queued runs and creates a run only when no queued run exists for that source. |
| `live_market` | NEPSE Alpha, ShareSansar, Merolagani market snapshots, and Merolagani floorsheet; then analysis if a source succeeds. |
| `historical_market` | Company directory, ShareSansar index history, company OHLCV/floorsheet history; then analysis if a source succeeds. |
| `market_analysis` | Summarizes saved market data; skips clearly if no usable records exist. |
| `all` | Runs news, live market, historical market, and analysis in dependency order, continuing after a source/operation failure and reporting failures at the end. |

Run any operation from this directory with `python manage.py run_collection
<operation>`. For news, optional `--source-keys key1,key2` selects enabled
crawler keys. For market operations, optional
`--market-source-keys nepsealpha,sharesansar,merolagani` selects providers;
provider-specific history keys are also accepted. Optional `--run-ids 1,2` is
reserved for explicit queued news runs and rejects IDs that do not exist;
scheduled workflow calls omit it. `--source-keys` and `--run-ids` cannot be
used together. The command uses a
PostgreSQL advisory lock to reject overlapping jobs and creates
`CrawlRun` records for each source with status, timestamps, record counters,
and error details. Provider network errors receive bounded retries; one
provider failure does not stop the remaining providers.

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

GitHub Actions runs `live_market` every 15 minutes Sunday–Thursday from
11:00–15:00 NPT (UTC 05:15–09:15) and `historical_market` at 15:05 NPT (UTC
09:20). News runs every four hours. The workflow is serialized at repository
scope, and the command also acquires a PostgreSQL advisory lock. Local Compose
retains its separate Celery Beat schedule. Tasks avoid requests outside
market hours; ShareSansar/Merolagani tasks also stop for the day after NEPSE
Alpha reports the market closed. Merolagani floorsheet rows are collected on
the live schedule and deduplicated by transaction ID. Its public page currently exposes a
paginated first page of up to 500 transactions; VWAP and broker statistics use
the rows actually stored and report this coverage limitation. ShareSansar's
NEPSE index-history page is queried daily for up to ten years; historical rows
are saved only when the provider returns valid records. Snapshot uniqueness and
timestamp uniqueness prevent duplicate daily/index-history records.

Complete company OHLCV rows are matched to active company records by symbol and
upserted by `(company, date)`. NEPSE Alpha takes precedence over ShareSansar,
then Merolagani, for conflicting same-day company prices; lower-priority
sources still fill gaps. Unmatched symbols and invalid/incomplete OHLCV are
logged and skipped rather than creating synthetic companies or prices.
Provider-reported price changes are retained when available. Daily index
history accumulates from snapshots and valid ShareSansar historical responses;
no values are backfilled or synthesized when source data is absent.

The inspected Merolagani market page did not expose a populated index table, so
its index, sector, and whole-market totals are not collected. Bizmandu is
configured as a news source only; no structured public quote/index endpoint was
confirmed. ShareSansar/Merolagani HTML parsing is limited to fields present in
their market pages. Per-provider snapshots remain separate; the overview
presents each provider's latest quotes while company price records select the
highest-priority available source.

`MarketSnapshot` and other source rows retain provider/source timestamps.
`/api/market-data/analysis/` computes NEPSE history and market metrics from
stored records, and reports freshness as unavailable/fresh/stale using a
24-hour threshold. Missing fields are not synthesized. The frontend displays
empty states when the API has no source data.

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

Connect through the same public origin at `/ws/updates/` with an access token in the
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
