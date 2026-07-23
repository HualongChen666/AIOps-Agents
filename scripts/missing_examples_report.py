# -*- coding: utf-8 -*-
import json
import pathlib

import yaml

openapi_path = pathlib.Path(r"C:\\AIOps_Agent_bak\\openapi.yaml")
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
