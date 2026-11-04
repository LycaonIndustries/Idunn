# PR Granularity & Algorithmic-First Policy

> [!IMPORTANT]
> All code changes in this repository must strictly adhere to atomic, granular PR sizing and the algorithmic-first principle.

## 1. Strict PR Sizing & Atomicity
- **Max Diff Target:** ≤ 350 lines per PR (hard ceiling: 500 lines, excluding lockfiles/generated assets).
- **One PR per Distinct Sub-Capability:** Never club backend engines, API routes, and frontend views together.
  - Core Business / Algorithm Logic -> Standalone PR
  - REST API Routes & Wiring -> Standalone PR
  - Frontend Workspace / UI View -> Standalone PR
- **Stacking Protocol:** Stack PRs cleanly (`branch-b` branched off `branch-a`). Keep each PR reviewable in < 5 minutes.
- **Review Lock Verification:** Run `just review` (or `uv run python scripts/dev_review.py --mode=audit`) to verify diff metrics. The pre-push hook blocks pushes if limits are violated.

## 2. Algorithmic-First Policy (AI is strictly an opt-in fallback)
- **Vault Retrieval First:** Primary features must search and match existing vault recipes and pantry stock deterministically.
- **No Pawned-Off AI:** If a problem can be solved with graphs, taxonomies, fuzzy matching, or regex (e.g., ingredient matching, substitution lookup, unit conversion), it MUST be solved algorithmically.
- **Generative AI must be User-Triggered:** Generative chef LLMs must NEVER trigger automatically or serve as the default screen. They must sit behind an explicit, deliberate user action.
