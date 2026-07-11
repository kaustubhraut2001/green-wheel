# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.12-slim AS production

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser . .

RUN mkdir -p /tmp/uploads/profile_images && chown -R appuser:appuser /tmp/uploads

USER appuser

EXPOSE 8000

# entrypoint.sh runs alembic then uvicorn
CMD ["sh", "-c", "\
    echo 'Running database migrations...' && \
    alembic upgrade head && \
    echo 'Starting FastAPI server...' && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 \
"]
