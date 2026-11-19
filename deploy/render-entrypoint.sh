
#!/bin/sh
set -eu

echo "========================================"
echo "Starting NEPSE Insight container"
echo "========================================"

export PORT="${PORT:-10000}"
export STATIC_ROOT="${STATIC_ROOT:-/srv/static}"
export MEDIA_ROOT="${MEDIA_ROOT:-/srv/media}"
export NGINX_FRONTEND_UPSTREAM="${NGINX_FRONTEND_UPSTREAM:-127.0.0.1:3000}"
export NGINX_BACKEND_UPSTREAM="${NGINX_BACKEND_UPSTREAM:-127.0.0.1:8000}"
export NGINX_STATIC_ROOT="${NGINX_STATIC_ROOT:-$STATIC_ROOT}"
export NGINX_MEDIA_ROOT="${NGINX_MEDIA_ROOT:-$MEDIA_ROOT}"

echo "Port: $PORT"
echo "Frontend upstream: $NGINX_FRONTEND_UPSTREAM"
echo "Backend upstream: $NGINX_BACKEND_UPSTREAM"

mkdir -p "$STATIC_ROOT" "$MEDIA_ROOT"
chown app:app "$STATIC_ROOT" "$MEDIA_ROOT"

cd /app/backend

echo "[1/5] Running database migrations..."
python /app/backend/run_migrations.py

echo "[2/5] Running database seed..."
python /app/backend/seed.py

echo "[3/5] Collecting static files..."
python manage.py collectstatic --noinput

echo "[4/5] Generating Nginx configuration..."
envsubst '${PORT} ${NGINX_FRONTEND_UPSTREAM} ${NGINX_BACKEND_UPSTREAM} ${NGINX_STATIC_ROOT} ${NGINX_MEDIA_ROOT}' \
    < /etc/nginx/nginx.conf.template \
    > /etc/nginx/nginx.conf

echo "Checking Nginx configuration..."
nginx -t

echo "[5/5] Starting application processes..."

exec python -u /usr/local/bin/render-processes.py
