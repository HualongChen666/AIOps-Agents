#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the Python bindings for every ``proto/*.proto`` file.

Produces ``proto/<name>_pb2.py`` and ``proto/<name>_pb2_grpc.py`` (importable as
``proto.<name>_pb2``). Requires ``grpcio-tools``.

Usage::

    python scripts/generate_proto.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.getenv("AIOPS_ROOT", Path(__file__).resolve().parents[1]))
PROTO_DIR = REPO_ROOT / "proto"


def main() -> int:
    protos = sorted(p.name for p in PROTO_DIR.glob("*.proto"))
    if not protos:
        print(f"No .proto files found in {PROTO_DIR}")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        "-I",
        str(REPO_ROOT),
        f"--python_out={REPO_ROOT}",
        f"--grpc_python_out={REPO_ROOT}",
        *[f"proto/{name}" for name in protos],
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    generated = sorted(p.name for p in PROTO_DIR.glob("*_pb2*.py"))
    print(f"Generated {len(generated)} files: {', '.join(generated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
