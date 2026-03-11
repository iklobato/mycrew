FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN uv sync --frozen --no-dev --no-install-project \
    && uv sync --frozen --no-dev

WORKDIR /workspace

# Environment variables for webhook
ENV GITHUB_WEBHOOK_SECRET=""
ENV DEFAULT_DRY_RUN="false"
ENV DEFAULT_BRANCH="main"
ENV PORT="8080"
ENV HOST="0.0.0.0"

# Expose webhook port
EXPOSE 8080

# Run the webhook API
ENTRYPOINT ["uv", "run", "--project", "/app", "webhook"]
