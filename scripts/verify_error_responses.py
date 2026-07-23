# -*- coding: utf-8 -*-
import json
import sys

import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_errors(data):
    missing = []
    required = {"400", "401", "403", "404", "500"}
    for path, methods in data.get("paths", {}).items():
        for verb, details in methods.items():
            if not isinstance(details, dict):
                continue
            resp = set(details.get("responses", {}).keys())
            miss = required - resp
            if miss:
                missing.append({"path": path, "method": verb, "missing": list(miss)})
    return missing


if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\AIOps_Agent_bak\openapi.yaml"
    data = load_yaml(yaml_path)
    missing = check_errors(data)
    print(
        json.dumps(
            {"missing_count": len(missing), "details": missing[:10]}, ensure_ascii=False, indent=2
        )
    )
