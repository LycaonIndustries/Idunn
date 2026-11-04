"""Unified test runner executing backend and frontend test suites for Iðunn."""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def run_backend_tests(verbose: bool = False) -> tuple[bool, float]:
    """Execute Python pytest test suite for backend services.

    Args:
        verbose: True to enable verbose test output.

    Returns:
        Tuple of (success_boolean, elapsed_seconds).
    """
    # Use uv runner if available to guarantee virtual environment consistency.
    uv_path = shutil.which("uv")
    if uv_path:
        cmd = [uv_path, "run", "python", "-m", "pytest"]
    else:
        cmd = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    print("\n" + "=" * 60)
    print(" [1/2] Running Backend Tests (pytest)...")
    print("=" * 60)

    start = time.perf_counter()
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    elapsed = time.perf_counter() - start

    return result.returncode == 0, elapsed


def run_frontend_tests(verbose: bool = False) -> tuple[bool, float]:
    """Execute frontend test suite using Bun test runner.

    Args:
        verbose: True to print verbose test execution details.

    Returns:
        Tuple of (success_boolean, elapsed_seconds).
    """
    bun_path = shutil.which("bun")
    if not bun_path:
        print("\n❌ Error: Bun is not installed or not in PATH.")
        print("Install Bun from https://bun.sh to run frontend tests.")
        return False, 0.0

    cmd = [bun_path, "test"]
    if verbose:
        cmd.append("--verbose")

    print("\n" + "=" * 60)
    print(" [2/2] Running Frontend Tests (bun test)...")
    print("=" * 60)

    start = time.perf_counter()
    result = subprocess.run(cmd, cwd=str(FRONTEND_DIR))
    elapsed = time.perf_counter() - start

    return result.returncode == 0, elapsed


def main() -> int:
    """Parse CLI arguments and run all test suites sequentially.

    Returns:
        Exit code (0 if all passed, 1 if any failed).
    """
    if sys.platform == "win32":
        with contextlib.suppress(AttributeError):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Unified test runner for Iðunn backend (pytest) and frontend (bun test)."
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run only the Python backend test suite.",
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="Run only the Bun frontend test suite.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for test runners.",
    )

    args = parser.parse_args()

    # Track results and execution durations.
    backend_ok = True
    backend_time = 0.0
    frontend_ok = True
    frontend_time = 0.0

    print("=" * 60)
    print("          Iðunn Kitchen OS - Unified Test Suite")
    print("=" * 60)

    if not args.frontend_only:
        backend_ok, backend_time = run_backend_tests(verbose=args.verbose)

    if not args.backend_only:
        frontend_ok, frontend_time = run_frontend_tests(verbose=args.verbose)

    # Print final summary banner with elapsed execution times.
    print("\n" + "=" * 60)
    print("                      Test Run Summary")
    print("=" * 60)

    if not args.frontend_only:
        status_label = "[PASSED]" if backend_ok else "[FAILED]"
        print(f" Backend (pytest) : {status_label} ({backend_time:.2f}s)")

    if not args.backend_only:
        status_label = "[PASSED]" if frontend_ok else "[FAILED]"
        print(f" Frontend (bun)   : {status_label} ({frontend_time:.2f}s)")

    print("=" * 60)

    total_time = backend_time + frontend_time
    if backend_ok and frontend_ok:
        print(f"SUCCESS: All test suites passed! (Total: {total_time:.2f}s)\n")
        return 0

    print(f"FAILURE: One or more test suites failed. (Total: {total_time:.2f}s)\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
