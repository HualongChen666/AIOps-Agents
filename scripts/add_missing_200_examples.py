# -*- coding: utf-8 -*-
import pathlib

import yaml

openapi_path = pathlib.Path(r"C:\AIOps_Agent_bak\openapi.yaml")
openapi = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))


# Define placeholder examples for missing endpoints
def placeholder(example_type="generic"):
    if example_type == "anomaly":
        return {
            "id": 1,
            "name": "example-anomaly",
            "severity": "critical",
            "status": "open",
            "detected_at": "2026-07-08T12:00:00Z",
        }
    if example_type == "workflow":
        return {"id": 1, "name": "example-workflow", "steps": [], "status": "inactive"}
    if example_type == "policy":
        return {"id": 1, "name": "example-policy", "rules": [], "enabled": True}
    # generic fallback
    return {"message": "success"}


paths = openapi.get("paths", {})

# Mapping of (path, method) to example type key
missing_map = {
    ("/anomalies", "post"): "anomaly",
    ("/anomalies/{anomaly_id}", "delete"): "anomaly",
    ("/workflows", "post"): "workflow",
    ("/policies", "post"): "policy",
}

for (p, m), ex_type in missing_map.items():
    method_dict = paths.get(p, {})
    details = method_dict.get(m, {})
    resp = details.setdefault("responses", {})
    r200 = resp.setdefault("200", {})
    content = r200.setdefault("content", {})
    app_json = content.setdefault("application/json", {})
    # Insert example if absent
    if "example" not in app_json:
        app_json["example"] = placeholder(ex_type)

# Write back
openapi_path.write_text(
    yaml.safe_dump(openapi, sort_keys=False, allow_unicode=True), encoding="utf-8"
)
print("Added missing 200 examples")
