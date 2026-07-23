# -*- coding: utf-8 -*-
"""Script to extract response examples from FastAPI router definitions
and inject them into the project's OpenAPI specification (openapi.yaml).

Assumptions:
- Each router file uses the @router.<method>(...) decorator from FastAPI.
- The decorator includes a `responses` argument where the 200 response
  contains an `example` under `content['application/json']`.
- The path argument is a literal string.

The script parses all .py files under the `api/` directory, collects the
examples, loads `openapi.yaml`, updates/creates the example entries for
the corresponding path+method, and writes the file back.
"""

import ast
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "api"
OPENAPI_PATH = PROJECT_ROOT / "openapi.yaml"


def extract_examples_from_file(file_path: Path):
    """Parse a router file and return a list of (path, method, example) tuples."""
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=str(file_path))
    examples = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # Look for router.<method>( ... )
            if getattr(node.func.value, "id", None) == "router":
                method = node.func.attr.upper()  # get, post, put, delete, etc.
                # Extract the first positional argument as path
                if not node.args:
                    continue
                path_node = node.args[0]
                if isinstance(path_node, ast.Constant):
                    path = path_node.value
                else:
                    continue  # non‑literal path, skip
                # Find 'responses' keyword
                responses_kw = None
                for kw in node.keywords:
                    if kw.arg == "responses":
                        responses_kw = kw.value
                        break
                if responses_kw is None:
                    continue
                # responses should be a dict literal
                if isinstance(responses_kw, ast.Dict):
                    # Look for key '200'
                    for k, v in zip(responses_kw.keys, responses_kw.values):
                        if isinstance(k, ast.Constant) and k.value == 200:
                            # v should be a dict with 'content' -> 'application/json' -> 'example'
                            if isinstance(v, ast.Dict):
                                # Find 'content'
                                content_val = None
                                for ck, cv in zip(v.keys, v.values):
                                    if isinstance(ck, ast.Constant) and ck.value == "content":
                                        content_val = cv
                                        break
                                if content_val and isinstance(content_val, ast.Dict):
                                    # Find 'application/json'
                                    appjson_val = None
                                    for ajk, ajv in zip(content_val.keys, content_val.values):
                                        if (
                                            isinstance(ajk, ast.Constant)
                                            and ajk.value == "application/json"
                                        ):
                                            appjson_val = ajv
                                            break
                                    if appjson_val and isinstance(appjson_val, ast.Dict):
                                        # Find 'example'
                                        example_val = None
                                        for ek, ev in zip(appjson_val.keys, appjson_val.values):
                                            if (
                                                isinstance(ek, ast.Constant)
                                                and ek.value == "example"
                                            ):
                                                example_val = ev
                                                break
                                        if example_val:
                                            # Convert AST literal to Python object
                                            example = ast.literal_eval(example_val)
                                            examples.append((path, method, example))
    return examples


def collect_all_examples():
    all_examples = {}
    for py_file in API_DIR.rglob("*.py"):
        exs = extract_examples_from_file(py_file)
        for path, method, example in exs:
            all_examples.setdefault(path, {})[method] = example
    return all_examples


def update_openapi_yaml(examples_dict):
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    if "paths" not in spec:
        spec["paths"] = {}
    for path, methods in examples_dict.items():
        # Ensure the path exists in spec (FastAPI may have generated it elsewhere)
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        for method, example in methods.items():
            method_key = method.lower()
            if method_key not in spec["paths"][path]:
                spec["paths"][path][method_key] = {}
            spec["paths"][path][method_key].setdefault("responses", {})
            spec["paths"][path][method_key]["responses"].setdefault("200", {})
            spec["paths"][path][method_key]["responses"]["200"].setdefault("content", {})
            spec["paths"][path][method_key]["responses"]["200"]["content"].setdefault(
                "application/json", {}
            )
            spec["paths"][path][method_key]["responses"]["200"]["content"]["application/json"][
                "example"
            ] = example
    # Write back
    with open(OPENAPI_PATH, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, allow_unicode=True, sort_keys=False)
    print(f"Updated {OPENAPI_PATH} with {len(examples_dict)} paths.")


if __name__ == "__main__":
    examples = collect_all_examples()
    update_openapi_yaml(examples)
