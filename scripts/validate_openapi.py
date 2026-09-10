# -*- coding: utf-8 -*-
import os
import pathlib

import yaml
from openapi_spec_validator import validate_spec

REPO_ROOT = pathlib.Path(os.getenv("AIOPS_ROOT", pathlib.Path(__file__).resolve().parents[1]))
path = pathlib.Path(
    os.getenv("AIOPS_OPENAPI", str(REPO_ROOT / "docs" / "api" / "openapi.yaml"))
)
with open(path, encoding="utf-8") as f:
    spec = yaml.safe_load(f)
try:
    validate_spec(spec)
    print("OpenAPI validation passed")
except Exception as e:
    print("Validation error:", e)
