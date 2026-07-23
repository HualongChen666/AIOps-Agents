# -*- coding: utf-8 -*-
import os
import textwrap

import yaml

BASE_URL = "http://localhost:8080/api/v1"

OPENAPI_PATH = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")
EXAMPLE_ROOT = os.path.join(os.path.dirname(__file__), "..", "examples")
PY_DIR = os.path.join(EXAMPLE_ROOT, "python")
CURL_DIR = os.path.join(EXAMPLE_ROOT, "curl")
JS_DIR = os.path.join(EXAMPLE_ROOT, "js")

os.makedirs(PY_DIR, exist_ok=True)
os.makedirs(CURL_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)

with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
    spec = yaml.safe_load(f)

paths = list(spec.get("paths", {}).items())
# Select core APIs: prioritize tags with high usage (first 50 paths)
selected = paths[:50]

for path, methods in selected:
    for method, detail in methods.items():
        operation_id = detail.get("operationId", f"{method}_{path.replace('/', '_')}")
        # Build Python example
        python_code = textwrap.dedent(f"""
        import requests

        # 示例：{detail.get('summary', '')}
        # 使用 {method.upper()} 方法请求 {path}
        url = f"{BASE_URL}{path}"
        try:
            response = requests.{method}(url)
            print('Status:', response.status_code)
            print('Response:', response.json())
        except Exception as e:
            print('Request failed:', e)
        """)
        py_path = os.path.join(PY_DIR, f"{operation_id}.py")
        with open(py_path, "w", encoding="utf-8") as pf:
            pf.write(python_code.strip() + "\n")

        # Build curl example
        curl_code = f"curl -X {method.upper()} {BASE_URL}{path}"
        curl_path = os.path.join(CURL_DIR, f"{operation_id}.sh")
        with open(curl_path, "w", encoding="utf-8") as cf:
            cf.write(f"# 示例：{detail.get('summary', '')}\n{curl_code}\n")

        # Build JavaScript example (fetch)
        js_code = textwrap.dedent(f"""
        // 示例：{detail.get('summary', '')}
        fetch('{BASE_URL}{path}', {{
            method: '{method.upper()}'
        }})
        .then(res => res.json())
        .then(data => console.log(data))
        .catch(err => console.error('Request error:', err));
        """)
        js_path = os.path.join(JS_DIR, f"{operation_id}.js")
        with open(js_path, "w", encoding="utf-8") as jf:
            jf.write(js_code.strip() + "\n")
print("Generated examples for", len(selected), "endpoints.")
