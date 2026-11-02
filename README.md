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
- **Background work:** Celery worker + Beat; separate NEPSE Alpha, ShareSansar,
  and Merolagani market-data collection plus configurable news crawling.
- **Real time:** authenticated Django Channels updates over ASGI/WebSockets.
- **Analysis:** Decimal-based calculations over stored OHLCV and floorsheet
  records; unavailable inputs are returned as unavailable.

## Requirements and local setup

Use Docker Desktop with Compose for the complete local stack. In PowerShell at
the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Compose starts PostgreSQL, Redis, the Django/Daphne API, the Next.js frontend,
two Celery workers, and one Celery Beat scheduler. The backend applies
migrations before starting. The root `.env` controls development database
credentials and frontend/backend build URLs; `.env.example` contains local-only
defaults. Change the Django key and database password before exposing this
stack beyond a trusted development machine.

Create the trusted initial Django administrator interactively:

```powershell
docker compose exec backend python manage.py createsuperuser
```

The new superuser has Django `is_staff`/`is_superuser` privileges for Django
Admin and automatically receives an independent `Admin` application role.
Public registrations remain `Viewer`; the application role is stored on the
user profile.

Open <http://localhost:3000> for the frontend, <http://localhost:8000/admin/>
for Django Admin, and <http://localhost:8000/api/docs/> for API documentation.
View service status and logs with `docker compose ps` and
`docker compose logs -f backend celery-worker-1 celery-worker-2 celery-beat`.

To populate a development database with clearly marked demonstration records:

```powershell
docker compose exec backend python manage.py seed
```

The command is disabled when `DEBUG=False`, is repeatable without changing
existing records, and creates eight sample companies, 22 weekday OHLCV rows per
company, fictional news and tags, fictional floorsheet transactions, demo
role accounts with unusable passwords, and sample crawl runs explicitly marked
as not crawled. Demo Admin is an application role only, not a Django
superuser. Optionally pass `--password` to set a validated password on newly
created demo accounts only. These records are for UI/development testing and
must not be treated as real market or publisher data.

Run a one-off crawler dispatch from the backend container after an administrator
has reviewed publisher terms, robots.txt, contact details, and enabled a source:

```powershell
docker compose exec backend python manage.py shell -c "from apps.crawlers.tasks import crawl_enabled_sources; crawl_enabled_sources.delay()"
```

For frontend/backend development directly on the host instead of inside
Compose, install Node.js 20.9+ and Python 3.12+, copy the respective example
environment files, and use the native setup steps in [backend/README.md](./backend/README.md).

Dashboard pages require authentication. Public registration is at `/register`
and always grants Viewer. Protected routes are `/dashboard`, `/analyst`, and
`/admin`.

## Environment variables

| File / variable | Purpose |
|---|---|
| `.env` · `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Compose development database settings. |
| `.env` · `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` | Compose development Django settings. Never use the example key outside local development. |
| `.env` · `CRAWLER_USER_AGENT` | Identifiable crawler contact string; replace with a real contact before enabling a publisher. |
| `.env` · `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL` | Frontend API and WebSocket URLs; these are baked into the frontend image at build time. |
| `backend\.env` · `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Native backend run settings. Use a unique secret and `DEBUG=False` in production. |
| `backend\.env` · `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Native backend database and Redis URLs. |
| `backend\.env` · `FRONTEND_URL` | Native backend CORS and CSRF trusted frontend origin. |

Never commit `.env`, `.env.local`, credentials, or production secrets.

## Authentication and permissions

- `POST /api/auth/register/` creates a Viewer only. Role, `is_staff`, and
  `is_superuser` fields are not accepted from public users.
- `POST /api/auth/token/` issues a short-lived access token and stores the
  refresh token in an HttpOnly, SameSite cookie. The frontend keeps the access
  token in session storage and includes CSRF headers for cookie-backed auth
  operations.
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
failed run. It does not bypass access controls. No live crawl or article
persistence is claimed. OHLCV and floorsheet records must otherwise come from a
verified/licensed source.
Consequently, company-behavior calculations on demo records are explicitly
fictional; VWAP and broker analysis remain unavailable until sourced
company-level OHLCV and floorsheet records exist. The pressure value is only
an OHLCV close-location estimate, not actual buy/sell volume.

The Market Analysis overview collects public NEPSE Alpha JSON from `/live/stocks`
and `/trading-ta`, ShareSansar's `/market` and `/today-share-price` pages, and
Merolagani's `/LatestMarket.aspx` page. These are website endpoints/pages, not
documented or guaranteed APIs. Celery Beat polls every 15 minutes during the
Sunday–Thursday 11:00–15:00 Nepal-time session and skips further collection once
NEPSE Alpha reports the market closed. Index and sector data are available
from NEPSE Alpha and ShareSansar; stock quotes and leaders are collected from
all three providers where their pages expose them. Bizmandu is used for news
only: no structured public quote/index source was confirmed. Merolagani's
inspected market page did not expose a populated index table, so its index,
sector, and market-total values remain unavailable rather than inferred. The
Alpha live endpoint supplies intraday index history; longer-term daily history
accumulates from snapshots and is not backfilled. Provider access, terms, and
page formats may change.

## API and real-time docs

- Swagger UI: <http://localhost:8000/api/docs/>
- ReDoc: <http://localhost:8000/api/redoc/>
- OpenAPI schema: <http://localhost:8000/api/schema/>
- WebSocket: `ws://localhost:8000/ws/updates/`; authenticated clients negotiate
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

## Production deployment

The included Compose stack is for development, not production. Production
requires a unique strong Django secret, `DEBUG=False`, explicit `ALLOWED_HOSTS`,
TLS-enabled PostgreSQL and Redis, HTTPS frontend/backend origins, secure
cookies, network-restricted databases, production-grade image builds and
supervised Daphne, Celery workers, and Celery Beat. Review publisher
terms/robots directives and crawler configuration before enabling a source.
