#!/usr/bin/env python3
"""Single offline entry point for manuscript evidence; never collect or score."""

from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "paper/scripts/reproduce.py"),
        run_name="__main__",
    )
