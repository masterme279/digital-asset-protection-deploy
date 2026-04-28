from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 1 platform ingestion server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--sample-root", type=Path, default=Path("data/raw"))
    return parser


def main() -> None:
    script_path = Path(__file__).resolve()
    project_root = script_path.parents[2]
    venv_python = project_root / "venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    force_project_venv = os.getenv("PHASE1_FORCE_PROJECT_VENV", "0").strip().lower() in {"1", "true", "yes"}

    if force_project_venv and venv_python.exists() and current_python != venv_python.resolve():
        try:
            probe = subprocess.run(
                [str(venv_python), "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"Switching interpreter to project venv: {venv_python} ({probe.stdout.strip()})")
            os.chdir(str(project_root))
            os.execv(
                str(venv_python),
                [
                    str(venv_python),
                    "-m",
                    "ai_pipeline.scripts.run_phase1_server",
                    *sys.argv[1:],
                ],
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Project venv probe failed, using current interpreter instead: {exc}")

    # Ensure the repo root is importable even if executed from another CWD.
    os.chdir(str(project_root))
    sys.path.insert(0, str(project_root))

    args = build_parser().parse_args()
    from ai_pipeline.platform.api import create_app

    app = create_app(sample_root=args.sample_root)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
