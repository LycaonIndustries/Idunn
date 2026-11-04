# Agent Guidelines for Iðunn Kitchen OS

## 1. Git Workflow & Branch Protection (CRITICAL)

- **Direct commits or pushes to `main` or `master` are strictly banned.**
- Never commit while on `main` or `master`.
- Always create a dedicated branch before making changes:
  - `feat/<feature-name>` for new capabilities
  - `fix/<bug-name>` for defect resolutions
  - `refactor/<scope>` for code restructuring
  - `chore/<task>` for maintenance and configuration
- All changes must be merged into `main` exclusively through GitHub Pull Requests.

## 2. Technical Stack Constraints

- **Backend**: Python 3.13+, FastAPI, Motor/Supabase, Pydantic v2.
  - Test runner: `uv run python -m pytest`
  - Linter & Formatter: `uv run ruff check` and `uv run ruff format`
  - Docstrings: Google-style docstrings with explicit `Args:` and `Returns:` on all functions.
  - Comments: ASD-STE100 technical comments before every block of code explaining **WHY** (not what), short sentences (≤ 25 words).
- **Frontend**: React 19, TypeScript, Bun, Vite, Tailwind CSS.
  - Test runner: `bun test` in `frontend/` (tests reside in `frontend/tests/`).
  - Linter: `bun run --cwd frontend lint` (Oxlint).
  - Package manager: **Bun only** (`bun.lock`). Never use `npm` or create `package-lock.json`.
- **Task Runner**: `just` (`Justfile`).
  - Run all tests: `just test`
  - Run all linters: `just lint`
