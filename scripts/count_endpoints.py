# -*- coding: utf-8 -*-

import yaml

path = r"C:\\AIOps_Agent_bak\\openapi.yaml"
with open(path, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)
count = 0
for p, methods in data.get("paths", {}).items():
    for m in methods.keys():
        if m.lower() in ["get", "post", "put", "delete", "patch"]:
            count += 1
print("Total HTTP verb endpoints:", count)
