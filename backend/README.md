# NEPSE Insight API

Django REST backend for NEPSE Insight. The project stores sourced market/news records and exposes analysis only when its required source data is present. It does not seed market prices, floorsheets, news, or analytics.

## Architecture

- `config/settings/`: shared, development, and production settings.
- `apps/companies/`: company directory.
- `apps/market_data/`: daily OHLCV and transaction-level floorsheet records.
- `apps/news/`: collected articles, multi-company tags, classifier, and analyst correction history.
- `apps/crawlers/`: source configuration, crawl-run monitoring, HTTPX/BeautifulSoup crawler, and Celery tasks.
- `apps/analytics/`: read-time analysis services; values are not persisted or approximated when inputs are missing.
- `apps/users/`: user roles and per-user company watchlists.
- `common/`: permissions, API date-range parsing, and Channels event publishing.
- `config/consumers.py`: authenticated WebSocket update consumer.

## Requirements and local setup

Python 3.12+, Docker Compose (or externally hosted PostgreSQL/Redis), and the backend virtual environment are required. From the repository root in PowerShell:

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up -d postgres redis
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\backend\.venv\Scripts\python.exe backend\manage.py migrate
.\backend\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\backend\.venv\Scripts\python.exe backend\manage.py runserver
```

In another terminal, from the `backend\` directory:

```powershell
.\.venv\Scripts\celery.exe -A config worker --pool=solo --loglevel=info
```

In a separate terminal, also from `backend\`:

```powershell
.\.venv\Scripts\celery.exe -A config beat --loglevel=info
```

`--pool=solo` is suitable for local Windows development. For an ASGI server (needed for WebSockets), run Daphne from `backend\`:

```powershell
.\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

The SQLite fallback is intended for basic local checks only. PostgreSQL is the supported application database.

## Environment

Copy `backend\.env.example` to `backend\.env`. Important settings:

| Variable | Purpose |
|---|---|
| `DEBUG` | Django debug mode; disable in production. |
| `SECRET_KEY` | Django signing secret; provide a unique secret outside local development. |
| `ALLOWED_HOSTS` | Comma-separated Django host allow-list. |
| `DATABASE_URL` | PostgreSQL/Supabase URL; include `?sslmode=require` for hosted TLS endpoints. |
| `REDIS_URL` | Channels Redis connection. |
| `CELERY_BROKER_URL` | Celery broker connection. |
| `CELERY_RESULT_BACKEND` | Celery result backend connection. |
| `FRONTEND_URL` | Allowed CORS and CSRF origin. |
| `CRAWLER_USER_AGENT` | Identifiable crawler User-Agent; configure real operator contact details before enabling a public source. |
| `LOG_LEVEL` | Root application log level. |

Never commit `backend\.env` or credentials. For Supabase, use a PostgreSQL connection string with TLS required and the connection/pooler endpoint recommended for the deployment.

## Database and migrations

For local PostgreSQL/Redis:

```powershell
docker compose up -d postgres redis
.\backend\.venv\Scripts\python.exe backend\manage.py migrate
```

Set `DATABASE_URL` to the Supabase PostgreSQL connection string for hosted use. Migrations create the domain tables and register four known news domains as **disabled** crawl sources. No historical OHLCV, transaction, or article data is included. Check the setup with:

```powershell
.\backend\.venv\Scripts\python.exe backend\manage.py check
.\backend\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
```

## Authentication and roles

Obtain JWTs using `POST /api/auth/token/` with `{"username":"...","password":"..."}` and refresh using `POST /api/auth/token/refresh/`. Send `Authorization: Bearer <access-token>` on REST requests.

New users default to `viewer`. The initial Django superuser receives the `admin` role. Admins can manage users and roles at `/api/admin/users/`; analysts can be assigned with `PATCH /api/admin/users/{id}/` and `{"role":"analyst"}`. Roles are enforced on the API:

- **Admin:** manage companies, users, watchlists, crawl sources/runs, and market-data imports.
- **Analyst:** read permitted data and create news categorization corrections.
- **Viewer:** authenticated read-only access to market/news endpoints and their own watchlist.

## REST endpoints

