# NEPSE Insight

Initial development setup for the NEPSE Insight frontend and backend. No stock-market features or sample data are included.

## Requirements

- Node.js 20.9 or newer and npm
- Python 3.12+
- Docker Desktop with Docker Compose

## Configure local environment

From the project root in PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.local.example frontend\.env.local
```

`.env` provides local Docker Compose defaults. The Django process reads `backend\.env`, and Next.js reads `frontend\.env.local`. Change development values as needed; do not commit local environment files.

## Start PostgreSQL and Redis

```powershell
docker compose up -d
docker compose ps
```

PostgreSQL data persists in the `postgres_data` volume. To stop the services without removing data, run `docker compose down`.

## Backend

Create the Python environment and install dependencies:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Apply migrations and start Django:

```powershell
.\backend\.venv\Scripts\python.exe backend\manage.py migrate
.\backend\.venv\Scripts\python.exe backend\manage.py runserver
```

API schema and interactive docs:

- Swagger UI: <http://localhost:8000/api/docs/>
- ReDoc: <http://localhost:8000/api/redoc/>
- OpenAPI schema: <http://localhost:8000/api/schema/>

Run a Celery worker and scheduler in separate terminals:

```powershell
Set-Location backend
.\.venv\Scripts\celery.exe -A config worker --pool=solo --loglevel=info
# Use the same command in another terminal, replacing worker with beat:
.\.venv\Scripts\celery.exe -A config beat --loglevel=info
```

The ASGI application is `config.asgi:application`. From `backend\`, serve it locally with:

```powershell
Set-Location backend
.\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

## Frontend

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open <http://localhost:3000>. API and WebSocket base URLs are configured through `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` in `frontend\.env.local`.

## Checks

Run from the project root:

```powershell
.\backend\.venv\Scripts\python.exe backend\manage.py check
.\backend\.venv\Scripts\python.exe backend\manage.py migrate --check
Push-Location frontend
npm.cmd run lint
npm.cmd run build
Pop-Location
```

The backend defaults to the PostgreSQL URL in `backend\.env.example`; start Docker services before database-dependent management commands. Django settings can also be selected with `DJANGO_SETTINGS_MODULE=config.settings.production` in production.
