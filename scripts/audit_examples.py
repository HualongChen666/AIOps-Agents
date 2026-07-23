# -*- coding: utf-8 -*-
import json

import yaml

path = r"C:\\AIOps_Agent_bak\\openapi.yaml"
with open(path, "r", encoding="utf-8") as f:
    spec = yaml.safe_load(f)
methods = ["get", "post", "put", "delete", "patch"]
total = 0
missing = []
for p, ops in spec.get("paths", {}).items():
    for m, details in ops.items():
        if m.lower() in methods:
            total += 1
            resp = details.get("responses", {}).get("200")
            if resp:
                content = resp.get("content", {})
                app_json = content.get("application/json")
                if not app_json or "example" not in app_json:
                    missing.append(f"{m.upper()} {p}")
            else:
                missing.append(f"{m.upper()} {p} (no 200 response)")
print("Total verb endpoints:", total)
print("Missing examples:", len(missing))
print(json.dumps(missing, ensure_ascii=False, indent=2))
