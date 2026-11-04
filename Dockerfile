# ──────────────────────────────────────────────
# Stage 1: Build the React frontend
# ──────────────────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts

COPY frontend/ ./
# Vite outputs to ../src/idunn/web_dist relative to frontend/
RUN mkdir -p ../src/idunn && npm run build


# ──────────────────────────────────────────────
# Stage 2: Python application
# ──────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# System deps: ffmpeg for video frame extraction, curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend source
COPY src/ src/
COPY main.py ./

# Copy built frontend from stage 1
COPY --from=frontend-build /build/src/idunn/web_dist src/idunn/web_dist/

# Install the project itself
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run with uv so the virtualenv is activated
CMD ["uv", "run", "uvicorn", "idunn.main:app", "--host", "0.0.0.0", "--port", "8000"]
