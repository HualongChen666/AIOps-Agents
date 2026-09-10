# -*- coding: utf-8 -*-
import os
import pathlib

import yaml

REPO_ROOT = pathlib.Path(os.getenv("AIOPS_ROOT", pathlib.Path(__file__).resolve().parents[1]))
path = pathlib.Path(
    os.getenv("AIOPS_OPENAPI", str(REPO_ROOT / "docs" / "api" / "openapi.yaml"))
)
with open(path, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)
count = 0
for p, methods in data.get("paths", {}).items():
    for m in methods.keys():
        if m.lower() in ["get", "post", "put", "delete", "patch"]:
            count += 1
print("Total HTTP verb endpoints:", count)
