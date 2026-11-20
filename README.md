# NEPSE Insight

NEPSE Insight is a Next.js dashboard backed by Django REST Framework. It stores
provenance-tracked company, OHLCV, floorsheet, and news records; analytics are
computed only from data actually present. Optional development demo data is
created with `python manage.py seed` and is explicitly labeled as fabricated.

## Architecture

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, TanStack
  Query.
- **Backend:** Django 6, Django REST Framework, SimpleJWT, drf-spectacular.
- **Data:** PostgreSQL (or Supabase PostgreSQL); Redis for Celery and Channels.
- **Background work:** GitHub Actions runs scheduled/manual collection
  commands directly against PostgreSQL. Celery remains available for local
  Compose and explicitly bounded legacy-queue processing.
- **Real time:** authenticated Django Channels updates over ASGI/WebSockets.
- **Analysis:** Decimal-based calculations over stored OHLCV and floorsheet
  records; unavailable inputs are returned as unavailable.

## Single-platform Docker deployment

The root `docker-compose.yml` runs the application as one Compose deployment:
Nginx is the only published service and routes the same public origin to
Next.js, Django/Daphne, static files, media files, and WebSockets. The backend,
frontend, Redis, workers, and Beat share the private Compose network. Supabase
PostgreSQL remains external; Compose does not create a database service.

Use a Docker hosting platform that supports Compose (or an equivalent
multi-container application), TLS termination, environment variables, and
persistent Docker volumes. At the repository root, prepare the environment:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Set the generated value as `DJANGO_SECRET_KEY`, then edit `.env` and set the
Supabase Session Pooler `DATABASE_URL` on port `5432` using the connection
template in `.env.example`. URL-encode special characters in the database
password and retain `?sslmode=require`. Also set a URL-safe random
`REDIS_PASSWORD`, the public HTTPS `PUBLIC_APP_URL`, and the matching
`ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`. Never use
the example domain or leave secrets blank. Configure the platform to provide
HTTPS and pass the original `X-Forwarded-Proto` value to Nginx; Django uses it
to recognize secure requests and protect cookies. Keep only the Nginx service
public. Do not publish backend or Redis ports.

For a local HTTP smoke test, set `PUBLIC_APP_URL`,
`CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` to
`http://localhost:8080`, set `ALLOWED_HOSTS=localhost,127.0.0.1`, and set
`DJANGO_SECURE_SSL_REDIRECT=False` and `DJANGO_HSTS_SECONDS=0`. Restore HTTPS
origins and secure redirect before deployment.

Validate and start the stack:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

The backend runs migrations and `collectstatic` before starting Daphne. The
Compose stack starts two Celery workers (concurrency 2 each) and one Beat
scheduler, preserving the existing collection and crawler schedules. Beat's
schedule, Redis data, and uploaded media use named volumes; configure these as
persistent volumes on the hosting platform. Only one Beat instance should run
against this schedule.

With the local HTTP settings above, open `http://localhost:8080`. In
production, use the platform's HTTPS domain. The routes are `/` (Next.js),
`/api/` and `/admin/` (Django), `/static/` and `/media/` (Nginx file aliases),
and `/ws/` (Daphne WebSockets). API and WebSocket requests use same-origin
paths (`/api` and `/ws/updates/`); no public backend URL is built into the
frontend. Check proxy routes and service status with:

```powershell
curl.exe -I http://localhost:8080/
curl.exe -I http://localhost:8080/api/schema/
curl.exe -I http://localhost:8080/admin/login/
docker compose logs -f nginx backend celery-worker-1 celery-worker-2 celery-beat
```

Create the initial Django administrator interactively:

```powershell
docker compose exec backend python manage.py createsuperuser
```

The new superuser has Django `is_staff`/`is_superuser` privileges for Django
Admin and automatically receives the separate `Admin` application role.
Public registrations remain `Viewer`.

The demo seed command requires development settings and is unavailable in this
production Compose configuration. Company sync, crawler enablement, source
terms/robots review, and all existing market collection tasks remain managed
through their existing admin UI and Django management commands. Logs can be
reviewed with `docker compose logs`; do not run a second Beat scheduler.

For native development outside Compose, see
[backend/README.md](./backend/README.md). Local Next.js API URLs remain
relative; use the Compose Nginx entry point when testing the integrated app.

## Render and GitHub Actions deployment

