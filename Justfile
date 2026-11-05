# Iðunn Kitchen OS - Developer Command Runner
# Modern polyglot task runner: https://github.com/casey/just

# Configure shell on Windows to use PowerShell
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Default recipe lists all available recipes
default:
    @just --list

# Run all test suites (backend + frontend)
test: test-backend test-frontend

# Run Python backend test suite with pytest
test-backend:
    uv run python -m pytest

# Run React frontend test suite with bun test
test-frontend:
    bun run --cwd frontend test

# Run all linters (Ruff for backend + Oxlint for frontend)
lint: lint-backend lint-frontend

# Lint Python backend using Ruff
lint-backend:
    uv run ruff check backend tests
    uv run ruff format --check backend tests

# Lint React frontend using Oxlint via Bun
lint-frontend:
    bun run --cwd frontend lint

# Format all codebase files
format:
    uv run ruff check --fix backend tests
    uv run ruff format backend tests

# Build frontend production web assets into backend/web_dist/
build-frontend:
    bun run --cwd frontend build

# Run runtime contract smoke test against live FastAPI app
smoke:
    uv run python scripts/smoke_test.py

# Run all linters, test suites, and runtime smoke checks as a pre-push quality gate
check: lint test smoke

# Run dependency vulnerability security audit across Python backend and Bun frontend
audit:
    uvx pip-audit
    bun audit --cwd frontend

# Run development review audit and update .review.lock
review:
    uv run python scripts/dev_review.py --mode=audit

# Verify .review.lock matches current HEAD and satisfies granularity limits
review-verify:
    uv run python scripts/dev_review.py --mode=verify

# Run pre-flight quality checks and push branch
pr-check: check review-verify
    git push origin (git branch --show-current)

# Run asynchronous background task queue worker
worker:
    uv run python -m arq backend.workers.tasks.WorkerSettings

# Start fullstack development server
dev:
    python main.py
