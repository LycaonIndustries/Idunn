"""Automated AI code review engine for Iðunn Kitchen OS."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MAX_DIFF_LINES = 500
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"


def run_git(args: list[str], root: Path | None = None) -> str:
    """Execute git command and return standard output."""
    res = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def calculate_diff_stats(root: Path, base: str, head: str) -> dict[str, Any]:
    """Calculate line additions and deletions against base branch."""
    stat_out = run_git(["diff", f"{base}...{head}", "--shortstat"], root=root)
    name_out = run_git(["diff", f"{base}...{head}", "--name-only"], root=root)
    files = [f.strip() for f in name_out.splitlines() if f.strip()]
    adds = int(m.group(1)) if (m := re.search(r"(\d+)\s+insertion", stat_out)) else 0
    dels = int(m.group(1)) if (m := re.search(r"(\d+)\s+deletion", stat_out)) else 0
    return {
        "base": base,
        "head": head,
        "files_changed": files,
        "additions": adds,
        "deletions": dels,
        "total_lines": adds + dels,
    }


def check_granularity_limit(
    diff_stats: dict[str, Any], max_lines: int = DEFAULT_MAX_DIFF_LINES
) -> tuple[bool, str]:
    """Verify that pull request line diff does not exceed granularity threshold."""
    total = int(diff_stats.get("total_lines", 0))
    if total > max_lines:
        return False, f"PR exceeds limit ({total} lines, max {max_lines} per AGENTS.md)."
    return True, f"Granularity PASS: {total} lines changed (max: {max_lines})."


def extract_valid_diff_lines(diff_text: str) -> dict[str, set[int]]:
    """Extract line numbers present in new side of unified diff hunks."""
    valid_lines: dict[str, set[int]] = {}
    cur_file: str | None = None
    cur_line = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            cur_file = line[6:].strip()
            valid_lines.setdefault(cur_file, set())
        elif line.startswith("@@ ") and cur_file:
            m = re.search(r"\+(\d+)(?:,(\d+))? @@", line)
            cur_line = int(m.group(1)) if m else 0
        elif cur_file and (
            (line.startswith("+") and not line.startswith("+++")) or line.startswith(" ")
        ):
            valid_lines[cur_file].add(cur_line)
            cur_line += 1
    return valid_lines


def load_repository_rules(rules_dir: Path) -> str:
    """Read all markdown rules from directory into unified instruction string."""
    if not rules_dir.is_dir():
        return ""
    return "\n\n---\n\n".join(
        p.read_text("utf-8").strip() for p in sorted(rules_dir.glob("*.md")) if p.is_file()
    )


def build_review_prompt(diff_text: str, rules_text: str, changed_files: dict[str, str]) -> str:
    """Build structured prompt for Gemini review model."""
    ctx = "\n\n".join(f"### File: {p}\n```\n{c}\n```" for p, c in changed_files.items())
    return (
        f"You are the senior code reviewer for Iðunn Kitchen OS.\n\n### Rules\n{rules_text}\n\n"
        "### Instructions\n"
        "1. Linters passed. Focus on logic/crashes, button disabled on submit, security.\n"
        "2. Check ASD-STE100 comments (WHY not what, <=25 words).\n"
        '3. Output JSON: {"verdict": "ready|needs-changes|high-risk", "summary": "...",\n'
        '   "findings": [{"file": "...", "line": 1, '
        '"severity": "L0|L1|nit", "explanation": "..."}]}\n\n'
        f"### Files\n{ctx}\n\n### Diff\n```diff\n{diff_text}\n```\n"
    )


def parse_gemini_response(response_text: str) -> dict[str, Any]:
    """Parse and sanitize JSON response from Gemini model."""
    txt = response_text.strip()
    if not txt:
        return {"verdict": "error", "summary": "Empty model response.", "findings": []}
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
        txt = re.sub(r"\n?```$", "", txt).strip()
    try:
        data = json.loads(txt)
    except json.JSONDecodeError:
        return {"verdict": "error", "summary": "Invalid JSON response.", "findings": []}
    return {
        "verdict": data.get("verdict", "ready"),
        "summary": data.get("summary", "Review completed."),
        "findings": data.get("findings", []) if isinstance(data.get("findings"), list) else [],
    }


def call_gemini_api(api_key: str, prompt: str, model: str = DEFAULT_GEMINI_MODEL) -> str:
    """Call Google AI Studio Gemini API endpoint with structured JSON output."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return str(data["candidates"][0]["content"]["parts"][0]["text"])
    except (urllib.error.URLError, OSError, KeyError, IndexError) as err:
        print(f"Gemini API request failed: {err}")
        return ""


