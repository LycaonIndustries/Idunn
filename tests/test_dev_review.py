"""Unit tests for the development review tool and lockfile validator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.dev_review import (
    compute_signature,
    get_review_secret,
    verify_lockfile,
    write_lockfile,
)


def test_compute_signature_deterministic(tmp_path: Path) -> None:
    """Verify compute_signature produces identical HMAC for equivalent payloads."""
    secret = b"test_secret_key_123"
    payload1 = {"branch": "feat/test", "commit": "abc", "lines": 100}
    payload2 = {"lines": 100, "commit": "abc", "branch": "feat/test"}

    sig1 = compute_signature(payload1, secret)
    sig2 = compute_signature(payload2, secret)

    assert sig1 == sig2
    assert len(sig1) == 64


def test_tamper_detection_on_lockfile(tmp_path: Path) -> None:
    """Verify verify_lockfile fails when signature does not match modified payload."""
    secret = b"test_secret_key_123"
    data = {
        "version": 1,
        "branch": "feat/test",
        "head_commit": "commit_123",
        "diff_metrics": {"total_diff_lines": 50, "is_within_limit": True},
    }
    data["signature"] = compute_signature(data, secret)

    # Write valid lockfile first
    write_lockfile(tmp_path, data)

    # Tamper with the diff metrics without updating signature
    tampered = json.loads((tmp_path / ".review.lock").read_text(encoding="utf-8"))
    tampered["diff_metrics"]["total_diff_lines"] = 500
    (tmp_path / ".review.lock").write_text(json.dumps(tampered), encoding="utf-8")

    with (
        patch("scripts.dev_review.get_review_secret", return_value=secret),
        patch("scripts.dev_review.get_head_commit", return_value="commit_123"),
    ):
        valid, msg = verify_lockfile(tmp_path, max_lines=400)
        assert valid is False
        assert "Tamper detected" in msg


def test_verify_lockfile_detects_oversized_diff(tmp_path: Path) -> None:
    """Verify verify_lockfile flags diffs exceeding the max_lines threshold."""
    secret = b"test_secret_key_123"
    data = {
        "version": 1,
        "branch": "feat/oversized",
        "head_commit": "commit_999",
        "diff_metrics": {"total_diff_lines": 650, "is_within_limit": False},
    }
    data["signature"] = compute_signature(data, secret)
    write_lockfile(tmp_path, data)

    with (
        patch("scripts.dev_review.get_review_secret", return_value=secret),
        patch("scripts.dev_review.get_head_commit", return_value="commit_999"),
    ):
        valid, msg = verify_lockfile(tmp_path, max_lines=400)
        assert valid is False
        assert "exceeds 400-line" in msg


def test_get_review_secret_generates_and_persists(tmp_path: Path) -> None:
    """Verify secret is created inside .git directory and reloaded consistently."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True)

    secret1 = get_review_secret(tmp_path)
    secret2 = get_review_secret(tmp_path)

    assert secret1 == secret2
    assert (git_dir / "review_lock_secret").exists()
