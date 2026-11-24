# React is compiled once; Node.js is not needed in the runtime image.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REDIS_URL=redis://127.0.0.1:6379/0 \
    UPLOADS_DIR=/srv/okhovat/private-media

# Redis is private to this container. Supervisor runs/restarts both services.
RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server supervisor ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 okhovat \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin okhovat

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY --from=frontend-build /build/frontend/dist/ /app/frontend/dist/
COPY deploy/ /app/deploy/
RUN chmod 755 /app/deploy/entrypoint.sh \
    && mkdir -p /app/backend/staticfiles /srv/okhovat/private-media \
    && chown 10001:10001 /app/backend/staticfiles /srv/okhovat/private-media

USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=20s --start-period=120s --retries=3 \
    CMD ["python", "/app/deploy/healthcheck.py"]
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
