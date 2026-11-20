
FROM node:22-bookworm-slim AS frontend-dependencies

WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS frontend-build

WORKDIR /src/frontend
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=frontend-dependencies /src/frontend/node_modules ./node_modules
COPY frontend/ ./

RUN npm run build

FROM node:22-bookworm-slim AS frontend-production-dependencies

WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev

FROM python:3.12-slim AS backend-dependencies

WORKDIR /build
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/opt/python -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    STATIC_ROOT=/srv/static \
    MEDIA_ROOT=/srv/media

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       gettext-base \
       libstdc++6 \
       nginx \
       supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app \
    && mkdir -p \
       /srv/static \
       /srv/media \
       /var/lib/celerybeat \
       /var/cache/nginx \
       /var/lib/nginx \
       /tmp/nginx_client_temp \
       /tmp/nginx_proxy_temp \
       /tmp/nginx_fastcgi_temp \
       /tmp/nginx_uwsgi_temp \
       /tmp/nginx_scgi_temp \
    && chmod 1777 /tmp \
    && chown -R app:app \
       /srv/static \
       /srv/media \
       /var/lib/celerybeat \
       /var/cache/nginx \
       /var/lib/nginx \
       /tmp/nginx_client_temp \
       /tmp/nginx_proxy_temp \
       /tmp/nginx_fastcgi_temp \
       /tmp/nginx_uwsgi_temp \
       /tmp/nginx_scgi_temp

COPY --from=backend-dependencies /opt/python/ /usr/local/

COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node

COPY --chown=app:app frontend/package.json /app/frontend/package.json
COPY --chown=app:app frontend/public/ /app/frontend/public/
COPY --from=frontend-build --chown=app:app /src/frontend/.next /app/frontend/.next
COPY --from=frontend-production-dependencies --chown=app:app /src/frontend/node_modules /app/frontend/node_modules


COPY --chown=app:app backend/ /app/backend/

COPY --chown=app:app deploy/render-entrypoint.sh /usr/local/bin/render-entrypoint.sh
COPY --chown=app:app deploy/render-processes.py /usr/local/bin/render-processes.py

COPY deploy/nginx.conf /etc/nginx/nginx.conf.template
COPY deploy/supervisord.conf /etc/supervisor/supervisord.conf

RUN sed -i '1s/^\xEF\xBB\xBF//' /usr/local/bin/render-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/render-entrypoint.sh \
    && chmod 755 /usr/local/bin/render-entrypoint.sh \
    && chmod 755 /usr/local/bin/render-processes.py \
    && chown -R app:app /app/frontend /app/backend

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request; host=os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0].strip(); base='http://127.0.0.1:' + os.getenv('PORT', '10000'); headers={'Host':host, 'X-Forwarded-Proto':'https'}; [urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=4).close() for path in ('/healthz', '/') ]"

ENTRYPOINT ["/bin/sh", "/usr/local/bin/render-entrypoint.sh"]
