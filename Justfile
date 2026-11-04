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

# Run all linters and test suites as a pre-push quality gate
check: lint test

# Start fullstack development server
dev:
    python main.py
