#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run core/api/infrastructure/unit/root tests sequentially and build a single coverage report."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def clean_coverage() -> None:
    """Remove stale coverage artifacts before a fresh run."""
    for pattern in (".coverage", ".coverage.*", ".coverage_*", "coverage.json", "coverage.xml"):
        for path in ROOT.glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink()
            except FileNotFoundError:
                pass


def run() -> int:
    clean_coverage()

    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    root_tests = sorted(
        str(p) for p in (ROOT / "tests").glob("test_*.py") if "_integration" not in p.name
    )

    # API 测试文件按文件分发到单独 worker，避免 sys.modules 跨文件 mock 污染
    api_file_count = len(list((ROOT / "tests" / "api").glob("test_*.py")))

    phases = [
        ("core", ["tests/core"], "auto", None),
        ("api", ["tests/api"], str(api_file_count), "loadfile"),
        ("infrastructure", ["tests/infrastructure"], "auto", None),
        ("unit", ["tests/unit"], "auto", None),
        ("root", root_tests, "auto", None),
    ]

    def build_command(n_workers, dist):
        parts = [
            "--strict-markers --disable-warnings --tb=short --verbose --showlocals",
            f"-n {n_workers}",
            "--cov=core --cov=api --cov-append -m 'not performance'",
        ]
        if dist:
            parts.append(f"--dist={dist}")
        addopts = " ".join(parts)
        return [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            f"addopts={addopts}",
            "--timeout=120",
        ]

    with open("cov_full.log", "w", encoding="utf-8") as out, open(
        "cov_full_err.log", "w", encoding="utf-8"
    ) as err:
        any_failed = False
        for name, paths, n_workers, dist in phases:
            out.write(f"\n=== Running {name} tests ===\n")
            out.flush()
            rc = subprocess.call(
                build_command(n_workers, dist) + paths,
                env=env,
                stdout=out,
                stderr=err,
            )
            out.write(
                f"\n=== {name} phase exited with {rc} ===\n"
            )
            out.flush()
            if rc != 0:
                any_failed = True

        out.write("\n=== Generating coverage JSON ===\n")
        out.flush()
        subprocess.call(
            [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
            stdout=out,
            stderr=err,
        )
        subprocess.call([sys.executable, "cov_summary.py"], stdout=out, stderr=err)
        out.write("\n=== DONE ===\n")
        out.flush()

    Path("cov_status.json").write_text(
        json.dumps({"status": "DONE", "any_failed": any_failed, "pid": None}),
        encoding="utf-8",
    )
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(run())
