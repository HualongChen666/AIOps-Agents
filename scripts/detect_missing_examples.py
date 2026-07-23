# -*- coding: utf-8 -*-
import json

import yaml

path = r"C:\\AIOps_Agent_bak\\openapi.yaml"
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