All REST routes below require a bearer token except JWT issuance/refresh, schema, Swagger, and ReDoc. List endpoints use page-number pagination (`count`, `next`, `previous`, `results`); validation errors use standard DRF `{"field":["message"]}` responses.

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/companies/` | Authenticated | Paginated company listing; supports `search`, `sector`, `is_active`, `ordering`. |
| `GET` | `/api/companies/{id}/` | Authenticated | Company details. |
| `POST/PATCH/DELETE` | `/api/companies/` or `/api/companies/{id}/` | Admin | Company directory administration. |
| `GET` | `/api/companies/{id}/prices/?range=30d` | Authenticated | Company OHLCV history, newest first; accepts `7d`, `30d`, `90d`, `1y`, `all`, optional `from`/`to` dates. |
| `GET` | `/api/companies/{id}/behavior-summary/?range=30d` | Authenticated | Summary of recorded prices, measured floorsheet VWAP, estimated close-location pressure, volume anomaly, brokers, and news observations. |
| `GET` | `/api/companies/compare/?ids=1,2&range=30d` | Authenticated | Compare 2–10 company summaries. |
| `GET` | `/api/market-data/prices/?company_id=1` | Authenticated | Paginated daily price records. |
| `GET` | `/api/market-data/floorsheet/?company_id=1&trade_date=YYYY-MM-DD` | Authenticated | Paginated recorded transactions, including broker codes where supplied. |
| `POST` | `/api/market-data/admin/prices/import/` | Admin | Import verified OHLCV records; unique `(company, date)` records are updated idempotently. |
| `POST` | `/api/market-data/admin/floorsheet/import/` | Admin | Import verified transactions; requires stable source record IDs and skips duplicates. |
| `GET` | `/api/news/?company_id=1&search=...` | Authenticated | Paginated articles and company tags. |
| `GET` | `/api/news/{id}/` | Authenticated | Article and tag details. |
| `POST` | `/api/news/{id}/classify/` | Analyst/Admin | Run the explainable alias/name/symbol matcher. |
| `POST` | `/api/news/{id}/recategorize/` | Analyst/Admin | Replace tags and append immutable correction history. |
| `GET` | `/api/news/{id}/corrections/` | Authenticated | Paginated analyst correction history. |
| `GET` | `/api/users/me/` | Authenticated | Current user and assigned role. |
| `GET/POST/DELETE` | `/api/users/watchlists/` | Authenticated | Read or change the caller's company watchlist; admins may filter by `user_id`. |
| `GET/POST/PATCH/DELETE` | `/api/admin/users/` | Admin | User and role administration. |
| `GET/POST` | `/api/admin/crawl-runs/` | Admin | Monitor runs or queue enabled sources; POST accepts optional `{"source_ids":[1,2]}`. Returns `202` with queued run records. |
| `GET` | `/api/admin/crawl-runs/{id}/` | Admin | Inspect a crawl run and its status/counts/errors. |
| `GET/POST/PATCH/DELETE` | `/api/admin/crawl-sources/` | Admin | Configure, enable, and manage news source URLs and article URL patterns. |
| `GET` | `/api/schema/` | Public | OpenAPI schema. |
| `GET` | `/api/docs/` | Public | Swagger UI. |
| `GET` | `/api/redoc/` | Public | ReDoc. |

Example correction request:

```json
{
  "tags": [{"company_id": 1, "confidence_score": "0.850"}],
  "note": "The article names this issuer in the body."
}
```

Example article representation:

```json
{
  "id": 12,
  "url": "https://publisher.example/article/12",
  "source": "Publisher",
  "headline": "Article headline",
  "body": "Publisher-sourced article body or excerpt.",
  "published_at": null,
  "collected_at": "2026-11-02T08:00:00Z",
  "company_tags": [
    {
      "company": {"id": 1, "symbol": "NABIL", "name": "Nabil Bank Limited"},
      "confidence_score": "0.980",
      "method": "rule",
      "updated_at": "2026-11-02T08:00:01Z"
    }
  ]
}
```

The example is a response-shape illustration, not stored platform data.

## Crawling and scheduled tasks

Four domains are seeded as disabled configuration records: Merolagani, ShareSansar, NEPSE Alpha, and Bizmandu. Before enabling a source, verify its current terms and `robots.txt`, configure its actual listing URL and a narrow article URL regular expression, and set a descriptive `CRAWLER_USER_AGENT`. The HTTPX/BeautifulSoup crawler:

- checks `robots.txt` for listing and article URLs, fails closed on robots/network errors, enforces same-host links/redirects, and honors the maximum of source and robots crawl delays;
- bounds requests per run, extracts title/body/date when present, records missing publication dates as `null`, and deduplicates on canonical article URL;
- automatically applies the deterministic company symbol/name/alias matcher to newly collected articles;
- records queued/running/succeeded/partial/failed runs, request counts, created/duplicate article counts, errors, retries, and status events.

Celery Beat schedules enabled sources every four hours. Crawl data are not collected until sources are explicitly configured and enabled; this avoids assuming selectors or bypassing publisher restrictions.

## Market analysis and data limitations

- **VWAP:** `sum(transaction price × quantity) / sum(quantity)` using only recorded transaction-level floorsheet rows. If none exist, the API returns `available: false` and `value: null`; OHLCV is never used as an exact substitute.
- **Buy/sell pressure:** the close-location indicator `(2 × close − high − low) / (high − low)`, bounded to `[-1, 1]`, multiplied by no estimated trade shares. It is an OHLCV-derived direction proxy, not actual buyer/seller volume.
- **Volume anomaly:** current daily volume is flagged only when it is strictly greater than 2× the mean of the preceding 20 recorded trading-day rows. Fewer than 20 rows yields `available: false`.
- **Broker breakdown:** groups recorded floorsheet quantities and turnover by the supplied buyer/seller broker codes. Missing data returns unavailable, not zero-valued claims.
- **News/market observations:** each tagged article is compared with the last recorded price date before publication and the next recorded price date after publication. This handles weekends/holidays based on observed market rows; it does not prove causation.

No verified one-month OHLCV or floorsheet provider has been configured or supplied in this repository. Authorized admins can import sourced records through the market-data import endpoints; responses and analysis reflect only those records. There are no observed news/market findings until real source data have been collected/imported.

## Categorization and corrections

The initial matcher case-insensitively checks word-boundary matches of each active company's symbol, name, and aliases against headline plus body. Symbol matches score `0.980`, company-name matches `0.900`, and alias matches `0.800`; symbol has precedence. These are deterministic rule scores, not calibrated ML probabilities. Analysts/admins may replace the article's full tag set; each change records the previous tags, new tags, user, note, and timestamp. Tags and corrections preserve history independently of the current tag set.

## WebSocket updates

Connect using an ASGI server to `ws://localhost:8000/ws/updates/?token=<JWT access token>` (use `wss://` in production). A valid authenticated viewer, analyst, or admin receives JSON envelopes:

