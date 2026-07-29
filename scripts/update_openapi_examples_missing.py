# -*- coding: utf-8 -*-
"""Add default_value response examples for any FastAPI endpoint lacking them.
This script parses router files to collect all (path, method) pairs, then loads
openapi.yaml and ensures each endpoint has a 200 response example. If an
example already exists, it is left unchanged; otherwise a generic example is
added.
"""

import ast
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "api"
OPENAPI_PATH = PROJECT_ROOT / "openapi.yaml"


def collect_all_routes():
    routes = {}
    for py_file in API_DIR.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if getattr(node.func.value, "id", None) == "router":
                    method = node.func.attr.upper()
                    if not node.args:
                        continue
                    path_node = node.args[0]
                    if isinstance(path_node, ast.Constant):
                        path = path_node.value
                    else:
                        continue
                    routes.setdefault(path, set()).add(method)
    return routes


def ensure_examples(spec, routes):
    if "paths" not in spec:
        spec["paths"] = {}
    for path, methods in routes.items():
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        for method in methods:
            method_key = method.lower()
            if method_key not in spec["paths"][path]:
                spec["paths"][path][method_key] = {}
            spec["paths"][path][method_key].setdefault("responses", {})
            spec["paths"][path][method_key]["responses"].setdefault("200", {})
            resp200 = spec["paths"][path][method_key]["responses"]["200"]
            resp200.setdefault("description", "Successful response")
            resp200.setdefault("content", {})
            resp200["content"].setdefault("application/json", {})
            # If no example, add default_value
            if "example" not in resp200["content"]["application/json"]:
                resp200["content"]["application/json"]["example"] = {"message": "success"}
    return spec


def main():
    routes = collect_all_routes()
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    updated_spec = ensure_examples(spec, routes)
    with open(OPENAPI_PATH, "w", encoding="utf-8") as f:
        yaml.dump(updated_spec, f, allow_unicode=True, sort_keys=False)
    print("OpenAPI examples ensured for all routes.")


if __name__ == "__main__":
    main()
