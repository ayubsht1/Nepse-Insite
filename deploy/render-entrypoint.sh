#!/bin/sh
set -eu

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
python manage.py migrate --noinput
python manage.py collectstatic --noinput

envsubst '${PORT} ${NGINX_FRONTEND_UPSTREAM} ${NGINX_BACKEND_UPSTREAM} ${NGINX_STATIC_ROOT} ${NGINX_MEDIA_ROOT}' \
    < /etc/nginx/nginx.conf.template \
    > /etc/nginx/nginx.conf

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