The root [render.yaml](./render.yaml) defines only the Docker Web Service.
It runs Nginx, Next.js, and Daphne in the existing container; it does not run
Celery workers or Beat. This keeps the 512 MiB Render Web Service within its
memory budget. Do not add a persistent Render Worker or Beat service on the
free plan.

The [data-jobs.yml](./.github/workflows/data-jobs.yml) workflow runs Django
management commands directly against PostgreSQL. Scheduled market, directory,
history, and news collection does not publish to Redis. Existing Celery task
implementations are reused synchronously; Celery Beat remains available for
local Compose compatibility but must not run in production alongside GitHub
Actions. Analytics endpoints calculate from stored records on request, so new
market data is reflected without a separate analytics refresh job or cache.

### Configure Render

Connect the repository to Render as a Blueprint and sync `render.yaml`. Before
syncing, make the Web Service `name` match the existing service if it should be
updated rather than duplicated. Keep the existing production values for
`SECRET_KEY`, `DATABASE_URL`, Redis URLs, host/origin settings, and
`CRAWLER_USER_AGENT`; do not change the existing database or Redis credentials.

Configure these additional Web Service values:

- `GITHUB_ACTIONS_TOKEN`: a fine-grained GitHub token scoped to this repository
  with **Actions: read and write** permission. The token is only used when an
  administrator starts a crawl from the app.
- `GITHUB_REPOSITORY`, `GITHUB_WORKFLOW_FILE`, and `GITHUB_ACTIONS_REF` are
  set in the Blueprint to the repository, workflow filename, and default
  branch. Update them if the repository or default branch changes.

The admin crawl endpoint creates `CrawlRun` rows and dispatches
`workflow_dispatch`; it no longer puts work on a Redis queue with no worker.
If dispatch fails, the runs are marked failed with an explanatory error.

### Configure GitHub Actions

Add these repository **Actions secrets** using the same production credentials
as Render:

- `SECRET_KEY`
- `DATABASE_URL` (Supabase PostgreSQL URL, including `sslmode=require`)
- `CRAWLER_USER_AGENT` (a real contact string, required before enabling sources)

The workflow uses a GitHub Actions-specific Django settings module that requires
external TLS-enabled PostgreSQL and uses an in-memory Channels layer. Normal
collection jobs do not need Redis and do not connect to it. The Supabase
database must accept connections from GitHub-hosted runners; no live database
connection has been tested here.

To run a job manually, open **Actions → NEPSE data jobs → Run workflow** and
choose `news`, `live_market`, `historical_market`, `market_analysis`, or `all`.
The older `market-data`, `company-history`, `index-history`, and
`company-directory` operation names remain available. `source_keys` selects
enabled news crawler keys; `market_source_keys` selects market providers
(`nepsealpha`, `sharesansar`, `merolagani`) or a specific history collector.
Blank source inputs select all applicable enabled/implemented sources.
`crawl_run_ids` is optional and only for explicit queued news runs. Unknown or
deleted IDs are rejected with an error naming the missing IDs. Scheduled jobs
never supply database IDs. The Django admin crawl button dispatches the same
workflow.

