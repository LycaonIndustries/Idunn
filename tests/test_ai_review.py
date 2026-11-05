"""Unit tests for automated AI review engine script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ai_review import (
    build_github_review_payload,
    build_review_prompt,
    check_granularity_limit,
    extract_valid_diff_lines,
    load_repository_rules,
    parse_gemini_response,
)


@pytest.mark.parametrize(
    ("lines", "expected_valid", "expected_text"),
    [(350, True, "PASS"), (501, False, "exceeds")],
)
def test_check_granularity_limit(lines: int, expected_valid: bool, expected_text: str) -> None:
    """Verify granularity checks against maximum permitted lines."""
    is_valid, message = check_granularity_limit(
        {"total_lines": lines, "additions": lines, "deletions": 0}, max_lines=500
    )
    assert is_valid is expected_valid and expected_text in message


def test_extract_valid_diff_lines() -> None:
    """Verify extraction of valid line numbers from unified diff text."""
    sample = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -10,2 +10,3 @@\n x\n+y 11\n+z 12\n"
    )
    valid = extract_valid_diff_lines(sample)
    assert {11, 12}.issubset(valid.get("a.py", set()))


def test_load_repository_rules(tmp_path: Path) -> None:
    """Verify loading repository markdown rules from directory."""
    (tmp_path / "test-rule.md").write_text("# Test Rule\nRule content.", encoding="utf-8")
    content = load_repository_rules(tmp_path)
    assert "# Test Rule" in content and "Rule content." in content


def test_build_review_prompt() -> None:
    """Verify review prompt incorporates diff, rules, and files."""
    prompt = build_review_prompt("diff text", "rules", {"api.py": "def test(): pass"})
    assert "diff text" in prompt and "rules" in prompt and "api.py" in prompt


@pytest.mark.parametrize(
    ("raw_input", "expected_verdict", "expected_findings_count"),
    [
        (
            json.dumps({"verdict": "needs-changes", "findings": [{"file": "a.py", "line": 1}]}),
            "needs-changes",
            1,
        ),
        ('```json\n{"verdict": "ready", "findings": []}\n```', "ready", 0),
        ("", "error", 0),
        ("invalid json", "error", 0),
    ],
)
def test_parse_gemini_response(
    raw_input: str, expected_verdict: str, expected_findings_count: int
) -> None:
    """Verify parsing valid, fenced, and corrupted model responses."""
    parsed = parse_gemini_response(raw_input)
    assert parsed["verdict"] == expected_verdict
    assert len(parsed["findings"]) == expected_findings_count


def test_build_github_review_payload() -> None:
    """Verify payload generation for GitHub PR review API."""
    findings = [
        {"file": "a.py", "line": 11, "severity": "L1", "explanation": "Check missing."},
        {"file": "a.py", "line": 999, "severity": "nit", "explanation": "General note."},
        {"file": "b.py", "line": None, "severity": "L0", "explanation": "File level."},
    ]
    p = build_github_review_payload("sha123", "needs-changes", "Audit.", findings, {"a.py": {11}})
    assert p["commit_id"] == "sha123" and p["event"] == "COMMENT"
    assert len(p["comments"]) == 1 and p["comments"][0]["line"] == 11
    assert "General note" in p["body"] and "File level" in p["body"]
