# Contributing to Iðunn Kitchen OS

Thank you for your interest in contributing to Iðunn! We welcome contributions from the community. To maintain high software quality, security, and developer ergonomics, all contributors must adhere to these guidelines.

---

## 1. Core Engineering Principles

1. **Algorithmic-First Policy**:
   Never use AI or LLMs when graphs, taxonomies, string normalization, or fuzzy matching can solve the problem deterministically. Generative AI is strictly opt-in and user-triggered.
2. **Atomic PR Granularity**:
   Target **≤ 350 lines changed** per PR (hard ceiling: **500 lines**). Split features into sequential sub-capabilities: core algorithm first, API router second, UI view third.
3. **Zero External Calls in Tests**:
   Automated unit and integration tests must run completely offline without live network calls to Gemini, Anthropic, OpenAI, or cloud databases. Mock all external dependencies.
4. **Documentation & Comment Integrity**:
   - **ASD-STE100 technical comments** before every block explaining **WHY** (not what), short sentences (≤ 25 words).
   - **Google-style docstrings** with explicit `Args:` and `Returns:` on all functions and methods.

---

## 2. Git Workflow & Branch Protection

- **Direct commits or pushes to `main` are strictly prohibited.**
- Always create a dedicated branch before making changes:
  - `feat/<feature-name>` for new capabilities
  - `fix/<bug-name>` for bug fixes
  - `refactor/<scope>` for restructuring
  - `chore/<task>` for maintenance, dependencies, and docs
- All changes must be merged into `main` exclusively through GitHub Pull Requests.

---

## 3. Local Development Setup

### Prerequisites
- **Python**: 3.13+ installed with [`uv`](https://docs.astral.sh/uv/)
- **Frontend**: [`bun`](https://bun.sh/) (Bun only; never use `npm` or commit `package-lock.json`)
- **Task Runner**: [`just`](https://github.com/casey/just)

### Setup Steps
```bash
# 1. Clone your fork
git clone https://github.com/<your-username>/Idunn.git
cd Idunn

# 2. Install backend dependencies
uv sync

# 3. Install frontend dependencies
bun install --cwd frontend

# 4. Copy environment configuration
cp .env.example .env
```

---

## 4. Verification & Testing

Before staging or committing any code, verify your changes pass all linters and tests:

```bash
# Run all linters (Ruff + Oxlint)
just lint

# Run all automated tests (Python pytest + Bun test)
just test

# Check PR diff granularity and update review lock
just review

# Verify review lock validity
just review-verify
```

---

## 5. Licensing of Contributions

By submitting a pull request to Iðunn, you agree that your contributions will be licensed under the [Lycaon Source-Available License with AI Restrictions (LSAL-AI 1.0)](LICENSE.md). Full rights are granted to Lycaon Industries to maintain, dual-license, or relicense the software.
