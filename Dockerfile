# Multi-stage: Node builds the Vite frontend, Python runs FastAPI and serves
# the built static files alongside the API. Single image, single port.

# ---------- Stage 1: build the frontend ----------
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: run FastAPI ----------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    AUTO_INGEST_ON_STARTUP=true

# uv is the project's package manager.
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# HF Spaces expects the app to run as a non-root user with UID 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

# Install Python deps first (cached unless lockfile changes).
COPY --chown=user:user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the rest of the app.
COPY --chown=user:user app/ ./app/
COPY --chown=user:user alembic/ ./alembic/
COPY --chown=user:user alembic.ini ./alembic.ini
COPY --chown=user:user convictions/ ./convictions/

# Bring in the built frontend from stage 1.
COPY --from=frontend-build --chown=user:user /build/dist ./frontend/dist

# Writable dir for SQLite (ephemeral on Spaces free tier — auto-ingest handles it).
RUN mkdir -p /app/data && chown user:user /app/data

USER user

# HF Spaces routes traffic to port 7860 by default.
EXPOSE 7860
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
