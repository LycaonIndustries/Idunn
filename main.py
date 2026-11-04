"""Single-command entrypoint to run Iðunn Kitchen OS."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "backend" / "web_dist" / "index.html"


def main():
    if not WEB_DIST.exists():
        print("⚡ Frontend bundle not found. Building with npm...")
        subprocess.run(["npm", "--prefix", "frontend", "run", "build"], check=True)

    print("🚀 Starting Iðunn Kitchen OS on http://127.0.0.1:8000...")
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
