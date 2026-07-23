# -*- coding: utf-8 -*-
import textwrap

import yaml

OPENAPI_PATH = r"C:\\AIOps_Agent_bak\\openapi.yaml"


def load_openapi():
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_openapi(data):
    # Preserve order, dump with default_flow_style=False
    with open(OPENAPI_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def generate_description(summary, operation_id):
    # Simple heuristic: use summary and operationId
    if not summary:
        summary = operation_id.replace("_", " ").title()
    desc = f"{summary}. This endpoint is identified by operationId '{operation_id}'."
    return desc


def generate_param_desc(name):
    return f"Parameter `{name}` description."


def generate_code_sample(path, method, operation_id):
    # Build a simple python requests example
    f"{{BASE_URL}}{path}"
    sample = textwrap.dedent(f"""
        import requests

        BASE_URL = 'https://aiops.aiops.example.com/api/v1'
        response = requests.{method.lower()}(BASE_URL + '{path}')
        print('Status:', response.status_code)
        print('Response:', response.json())
    """)
    return {"lang": "python", "source": sample.strip()}


def enhance():
    data = load_openapi()
    total = 0
    enhanced = 0
    for path, methods in data.get("paths", {}).items():
        for method, details in methods.items():
            total += 1
            changed = False
            # Ensure summary exists
            if "summary" not in details:
                details["summary"] = f"{method.upper()} {path}"
                changed = True
            # Ensure description exists
            if "description" not in details:
                details["description"] = generate_description(
                    details.get("summary"), details.get("operationId", "")
                )
                changed = True
            # Ensure parameters have description
            params = details.get("parameters", [])
            for p in params:
                if "description" not in p:
                    p["description"] = generate_param_desc(p.get("name", "param"))
                    changed = True
            # Add usage example via extension
            if "x-codeSamples" not in details:
                details["x-codeSamples"] = [
                    generate_code_sample(path, method, details.get("operationId", ""))
                ]
                changed = True
            if changed:
                enhanced += 1
    save_openapi(data)
    print(f"Enhanced {enhanced}/{total} endpoint definitions.")


if __name__ == "__main__":
    enhance()
