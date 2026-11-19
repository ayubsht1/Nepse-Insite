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
    PORT=10000 \
    STATIC_ROOT=/srv/static \
    MEDIA_ROOT=/srv/media

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates gettext-base libstdc++6 nginx supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app \
    && groupadd --system nginx \
    && useradd --system --gid nginx --no-create-home --shell /usr/sbin/nologin nginx \
    && mkdir -p /srv/static /srv/media /var/cache/nginx /var/lib/nginx \
    && chown -R app:app /srv/static /srv/media \
    && chown -R nginx:nginx /var/cache/nginx /var/lib/nginx

COPY --from=backend-dependencies /opt/python/ /usr/local/
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-production-dependencies /src/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-build /src/frontend/.next /app/frontend/.next
COPY --from=frontend-build /src/frontend/public /app/frontend/public
COPY --from=frontend-build /src/frontend/package.json /app/frontend/package.json
COPY --chown=app:app backend/ /app/backend/
COPY --chown=app:app deploy/render-entrypoint.sh /usr/local/bin/render-entrypoint.sh
COPY deploy/nginx.conf /etc/nginx/nginx.conf.template
COPY deploy/supervisord.conf /etc/supervisor/supervisord.conf

RUN sed -i 's/\r$//' /usr/local/bin/render-entrypoint.sh \
    && chmod 755 /usr/local/bin/render-entrypoint.sh

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '10000') + '/healthz', timeout=4)"

CMD ["/usr/local/bin/render-entrypoint.sh"]
