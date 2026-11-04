---
description: Strictly prohibit direct commits or pushes to main/master branches
trigger: always_on
---

# Git Workflow: Direct Commits to Main/Master are Banned

> [!CAUTION]
> Direct commits and direct pushes to `main` or `master` are strictly prohibited.

## Rules

1. **Never commit on `main` or `master`**:
   Before making any code changes or staging files, verify the current branch:
   `git branch --show-current`
   If on `main` or `master`, immediately checkout a new feature branch:
   `git checkout -b <type>/<description>`
   (e.g., `feat/...`, `fix/...`, `refactor/...`, `chore/...`).

2. **Never push to `main` or `master`**:
   All code changes must be pushed to their dedicated remote branch:
   `git push origin <branch-name>`

3. **All merges must use Pull Requests**:
   Every change must be submitted and reviewed as a Pull Request targeting `main`.
