#!/bin/sh
set -eu

SUPERVISOR_CONFIG=/etc/supervisor/supervisord.conf

export PORT="${PORT:-10000}"
export STATIC_ROOT="${STATIC_ROOT:-/srv/static}"
export MEDIA_ROOT="${MEDIA_ROOT:-/srv/media}"
export NGINX_FRONTEND_UPSTREAM="${NGINX_FRONTEND_UPSTREAM:-127.0.0.1:3000}"
export NGINX_BACKEND_UPSTREAM="${NGINX_BACKEND_UPSTREAM:-127.0.0.1:8000}"
export NGINX_STATIC_ROOT="${NGINX_STATIC_ROOT:-$STATIC_ROOT}"
export NGINX_MEDIA_ROOT="${NGINX_MEDIA_ROOT:-$MEDIA_ROOT}"

mkdir -p "$STATIC_ROOT" "$MEDIA_ROOT"
chown app:app "$STATIC_ROOT" "$MEDIA_ROOT"

cd /app/backend
python /app/backend/run_migrations.py
python /app/backend/seed.py
python manage.py collectstatic --noinput

envsubst '${PORT} ${NGINX_FRONTEND_UPSTREAM} ${NGINX_BACKEND_UPSTREAM} ${NGINX_STATIC_ROOT} ${NGINX_MEDIA_ROOT}' \
    < /etc/nginx/nginx.conf.template \
    > /etc/nginx/nginx.conf

nginx -t
printf 'Starting Nginx and web processes on port %s; Celery processes are managed by the container launcher\n' "$PORT"
exec python /usr/local/bin/render-processes.py
