# -*- coding: utf-8 -*-
import json
import os
import pathlib

import yaml

REPO_ROOT = pathlib.Path(os.getenv("AIOPS_ROOT", pathlib.Path(__file__).resolve().parents[1]))
path = pathlib.Path(
    os.getenv("AIOPS_OPENAPI", str(REPO_ROOT / "docs" / "api" / "openapi.yaml"))
)
with open(path, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)
missing = []
for p, methods in data.get("paths", {}).items():
    for m, details in methods.items():
        if m.lower() in ["get", "post", "put", "delete", "patch"]:
            resp = details.get("responses", {}).get("200")
            if resp:
                content = resp.get("content", {})
                app_json = content.get("application/json")
                if app_json and "example" not in app_json:
                    missing.append(f"{m.upper()} {p}")
print(json.dumps(missing, ensure_ascii=False, indent=2))
