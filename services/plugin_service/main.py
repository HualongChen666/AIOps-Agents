# -*- coding: utf-8 -*-
"""Standalone entry point for the plugin microservice.

Runs the FastAPI app from ``main_app`` with uvicorn. ``python -m
services.plugin_service.main [port]`` overrides the configured port.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plugin_service.config import settings  # noqa: E402


def main() -> None:
    """Start the plugin service."""
    uvicorn.run(
        "services.plugin_service.main_app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(sys.argv[1]) if len(sys.argv) > 1 else settings.orchestrator_port,
    )


if __name__ == "__main__":
    main()
