# -*- coding: utf-8 -*-
import textwrap

import yaml

OPENAPI_PATH = r"C:\\AIOps_Agent_bak\\openapi.yaml"


def load():
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save(data):
    with open(OPENAPI_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def gen_desc(summary, operation_id):
    if not summary:
        summary = operation_id.replace("_", " ").title()
    return f"{summary}. This endpoint is identified by operationId '{operation_id}'."


def param_desc(name):
    return f"Parameter `{name}` description."


def python_sample(path, method):
    return {
        "lang": "python",
        "source": textwrap.dedent(f"""
            import requests

            BASE_URL = 'https://aiops.aiops.example.com/api/v1'
            response = requests.{method.lower()}(BASE_URL + '{path}')
            print('Status:', response.status_code)
            print('Response:', response.json())
        """).strip(),
    }


def curl_sample(path, method):
    return {
        "lang": "curl",
        "source": f"curl -X {method.upper()} https://aiops.aiops.example.com/api/v1{path}",
    }


def js_sample(path, method):
    return {
        "lang": "javascript",
        "source": textwrap.dedent(f"""
            fetch('https://aiops.aiops.example.com/api/v1{path}', {{
                method: '{method.upper()}'
            }})
            .then(res => res.json())
            .then(data => console.log(data))
            .catch(err => console.error(err));
        """).strip(),
    }


def enhance():
    data = load()
    total = 0
    enhanced = 0
    for path, methods in data.get("paths", {}).items():
        for method, details in methods.items():
            total += 1
            changed = False
            # summary
            if "summary" not in details:
                details["summary"] = f"{method.upper()} {path}"
                changed = True
            # description
            if "description" not in details:
                details["description"] = gen_desc(
                    details.get("summary"), details.get("operationId", "")
                )
                changed = True
            # parameters description
            for p in details.get("parameters", []):
                if "description" not in p:
                    p["description"] = param_desc(p.get("name", "param"))
                    changed = True
            # x-codeSamples (list of samples)
            samples = details.get("x-codeSamples", [])
            # ensure we have python, curl, js
            langs = {s["lang"] for s in samples}
            if "python" not in langs:
                samples.append(python_sample(path, method))
                changed = True
            if "curl" not in langs:
                samples.append(curl_sample(path, method))
                changed = True
            if "javascript" not in langs:
                samples.append(js_sample(path, method))
                changed = True
            if changed:
                details["x-codeSamples"] = samples
                enhanced += 1
            # add notes placeholder if missing
            if "x-notes" not in details:
                details["x-notes"] = "注意事项: 暂无特殊限制。"
                enhanced += 1
    save(data)
    print(f"Enhanced {enhanced}/{total} endpoints with descriptions, samples, notes.")


if __name__ == "__main__":
    enhance()
