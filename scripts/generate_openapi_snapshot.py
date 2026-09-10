#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the committed OpenAPI snapshots from the live FastAPI app.

The files ``docs/api/openapi.json`` and ``docs/api/openapi.yaml`` are generated
artifacts. They drift whenever routers change, so this script rebuilds both from
``main.app.openapi()`` (the single source of truth) and writes them in a stable
format.

Usage::

    python scripts/generate_openapi_snapshot.py            # write both files
    python scripts/generate_openapi_snapshot.py --check    # exit 1 if stale

``--check`` is intended for CI: it regenerates in memory and compares against the
committed files, failing when the snapshot is out of date.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.getenv("AIOPS_ROOT", Path(__file__).resolve().parents[1]))
OUTPUT_DIR = REPO_ROOT / "docs" / "api"
JSON_PATH = OUTPUT_DIR / "openapi.json"
YAML_PATH = OUTPUT_DIR / "openapi.yaml"


def build_spec() -> dict:
    """Build the OpenAPI document from the application object."""
    sys.path.insert(0, str(REPO_ROOT))
    from main import app  # noqa: PLC0415 - imported late so ``--help`` is fast

    return app.openapi()


def render_json(spec: dict) -> str:
    return json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def render_yaml(spec: dict) -> str:
    import yaml

    return yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit non-zero when the committed snapshots are stale.",
    )
    args = parser.parse_args()

    spec = build_spec()
    rendered_json = render_json(spec)
    rendered_yaml = render_yaml(spec)

    if args.check:
        stale = []
        for path, rendered in ((JSON_PATH, rendered_json), (YAML_PATH, rendered_yaml)):
            if not path.exists() or path.read_text(encoding="utf-8") != rendered:
                stale.append(str(path.relative_to(REPO_ROOT)))
        if stale:
            print("OpenAPI snapshot is stale: " + ", ".join(stale))
            print("Run: python scripts/generate_openapi_snapshot.py")
            return 1
        print("OpenAPI snapshot is up to date.")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(rendered_json, encoding="utf-8")
    YAML_PATH.write_text(rendered_yaml, encoding="utf-8")
    print(f"Wrote {JSON_PATH.relative_to(REPO_ROOT)} ({len(spec.get('paths', {}))} paths)")
    print(f"Wrote {YAML_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
