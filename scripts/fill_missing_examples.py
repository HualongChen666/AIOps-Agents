# -*- coding: utf-8 -*-

import yaml

path = r"C:\\AIOps_Agent_bak\\openapi.yaml"

with open(path, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)


def ensure_examples(node):
    if isinstance(node, dict):
        for method, details in node.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                responses = details.get("responses", {})
                r200 = responses.get("200")
                if r200:
                    content = r200.get("content", {})
                    app_json = content.get("application/json")
                    if app_json and "example" not in app_json:
                        # generate default_value based on schema if possible
                        schema = app_json.get("schema")
                        placeholder = {"message": "success"}
                        if schema:
                            # simple heuristic: if schema references a component,
                            # use its title or properties
                            ref = schema.get("$ref")
                            if ref:
                                comp_name = ref.split("/")[-1]
                                placeholder = {comp_name: "example"}
                        app_json["example"] = placeholder
        # recurse deeper
        for v in node.values():
            ensure_examples(v)
    elif isinstance(node, list):
        for item in node:
            ensure_examples(item)


ensure_examples(data.get("paths", {}))

# write back
with open(path, "w", encoding="utf-8") as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
print("default_value examples added where missing.")
