# NEPSE Insight

NEPSE Insight is a Next.js dashboard backed by Django REST Framework. It stores
provenance-tracked company, OHLCV, floorsheet, and news records; analytics are
computed only from data actually present. The repository does not include
sample market prices, floorsheets, or news.

## Architecture

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, TanStack
  Query.
- **Backend:** Django 6, Django REST Framework, SimpleJWT, drf-spectacular.
- **Data:** PostgreSQL (or Supabase PostgreSQL); Redis for Celery and Channels.
- **Background work:** Celery worker + Beat; configurable HTTPX/BeautifulSoup
  news crawler.
- **Real time:** authenticated Django Channels updates over ASGI/WebSockets.
- **Analysis:** Decimal-based calculations over stored OHLCV and floorsheet
  records; unavailable inputs are returned as unavailable.

## Requirements and local setup

Use Node.js 20.9+, npm, Python 3.12+, and Docker Desktop with Compose. In
PowerShell at the repository root:

```powershell
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
docker compose up -d
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\backend\.venv\Scripts\python.exe backend\manage.py migrate
```

Set `DJANGO_SETTINGS_MODULE=config.settings.development` when running Django
commands from the repository root, or run them from `backend\` as shown below.
Create the trusted initial Django administrator interactively; no credentials
are preconfigured:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
Pop-Location
```

The new superuser has Django `is_staff`/`is_superuser` privileges for Django
Admin but receives an independent `Viewer` application role. Sign into
`/admin/`, open User profiles, and explicitly assign the application `Admin`
role before using the protected application admin APIs.

Run Celery worker and Beat from `backend\` in separate terminals:

```powershell
.\.venv\Scripts\celery.exe -A config worker --pool=solo --loglevel=info
.\.venv\Scripts\celery.exe -A config beat --loglevel=info
```

For authenticated WebSockets, serve `config.asgi:application` with Daphne:

```powershell
.\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

Start the frontend in another terminal:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open <http://localhost:3000>. Dashboard pages require authentication. Public
registration is at `/register` and always grants Viewer. Protected routes are
`/dashboard`, `/analyst`, and `/admin`.

## Environment variables

| File / variable | Purpose |
|---|---|
| `.env` · `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Local Compose database only. Use non-default values outside development. |
| `backend\.env` · `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django security and host configuration. Set a unique secret and `DEBUG=False` in production. |
| `backend\.env` · `DATABASE_URL` | PostgreSQL/Supabase URL; require TLS for hosted databases. SQLite is only a local fallback. |
| `backend\.env` · `REDIS_URL` | Channels Redis URL. |
| `backend\.env` · `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery Redis URLs. |
| `backend\.env` · `FRONTEND_URL` | CORS and CSRF trusted frontend origin. |
| `backend\.env` · `CRAWLER_USER_AGENT` | Identifiable crawler contact string; configure before enabling sources. |
| `frontend\.env.local` · `NEXT_PUBLIC_API_URL` | Django REST base URL, e.g. `http://localhost:8000/api`. |
| `frontend\.env.local` · `NEXT_PUBLIC_WS_URL` | WebSocket URL, e.g. `ws://localhost:8000/ws/updates/`. |

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

The four known news-source records are seeded **disabled**. Before enabling
one, verify its current terms and `robots.txt`, then configure its listing URL,
article URL pattern, and a real crawler contact. Celery Beat schedules enabled
sources every four hours. OHLCV and floorsheet records must currently be
imported from a verified/licensed source; no provider configuration or dataset
is included. Consequently, prices, transaction VWAP, broker activity, anomaly
scores, and news-market observations remain unavailable until sourced records
exist. The pressure value is only an OHLCV close-location estimate, not actual
buy/sell volume.

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
sites or seed fabricated market data.

## Production deployment

Use a unique strong Django secret, `DEBUG=False`, explicit `ALLOWED_HOSTS`,
TLS-enabled PostgreSQL and Redis, HTTPS frontend/backend origins, secure
cookies, network-restricted databases, and supervised Daphne, Celery worker,
and Celery Beat processes. Apply migrations before deployment. Review publisher
terms/robots directives and crawler configuration before enabling a source.
Compose currently provides development services, not a production service
deployment.
