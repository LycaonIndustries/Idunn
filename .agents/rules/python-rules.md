# Python Style & Engineering Rules

## 1. Values & Type Safety
- **Safe Dictionary Access:** Read dictionary values using `d.get(key)` or `d.get(key, default)`. Never access untrusted dicts via `d[key]`.
- **None Caveat with `dict.get`:** Note that `dict.get('key', default)` returns `None` if the key exists with value `None`. Use `d.get('key') if d.get('key') is not None else default` when `None` is unacceptable.
- **Null & Empty Checks:** Verify variables, lists, and dicts are non-None before accessing attributes or subscripting.
- **List Removal Safety:** Check element existence before removing from lists (`if item in items: items.remove(item)`).
- **String Handling & UTF-8:** Handle non-ASCII / UTF-8 input at system boundaries. Validate payload strings against length limits ($\le$ 10,000 chars) to prevent payload exhaustion.

## 2. Control Flow & Structure
- **Early Returns & Guard Clauses:** Use guard clauses to keep nesting low. Invert conditionals to return or continue early.
- **Explicit Trailing Return:** Every function must end with an explicit `return` statement, even when returning `None`.
- **Function Length & Single Responsibility:** Keep functions short ($\le$ 40 lines). A function must perform exactly one logical action; extract secondary logic into focused helpers.
- **Call Order:** Organize functions in call order (callers before callees).
- **DRY & Reuse:** Reuse existing codebase helpers before introducing new utility functions.

## 3. Types, Docstrings & Comments
- **Type Hints:** Add type hints to function signatures (parameters and return types). Do not add type hints to local variables.
- **Google-Style Docstrings:** Every function must have a Google-style docstring with explicit `Args:` and `Returns:` sections.
- **ASD-STE100 Comments:** Write technical comments explaining **WHY** (not what) before every logical code block. Sentences must be short ($\le$ 25 words).
- **No Magic Numbers:** Assign literals to named constants in appropriate constants files or module-level `UPPERCASE` constants.

## 4. Error Handling & Logging
- **Intentional Try/Except:** Do not wrap broad logic in blank `except Exception: pass`. Handle specific exception types.
- **Logging Levels:** Use `logging.exception` in except blocks for unexpected errors. Use `logging.error` or `logging.warning` for expected validation rejections.
- **No Secret Leaks in Logs:** Never log credentials, API keys, passwords, or full raw payloads into logs.
- **Graceful Failure State:** If a variable is assigned inside a `try` block and read after it, initialize it with a safe default before the `try` block.