def build_github_review_payload(
    commit_sha: str,
    verdict: str,
    summary: str,
    findings: list[dict[str, Any]],
    valid_lines: dict[str, set[int]],
) -> dict[str, Any]:
    """Construct GitHub PR review payload containing inline comments and summary."""
    inlines: list[dict[str, Any]] = []
    generals: list[str] = []
    for item in findings:
        f = str(item.get("file", ""))
        raw_l = item.get("line")
        line = int(raw_l) if isinstance(raw_l, int | str) and str(raw_l).isdigit() else 0
        sev, exp = str(item.get("severity", "L1")), str(item.get("explanation", ""))
        if f in valid_lines and line in valid_lines[f]:
            inlines.append({"path": f, "line": line, "body": f"**{sev}** — {exp}"})
        else:
            generals.append(f"- **{sev}** `{f}:{line}`: {exp}")

    body = [f"### Automated AI Code Review\n\n- **Verdict:** `{verdict}`\n- **Summary:** {summary}"]
    if generals:
        body.append("\n#### General Findings\n" + "\n".join(generals))
    return {
        "commit_id": commit_sha,
        "body": "\n".join(body),
        "event": "COMMENT",
        "comments": inlines,
    }


def submit_github_pr_review(token: str, repo: str, pr_number: int, payload: dict[str, Any]) -> None:
    """Submit review payload to GitHub Pull Request Review API."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "Idunn-AI-Reviewer",
        },
        method="POST",
    )
    with (
        contextlib.suppress(urllib.error.HTTPError, urllib.error.URLError),
        urllib.request.urlopen(req, timeout=30),
    ):
        print(f"Submitted AI review for PR #{pr_number}")


def main() -> int:
    """CLI entrypoint for automated code review runner."""
    parser = argparse.ArgumentParser(description="Iðunn AI Code Review Runner")
    parser.add_argument("--mode", default="audit", choices=["audit", "github-pr"])
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    root = Path.cwd()
    stats = calculate_diff_stats(root, args.base, args.head)
    is_valid, gran_msg = check_granularity_limit(stats)

    if args.mode == "github-pr":
        token, repo = os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", "")
        api_key, ev_path = (
            os.environ.get("GEMINI_API_KEY", ""),
            os.environ.get("GITHUB_EVENT_PATH", ""),
        )
        pr_num, pr_sha = None, None

        if ev_path and Path(ev_path).is_file():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                ev = json.loads(Path(ev_path).read_text("utf-8"))
                pr_info = ev.get("pull_request") or {}
                pr_num = pr_info.get("number")
                pr_sha = (pr_info.get("head") or {}).get("sha")

        if not token or not repo or not pr_num:
            return 0

        commit_sha = pr_sha or run_git(["rev-parse", args.head], root=root)

        def post_notice(verdict: str, notice: str) -> None:
            submit_github_pr_review(
                token,
                repo,
                pr_num,
                {
                    "commit_id": commit_sha,
                    "body": f"### Automated AI Review\n\n- **Verdict:** `{verdict}`\n- {notice}",
                    "event": "COMMENT",
                    "comments": [],
                },
            )

        if not is_valid:
            post_notice("high-risk", f"**Error:** {gran_msg}")
            return 0
        if not api_key:
            post_notice("notice", "**Notice:** `GEMINI_API_KEY` missing from secrets.")
            return 0

        diff_text = run_git(["diff", f"{args.base}...{args.head}"], root=root)
        valid_lines = extract_valid_diff_lines(diff_text)
        sources: dict[str, str] = {}
        for rel in stats["files_changed"]:
            p = root / rel
            if p.is_file() and p.stat().st_size < 100_000:
                with contextlib.suppress(OSError, UnicodeDecodeError):
                    sources[rel] = p.read_text("utf-8")

        prompt = build_review_prompt(
            diff_text, load_repository_rules(root / ".agents" / "rules"), sources
        )
        parsed = parse_gemini_response(call_gemini_api(api_key, prompt))
        payload = build_github_review_payload(
            commit_sha, parsed["verdict"], parsed["summary"], parsed["findings"], valid_lines
        )
        submit_github_pr_review(token, repo, pr_num, payload)
        return 0

    print(gran_msg)
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
