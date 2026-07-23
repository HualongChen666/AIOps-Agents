# -*- coding: utf-8 -*-

import yaml
from openapi_spec_validator import validate_spec

path = r"C:\\AIOps_Agent_bak\\openapi.yaml"
with open(path, encoding="utf-8") as f:
    spec = yaml.safe_load(f)
try:
    validate_spec(spec)
    print("OpenAPI validation passed")
except Exception as e:
    print("Validation error:", e)
