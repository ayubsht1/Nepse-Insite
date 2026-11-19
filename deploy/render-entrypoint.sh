#!/bin/sh
set -eu

SUPERVISOR_CONFIG=/etc/supervisor/supervisord.conf
SUPERVISOR_PID=
NEXTJS_STARTUP_TIMEOUT="${NEXTJS_STARTUP_TIMEOUT:-120}"

stop_supervisor() {
    if [ -n "$SUPERVISOR_PID" ]; then
        if kill -0 "$SUPERVISOR_PID" 2>/dev/null; then
            /usr/bin/supervisorctl -c "$SUPERVISOR_CONFIG" shutdown \
                >/dev/null 2>&1 || kill -TERM "$SUPERVISOR_PID"
        fi
        wait "$SUPERVISOR_PID" 2>/dev/null || true
        SUPERVISOR_PID=
    fi
}

fail_startup() {
    printf 'Render startup failed: %s\n' "$1" >&2
    stop_supervisor
    exit 1
}

case "$NEXTJS_STARTUP_TIMEOUT" in
    ''|*[!0-9]*) fail_startup "NEXTJS_STARTUP_TIMEOUT must be a positive number of seconds." ;;
esac

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

/usr/bin/supervisord -c "$SUPERVISOR_CONFIG" &
SUPERVISOR_PID=$!
trap 'stop_supervisor; exit 0' INT TERM

startup_deadline=$(( $(date +%s) + NEXTJS_STARTUP_TIMEOUT ))
while :; do
    if ! kill -0 "$SUPERVISOR_PID" 2>/dev/null; then
        fail_startup "Supervisor exited before Next.js became ready."
    fi

    nextjs_status=$(
        /usr/bin/supervisorctl -c "$SUPERVISOR_CONFIG" status nextjs 2>/dev/null || true
    )
    case "$nextjs_status" in
        "nextjs BACKOFF "*|"nextjs FATAL "*|"nextjs EXITED "*|"nextjs STOPPED "*)
            fail_startup "Next.js exited before becoming ready ($nextjs_status)."
            ;;
        "nextjs RUNNING "*)
            if python -c "import urllib.request; response = urllib.request.urlopen('http://127.0.0.1:3000/', timeout=2); response.close()" \
                >/dev/null 2>&1; then
                nextjs_status=$(
                    /usr/bin/supervisorctl -c "$SUPERVISOR_CONFIG" status nextjs 2>/dev/null || true
                )
                case "$nextjs_status" in
                    "nextjs RUNNING "*) ;;
                    *) fail_startup "Next.js exited during its readiness check ($nextjs_status)." ;;
                esac
                if /usr/bin/supervisorctl -c "$SUPERVISOR_CONFIG" start nginx; then
                    printf 'Next.js is ready; Nginx started.\n'
                    break
                fi
                fail_startup "Supervisor could not start Nginx."
            fi
            ;;
    esac

    if [ "$(date +%s)" -ge "$startup_deadline" ]; then
        fail_startup "Next.js did not respond successfully on 127.0.0.1:3000 within ${NEXTJS_STARTUP_TIMEOUT} seconds."
    fi
    sleep 0.25
done

wait "$SUPERVISOR_PID"
