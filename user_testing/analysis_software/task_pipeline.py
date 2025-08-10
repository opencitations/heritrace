#!/usr/bin/env python3
"""
Run task analysis pipeline: compute metrics, then generate plots.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_script(python_executable: str, script_path: Path) -> None:
    result = subprocess.run([python_executable, str(script_path)], capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    if result.stdout:
        sys.stdout.write(result.stdout)


def main() -> None:
    python_executable = sys.executable or "python3"

    script_dir = Path(__file__).resolve().parent
    metrics_path = script_dir / "task_metrics.py"
    plots_path = script_dir / "task_plots.py"

    # 1) Compute metrics first
    run_script(python_executable, metrics_path)
    # 2) Then generate plots
    run_script(python_executable, plots_path)


if __name__ == "__main__":
    main()