The management command can also run locally from `backend\`:

```powershell
python manage.py run_collection news
python manage.py run_collection live_market
python manage.py run_collection historical_market
python manage.py run_collection market_analysis
python manage.py run_collection all
```

These commands call the existing collection services synchronously; a running
Celery worker is not required.

The optional `run_legacy_queue_worker` input is only for explicitly processing
old Celery messages. It requires a `CELERY_BROKER_URL` Actions secret reachable
from GitHub-hosted runners. It starts one prefork worker on the app's default
`celery` queue, concurrency one, with task-count, idle, per-task, and total-run
limits. Only use it if that broker and queue are dedicated to this app; normal
scheduled/manual collection never starts this worker.

### Scheduling and free-tier limits

GitHub Actions cron is UTC. The workflow schedules news every four hours,
`live_market` every 15 minutes during the current Sunday–Thursday
11:00–15:00 Nepal Standard Time window (UTC 05:15–09:15), and
`historical_market` at 15:05 NPT (UTC 09:20) on Sunday–Thursday. The live
schedule includes the UTC cron slots that align with that window; market-hours
and trading-day guards remain in the existing tasks. Live collection is
followed by market analysis only when at least one source succeeds;
`historical_market` backfills the company directory before index and company
history, then refreshes analysis when data collection succeeds. GitHub cron is
best-effort and may be delayed or skipped.

Each operation records source, type, start/completion time, status, record
counts, and error details in `CrawlRun`. The analysis API reports market-data
freshness as unavailable, fresh, or stale (24-hour threshold); it calculates
from stored records and returns empty/unavailable values when source data is
absent.

This schedule creates roughly 600 workflow runs per month before manual
triggers. Dependency caching reduces repeated setup, but actual included-minute
use depends on collection duration, repository visibility, and the GitHub plan.
Monitor **Settings → Billing and licensing → Actions**. If the repository's
included quota or average job duration is lower than required, reduce the cron
frequency before enabling sources; GitHub Actions cannot guarantee execution
timing or a particular monthly free-minute allowance.

### Verify after deployment

- **Render Web Service:** confirm Daphne, Next.js, and Nginx start. Celery
  Worker and Beat startup lines should not appear.
- **GitHub Actions:** confirm a scheduled or manual run starts and the
  `run_collection` step reports task results without a Redis/broker connection.
- **Crawlers:** check that selected sources are enabled, a `CrawlRun` moves
  through `queued` and `running` to `succeeded` (or `partial` when robots rules
  disallow access), and the logs report extracted/created/duplicate counts.
- **Market collection:** inspect the per-source `CrawlRun` rows for
  `live_market`, `historical_market`, and `market_analysis`; a workflow can be
  successful while individual sources are skipped outside market hours.
- **Market data:** confirm fresh rows and timestamps in the existing market
  tables and that the analysis API reflects them.
- **Database:** verify the expected rows in Supabase; a successful Actions
  command alone is not proof of durable production data or successful scraping.

No Render deployment, GitHub Actions run, Supabase write, or live scrape has
been verified. If verification fails, share the failing Actions step and
timestamped traceback, the corresponding Render Web Service log if dispatch
failed, and the affected `CrawlRun` status/error. Redact all credentials,
tokens, database/Redis URLs, and secret values.

Dashboard pages require authentication. Public registration is at `/register`
and always grants Viewer. Protected routes are `/dashboard`, `/analyst`, and
`/admin`.

## Environment variables

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Required unique Django signing key (at least 50 characters). |
| `DATABASE_URL` | Required external Supabase PostgreSQL URL; enable TLS with `sslmode=require`. |
| `REDIS_PASSWORD` | Required URL-safe Redis password used by Django Channels and Celery. |
| `PUBLIC_APP_URL` | Public HTTPS origin, used as the frontend/CSRF origin. |
| `ALLOWED_HOSTS` | Comma-separated public hostname(s), plus localhost entries for container health checks. |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Allowed same-domain origins, including the scheme (for example `https://app.example.com`). |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_HSTS_SECONDS`, `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD` | Production HTTPS redirect and HSTS policy; enable subdomain/preload policies only when appropriate for the domain. |
| `CRAWLER_USER_AGENT` | Crawler contact string; provide a real contact before enabling any publisher. |
| `PORT` | Host/platform port mapped to Nginx container port 80; backend and Redis are not published. |
| `GITHUB_ACTIONS_TOKEN` | Render Web Service token with repository-scoped Actions read/write permission for admin-triggered crawls. |
| `GITHUB_REPOSITORY`, `GITHUB_WORKFLOW_FILE`, `GITHUB_ACTIONS_REF` | GitHub repository, workflow file, and default branch used for dispatching manual crawls. |

Compose constructs `REDIS_URL`, `CELERY_BROKER_URL`, and
`CELERY_RESULT_BACKEND` from the internal Redis service and password. Do not
add Supabase credentials to frontend build arguments or browser-visible
variables. The frontend API and WebSocket paths are fixed to same-origin
`/api` and `/ws/` routes.

Never commit `.env`, `.env.local`, credentials, or production secrets.

## Authentication and permissions

- `POST /api/auth/register/` creates a Viewer only. Role, `is_staff`, and
  `is_superuser` fields are not accepted from public users.
- `POST /api/auth/token/` issues a short-lived access token and stores the
  refresh token in an HttpOnly, SameSite cookie. In production the cookie is
  Secure; the frontend keeps the access token in session storage and includes
  CSRF headers for cookie-backed auth operations.