```json
{
  "event": "news.article.created",
  "occurred_at": "2026-11-02T08:00:00+00:00",
  "data": {"article_id": 12, "headline": "Article headline"}
}
```

Events include `news.article.created`, `news.categorization.updated`, and `crawl.run.updated`. Invalid/expired credentials are rejected with close code `4401`. Because the token is sent in the URL, production proxies/access logs must redact the `token` query parameter; alternatively, a future frontend may use a negotiated secure WebSocket credential mechanism.

## Tests

Run from the repository root:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe manage.py test tests
Pop-Location
```

Tests use isolated fixtures and mocked HTTP; they do not crawl public sites or insert sample production data. PostgreSQL test execution is recommended alongside the SQLite default test database.

## OpenAPI and deployment

Set `DJANGO_SETTINGS_MODULE=config.settings.production`, a strong `SECRET_KEY`, correct `ALLOWED_HOSTS`, a TLS-enabled PostgreSQL URL, Redis URLs, CORS `FRONTEND_URL`, and a real crawler contact string in production. Run migrations before serving. Serve HTTP and WebSockets through an ASGI server such as Daphne; run Celery worker and Beat as separate supervised processes. Restrict PostgreSQL/Redis network access, use TLS for hosted connections, rotate secrets, and configure proxy logs to redact WebSocket tokens.

## Known limitations and integration notes

- Publisher-specific listing URLs and selectors are intentionally not guessed; enabled sources must be reviewed/configured, and markup changes may require parser adjustments.
- No historical market provider, broker directory, or supplied OHLCV/floorsheet dataset is present; import only licensed, provenance-tracked records.
- Matching is deterministic and may miss ambiguous references; scores are rule weights, not empirically validated probabilities.
- News-to-market comparisons are observational and based on available recorded dates, not a local exchange-holiday calendar or causal model.
- The frontend should use `/api` as the HTTP base URL, standard bearer JWT authentication, `range`/`from`/`to` query parameters, and append `updates/` to a WebSocket base of `ws://localhost:8000/ws`. Render unavailable analytics explicitly instead of substituting zero.
