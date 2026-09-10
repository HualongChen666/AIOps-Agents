# -*- coding: utf-8 -*-
import json
import os
import pathlib

import yaml

REPO_ROOT = pathlib.Path(os.getenv("AIOPS_ROOT", pathlib.Path(__file__).resolve().parents[1]))
openapi_path = pathlib.Path(
    os.getenv("AIOPS_OPENAPI", str(REPO_ROOT / "docs" / "api" / "openapi.yaml"))
)
openapi = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
paths = openapi.get("paths", {})
missing = []
for p, methods in paths.items():
    for method, details in methods.items():
        resp = details.get("responses", {})
        r200 = resp.get("200")
        if not (
            r200
            and r200.get("content")
            and r200["content"].get("application/json")
            and "example" in r200["content"]["application/json"]
        ):
            missing.append({"path": p, "method": method})
print(
    json.dumps(
        {"missing_200_examples_count": len(missing), "missing": missing},
        ensure_ascii=False,
        indent=2,
    )
)