- `POST /api/auth/token/refresh/` rotates the HttpOnly refresh cookie.
- `POST /api/auth/logout/` revokes the refresh token. Existing access tokens
  remain valid until their 30-minute expiry.
- `GET /api/users/me/` returns the authenticated user and application role.
- Django flags and application roles are separate. Django Admin manages
  trusted users/profiles; only application Admin users may grant application
  Admin or Analyst roles through `/api/admin/users/`.
- Viewer: authenticated read-only data access. Analyst: news-tag corrections.
  Admin: user/role management, company administration, crawl administration,
  and data imports. Backend permissions enforce these rules.

See [backend/README.md](./backend/README.md) for request/response shapes,
complete API endpoint documentation, WebSocket events, crawler setup, and
market calculation methodology.

## Data collection and limitations

The database migration registers all four requested source URLs and article
patterns, with NEPSE Alpha's page-number template. All sources remain
**disabled** by default. These requested settings are configuration, not
confirmation that a publisher permits crawling or that selectors still work.
Verify publisher terms and current `robots.txt` before enabling any source.
The crawler checks robots rules on listing/article URLs, enforces same-site
links/redirects, rate-limits requests, and reports empty discovery/parsing as a
failed run. It does not bypass access controls. No live news crawl or article
persistence is claimed. Separate market-data collectors ingest currently
available public provider pages; those pages are not documented APIs or a
redistribution license. Verify publisher terms and obtain any required
permission before production use.
Consequently, company-behavior calculations on demo records are explicitly
fictional; VWAP and broker analysis use only stored company-level OHLCV and
floorsheet records and remain unavailable where those records are absent. The
pressure value is only an OHLCV close-location estimate, not actual buy/sell
volume.

The Market Analysis overview collects public NEPSE Alpha JSON from `/live/stocks`
and `/trading-ta`, ShareSansar's `/market` and `/today-share-price` pages, and
Merolagani's `/LatestMarket.aspx` page. These are website endpoints/pages, not
documented or guaranteed APIs. On Render, GitHub Actions runs synchronous
`live_market` collection every 15 minutes during the Sunday–Thursday
11:00–15:00 Nepal-time session and `historical_market` at 15:05 NPT; local
Compose retains Celery Beat. Complete company OHLCV rows are matched to active
companies by symbol and upserted by company/date; NEPSE Alpha is preferred over
ShareSansar and Merolagani when their same-day prices differ. Incomplete or
unmatched rows are skipped and logged. Historical collectors include directory
synchronization and paginate provider history, preserving provider dates and
values while upserting into `MarketIndexSnapshot`, `StockPrice`, and
`FloorsheetTransaction`.
Later runs refresh recent company history and daily floorsheet records.
Merolagani's paginated floorsheet page remains an independent source; it
currently exposes up to 500 rows per page, so VWAP/broker analysis may cover
only stored rows. Merolagani's inspected market page did not expose a populated
index table, so its index, sector, and market-total values remain unavailable.
NEPSE Alpha's CSV export is browser-accessible but blocks direct backend
requests in the current environment, so the collector does not bypass that
restriction. Bizmandu remains a news source: no structured quote feed was
confirmed. Missing data is displayed as unavailable, never backfilled with
estimates. ShareSansar pages are public but are not documented APIs; review its
current terms and robots directives before deploying collection beyond local
development. Provider access, terms, and page formats may change.

## API and real-time docs

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`
- WebSocket: `/ws/updates/` (same origin; `wss` under HTTPS); authenticated clients negotiate
  the `nepse-insight` and `nepse-insight.bearer.<access-token>` subprotocols.
  Tokens are not placed in query strings.

## Checks

Run from the repository root:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe manage.py test tests
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
Pop-Location
Push-Location frontend
npm.cmd run lint
npm.cmd run build
Pop-Location
```

Tests use isolated databases and mocked crawler HTTP; they do not crawl public
sites. Seed-command verification uses a separate temporary development
database; seeded data must not be used as real market information.

## Production deployment notes

Use the production Django settings and Dockerfiles in the Compose stack. Secure
the hosting platform's TLS termination and forwarded-protocol handling, set
the required secrets/origins, use Supabase TLS, persist Redis/media/Beat
volumes, and expose only Nginx. Review publisher terms and robots directives
before enabling crawlers. Back up Supabase and media according to their
respective retention policies.
