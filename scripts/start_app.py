"""Start API + dashboard together (local demo and single-port cloud deploy).

Usage (from the repo root):
    venv/Scripts/python.exe scripts/start_app.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    os.chdir(REPO_ROOT)
    os.environ.setdefault("FOODFLOW_API_URL", "http://127.0.0.1:8000/api")

    seed = subprocess.run(
        [sys.executable, "-m", "backend.seed"],
        cwd=REPO_ROOT,
    )
    if seed.returncode != 0:
        print("Seed step reported an error; continuing if the database already exists.")

    qr = subprocess.run(
        [sys.executable, "scripts/generate_qr.py"],
        cwd=REPO_ROOT,
    )

    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        cwd=REPO_ROOT,
    )
    time.sleep(2)

    dashboard_port = os.environ.get("PORT", "8501")
    try:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "dashboard/app.py",
                "--server.address",
                "0.0.0.0",
                "--server.port",
                str(dashboard_port),
                "--server.headless",
                "true",
            ],
            cwd=REPO_ROOT,
        )
    finally:
        api.terminate()
        try:
            api.wait(timeout=8)
        except subprocess.TimeoutExpired:
            api.kill()


if __name__ == "__main__":
    main()
