# syntax=docker/dockerfile:1

# ---- Stage 1: install deps ----
FROM python:3.13-slim AS deps
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy manifests and install runtime deps only (no dev)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- Stage 2: runtime image ----
FROM python:3.13-slim AS runtime
WORKDIR /app

COPY --from=deps /app/.venv /app/.venv

# Copy application source
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/
COPY config.yaml ./

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
