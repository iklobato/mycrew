# Stage 1 – Builder (install compilers & deps)
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev libssl-dev git curl && \
    rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

# Stage 2 – Runtime (tiny image)
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV GITHUB_WEBHOOK_SECRET="" \
    DEFAULT_DRY_RUN="false" \
    DEFAULT_BRANCH="main" \
    PORT="8000" \
    HOST="0.0.0.0" \
    PYTHONPATH="/app/src"

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/.venv /app/.venv

WORKDIR /app
COPY src/ ./src/
COPY config.example.yaml ./config.yaml

EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "webhook"]
