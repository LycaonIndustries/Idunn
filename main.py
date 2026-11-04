"""Single-command entrypoint to run Iðunn Kitchen OS."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "backend" / "web_dist" / "index.html"


def main() -> None:
    """Run the Iðunn Kitchen OS application.

    Builds the frontend bundle with Bun if absent, then starts Uvicorn.

    Returns:
        None.
    """
    # Automatically build frontend bundle on initial startup if missing.
    if not WEB_DIST.exists():
        print("⚡ Frontend bundle not found. Building with Bun...")
        runner = "bun" if shutil.which("bun") else "npm"
        if runner == "bun":
            subprocess.run(["bun", "run", "--cwd", "frontend", "build"], check=True)
        else:
            subprocess.run(["npm", "--prefix", "frontend", "run", "build"], check=True)

    print("🚀 Starting Iðunn Kitchen OS on http://127.0.0.1:8000...")
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
