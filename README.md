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
- **Background work:** Celery worker + Beat; NEPSE Alpha, ShareSansar, and
  Merolagani market-data collection plus four-source news crawling.
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

## Render Docker deployment

The root `Dockerfile` builds the Next.js production bundle and Django
dependencies, then runs Nginx, Next.js, and Daphne in one Render Web Service.
Nginx listens on Render's `PORT` (default `10000`) and proxies to the
localhost-only application processes. Django migrations and `collectstatic`
run before Supervisor starts Nginx, Daphne, and Next.js. Nginx binds Render's
public `PORT` immediately; Next.js and Daphne bind to localhost. Celery workers
and Beat are deliberately not started in the Web Service. Nginx answers
`HEAD /` directly for Render's health check; `GET /` remains proxied to Next.js.

In Render, create a **Web Service** from this repository, select **Docker**,
and leave the Dockerfile path at `./Dockerfile`. Add these environment variables
to the Web Service's Environment settings without committing their values;
Render does not need or use an uploaded `.env` file:

- `SECRET_KEY`: unique Django key of at least 50 characters.
- `DATABASE_URL`: Supabase PostgreSQL connection URL with `sslmode=require`.
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: URLs from an
  external Redis-compatible service, using separate logical databases if
  supported.
- `ALLOWED_HOSTS`: the Render hostname (and any custom domain), comma-separated.
- `PUBLIC_APP_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`: the public
  HTTPS origin, for example `https://your-service.onrender.com`.
- `CRAWLER_USER_AGENT`: a crawler identifier with a real contact address.
- Optionally set `SECURE_SSL_REDIRECT=True`, `DEBUG=False`,
  `SECURE_HSTS_SECONDS`,
  `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, and `LOG_LEVEL`.

Render supplies `PORT`; do not override it unless required by the service.
The Web Service image selects `config.settings.production`; set that value as
`DJANGO_SETTINGS_MODULE` on each Background Worker because its backend image
defaults to development settings. Django reads service configuration directly
from the process environment; only native development loads `backend/.env`.
`STATIC_ROOT` and `MEDIA_ROOT` default to `/srv/static` and `/srv/media`.
Static files are collected at startup. The container filesystem is ephemeral:
if the application stores uploads locally, attach a persistent Render Disk at a
path and set `MEDIA_ROOT` to that mount path. Otherwise configure external
object storage for uploads.

Create separate Render **Background Worker** services from the `backend/`
directory using `backend/Dockerfile` and the same Django, Supabase, and Redis
environment values, including `DJANGO_SETTINGS_MODULE=config.settings.production`.
Set one worker's Docker Command to
`celery -A config worker --loglevel=info --concurrency=2`. Create exactly one
additional worker for Beat with Docker Command
`celery -A config beat --loglevel=info`. Do not run multiple Beat instances.
These services keep scheduled market-data collection and crawling outside the
Web Service while using the existing Celery configuration and schedules.

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
documented or guaranteed APIs. Celery Beat polls every 15 minutes during the
Sunday–Thursday 11:00–15:00 Nepal-time session. Complete company OHLCV rows are
matched to active companies by symbol and upserted by company/date; NEPSE Alpha
is preferred over ShareSansar and Merolagani when their same-day prices differ.
Incomplete or unmatched rows are skipped and logged. After market close, Beat
imports ShareSansar's public Index History DataTables rows and the historical
price/floorsheet rows exposed on each active company's public profile. The
history collectors paginate the provider's 50-row tables, preserve provider
dates and values, and upsert into `MarketIndexSnapshot`, `StockPrice`, and
`FloorsheetTransaction`. Later runs refresh recent company history and daily
floorsheet records. Merolagani's paginated floorsheet page remains an independent
source; it currently exposes up to 500 rows per page, so VWAP/broker analysis may
cover only stored rows. Merolagani's inspected market page did not expose a
populated index table, so its index, sector, and market-total values remain
unavailable. NEPSE Alpha's CSV export is browser-accessible but blocks direct
backend requests in the current environment, so the collector does not bypass
that restriction. Bizmandu remains a news source: no structured quote feed was
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
