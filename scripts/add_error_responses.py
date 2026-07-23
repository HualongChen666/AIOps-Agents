# -*- coding: utf-8 -*-
import copy
import sys

import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def ensure_error_responses(openapi):
    error_refs = {
        "400": {"$ref": "#/components/responses/BadRequest"},
        "401": {"$ref": "#/components/responses/Unauthorized"},
        "403": {"$ref": "#/components/responses/Forbidden"},
        "404": {"$ref": "#/components/responses/NotFound"},
        "500": {"$ref": "#/components/responses/InternalServerError"},
    }
    # Ensure Forbidden response is defined in components if missing
    if "Forbidden" not in openapi.get("components", {}).get("responses", {}):
        openapi.setdefault("components", {}).setdefault("responses", {})["Forbidden"] = {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"error": {"type": "string"}, "message": {"type": "string"}},
                    }
                }
            },
        }
    for path, methods in openapi.get("paths", {}).items():
        for verb, details in methods.items():
            if not isinstance(details, dict):
                continue
            responses = details.setdefault("responses", {})
            for code, ref in error_refs.items():
                if code not in responses:
                    responses[code] = copy.deepcopy(ref)
    return openapi


if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\AIOps_Agent_bak\openapi.yaml"
    data = load_yaml(yaml_path)
    updated = ensure_error_responses(data)
    save_yaml(updated, yaml_path)
    print("Error responses added/ensured in", yaml_path)
