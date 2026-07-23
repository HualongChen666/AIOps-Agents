# -*- coding: utf-8 -*-

import yaml

OPENAPI_PATH = r"C:\\AIOps_Agent_bak\\openapi.yaml"

with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

components = data.get("components", {})
schemas = components.get("schemas", {})


# helper to generate example from schema
def gen_example(schema):
    if not schema:
        return {}
    if "$ref" in schema:
        ref = schema["$ref"]
        name = ref.split("/")[-1]
        return gen_example(schemas.get(name, {}))
    typ = schema.get("type")
    if typ == "object":
        example = {}
        props = schema.get("properties", {})
        for prop, prop_schema in props.items():
            example[prop] = gen_example(prop_schema)
        return example
    if typ == "array":
        item_schema = schema.get("items")
        return [gen_example(item_schema)]
    if typ == "string":
        fmt = schema.get("format")
        if fmt == "date-time":
            return "2023-01-01T00:00:00Z"
        enum = schema.get("enum")
        if enum:
            return enum[0]
        return "example"
    if typ == "integer" or typ == "number":
        return 0
    if typ == "boolean":
        return False
    return None


paths = data.get("paths", {})
for path, methods in paths.items():
    for method, details in methods.items():
        if method.lower() not in ["get", "post", "put", "delete", "patch"]:
            continue
        resp = details.get("responses", {}).get("200")
        if not resp:
            continue
        content = resp.setdefault("content", {})
        app_json = content.setdefault("application/json", {})
        if "example" not in app_json:
            schema = app_json.get("schema")
            example = gen_example(schema)
            app_json["example"] = example

# write back
with open(OPENAPI_PATH, "w", encoding="utf-8") as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
print("Examples populated based on schemas.")
