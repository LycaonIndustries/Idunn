"""Development review tool and lockfile validator for Iðunn Kitchen OS.

Audits PR granularity against base branch and maintains a tamper-evident uncommitted .review.lock.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Default ceiling for PR granularity in lines changed.
DEFAULT_MAX_DIFF_LINES = int(os.environ.get("MAX_DIFF_LINES", "500"))


def run_git(args: list[str], root: Path | None = None) -> str:
    """Execute git command and return standard output.

    Args:
        args: Git argument tokens.
        root: Optional working directory.

    Returns:
        Stripped standard output string.
    """
    res = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def get_git_root() -> Path:
    """Find the root directory of the current git repository.

    Returns:
        Path to the repository root directory.
    """
    return Path(run_git(["rev-parse", "--show-toplevel"]))


def get_current_branch() -> str:
    """Get the active branch name.

    Returns:
        Current branch name string.
    """
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"])


def get_head_commit() -> str:
    """Get full commit hash of HEAD.

    Returns:
        Full 40-character commit hash string.
    """
    return run_git(["rev-parse", "HEAD"])


def resolve_base_branch(root: Path, target_base: str | None = None) -> str:
    """Determine the base target branch for comparison.

    Args:
        root: Git repository root directory.
        target_base: Optional explicitly requested base branch.

    Returns:
        Resolved base branch ref string.
    """
    if target_base:
        return target_base
    env_base = os.environ.get("REVIEW_BASE")
    if env_base:
        return env_base
    res = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return "origin/main" if res.returncode == 0 else "main"


def get_review_secret(root: Path) -> bytes:
    """Retrieve or generate local machine secret key for lockfile HMAC.

    Args:
        root: Git repository root directory.

    Returns:
        Secret key bytes.
    """
    git_dir = root / ".git"
    secret_file = git_dir / "review_lock_secret"
    if secret_file.exists():
        return secret_file.read_bytes().strip()

    new_secret = os.urandom(32).hex().encode("utf-8")
    try:
        secret_file.write_bytes(new_secret)
    except OSError:
        return hashlib.sha256(str(root).encode("utf-8")).digest()
    return new_secret


def calculate_diff_stats(root: Path, base: str, head: str) -> dict[str, Any]:
    """Calculate line additions and deletions against base branch.

    Args:
        root: Git repository root directory.
        base: Target base branch ref.
        head: Current branch or HEAD ref.

    Returns:
        Dictionary containing added, deleted, total lines, and file list.
    """
    res = subprocess.run(
        ["git", "diff", "--numstat", f"{base}...{head}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = res.stdout if res.returncode == 0 else run_git(["diff", "--numstat", base, head], root)

    ignored_suffixes = (".lock", "bun.lock", "package-lock.json", ".min.js", ".min.css")
    total_added, total_deleted = 0, 0
    modified_files: list[str] = []

    for line in output.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[0] == "-" or parts[1] == "-":
            continue
        filepath = parts[2]
        if any(filepath.endswith(suf) for suf in ignored_suffixes):
            continue
        total_added += int(parts[0])
        total_deleted += int(parts[1])
        modified_files.append(filepath)

    return {
        "lines_added": total_added,
        "lines_deleted": total_deleted,
        "total_diff_lines": total_added + total_deleted,
        "files_count": len(modified_files),
        "files": modified_files,
    }


def compute_signature(payload: dict[str, Any], secret: bytes) -> str:
    """Calculate HMAC-SHA256 signature for lockfile payload.

    Args:
        payload: Canonical payload dictionary without signature field.
        secret: Secret key bytes.

    Returns:
        Hex-encoded HMAC signature string.
    """
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret, serialized.encode("utf-8"), hashlib.sha256).hexdigest()


def audit_repository(
    root: Path, base_branch: str | None = None, max_lines: int = DEFAULT_MAX_DIFF_LINES
) -> dict[str, Any]:
    """Execute review checks and create signed lockfile structure.

    Args:
        root: Git repository root directory.
        base_branch: Optional base branch target.
        max_lines: Maximum permitted lines in diff.

    Returns:
        Complete lockfile dictionary including HMAC signature.
    """
    branch = get_current_branch()
    head = get_head_commit()
    base = resolve_base_branch(root, base_branch)
    diff = calculate_diff_stats(root, base, head)
    secret = get_review_secret(root)

    status_out = run_git(["status", "--porcelain"], root)
    payload = {
        "version": 1,
        "branch": branch,
        "base_branch": base,
        "head_commit": head,
        "diff_metrics": {
            "lines_added": diff["lines_added"],
            "lines_deleted": diff["lines_deleted"],
            "total_diff_lines": diff["total_diff_lines"],
            "files_count": diff["files_count"],
            "max_allowed_lines": max_lines,
            "is_within_limit": diff["total_diff_lines"] <= max_lines,
        },
        "clean_working_tree": not bool(status_out),
    }

    payload["signature"] = compute_signature(payload, secret)
    return payload


def write_lockfile(root: Path, data: dict[str, Any]) -> Path:
    """Save generated review lockfile to repo root.

    Args:
        root: Git repository root directory.
        data: Signed lockfile data dictionary.

    Returns:
        Path to the saved lockfile.
    """
    lock_path = root / ".review.lock"
    lock_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return lock_path


def verify_lockfile(root: Path, max_lines: int = DEFAULT_MAX_DIFF_LINES) -> tuple[bool, str]:
    """Verify that current repository state satisfies review lockfile constraints.

    Args:
        root: Git repository root directory.
        max_lines: Expected maximum diff lines limit.

    Returns:
        Tuple of (is_valid, reason_message).
    """
    lock_path = root / ".review.lock"
    if not lock_path.exists():
        return False, "No .review.lock found. Run 'just review' or commit changes."

    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Failed to parse .review.lock: {exc}"

    if "signature" not in data:
        return False, ".review.lock is missing cryptographic signature."

    stored_sig = data.pop("signature")
    secret = get_review_secret(root)
    expected_sig = compute_signature(data, secret)

    if not hmac.compare_digest(stored_sig, expected_sig):
        return False, "Tamper detected: .review.lock signature is invalid! Manually modified."

    current_head = get_head_commit()
    if data.get("head_commit") != current_head:
        locked_head = str(data.get("head_commit", ""))[:7]
        msg = f".review.lock is stale. Locked {locked_head} != current HEAD {current_head[:7]}."
        return False, msg

    metrics = data.get("diff_metrics", {})
    total_lines = metrics.get("total_diff_lines", 0)
    if total_lines > max_lines:
        msg = f"PR diff ({total_lines} lines) exceeds {max_lines}-line limit! Split this feature."
        return False, msg

    return True, "Review lockfile verified successfully."


def main() -> int:
    """CLI entrypoint for dev_review tool.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    parser = argparse.ArgumentParser(description="Development review auditor and lock manager.")
    parser.add_argument(
        "--mode",
        choices=["audit", "verify"],
        default="audit",
        help="audit: compute and update lockfile; verify: validate lockfile",
    )
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Target base branch for comparison (e.g. parent branch for stacked PRs).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_DIFF_LINES,
        help=f"Max allowed lines changed against base branch (default: {DEFAULT_MAX_DIFF_LINES}).",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 on oversized diff.")

    args = parser.parse_args()
    try:
        root = get_git_root()
    except Exception as err:
        print(f"[FAIL] Error: {err}", file=sys.stderr)
        return 1

    if args.mode == "verify":
        valid, msg = verify_lockfile(root, max_lines=args.max_lines)
        if not valid:
            print(f"[FAIL] REVIEW GATE FAILED: {msg}", file=sys.stderr)
            return 1
        print(f"[OK] {msg}")
        return 0

    audit_data = audit_repository(root, base_branch=args.base, max_lines=args.max_lines)
    write_lockfile(root, audit_data)
    metrics = audit_data["diff_metrics"]
    diff_lines = metrics["total_diff_lines"]
    within_limit = metrics["is_within_limit"]
    status_str = (
        f"[PASS] (<= {args.max_lines})" if within_limit else f"[OVERSIZED] (> {args.max_lines})"
    )

    print("==================================================")
    print("Idunn Development Review Lock Updated")
    print(f"   Branch:       {audit_data['branch']}")
    print(f"   Base:         {audit_data['base_branch']}")
    print(
        f"   Diff:         +{metrics['lines_added']} / -{metrics['lines_deleted']} "
        f"({diff_lines} lines)"
    )
    print(f"   Files:        {metrics['files_count']} files changed")
    print(f"   Granularity:  {status_str}")
    print("==================================================")

    if not within_limit:
        print(
            f"[WARN] NOTICE: This PR diff is {diff_lines} lines (> {args.max_lines} limit).",
            file=sys.stderr,
        )
        print(
            "   Consider splitting into smaller atomic PRs before submitting review.",
            file=sys.stderr,
        )
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
