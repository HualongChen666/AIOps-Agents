# -*- coding: utf-8 -*-

import yaml

path = r"C:\\AIOps_Agent_bak\\openapi.yaml"
with open(path, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)
count = 0
missing = []
for p, methods in data.get("paths", {}).items():
    for method, details in methods.items():
        if method.lower() in ("get", "post", "put", "delete", "patch"):
            resp = details.get("responses", {})
            if "200" in resp:
                count += 1
                content = resp["200"].get("content", {})
                has_example = any("example" in mime_spec for mime_spec in content.values())
                if not has_example:
                    missing.append((p, method))
print("total_200_responses", count)
print("missing_examples", len(missing))
if missing:
    print("examples missing for:")
    for item in missing[:20]:
        print(item)
