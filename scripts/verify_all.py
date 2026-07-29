# -*- coding: utf-8 -*-
import json
import pathlib

import yaml


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main():
    openapi_path = pathlib.Path(r"C:\AIOps_Agent_bak\openapi.yaml")
    openapi = load_yaml(openapi_path)
    paths = openapi.get("paths", {})
    total_endpoints = sum(len(m) for m in paths.values())
    missing_example = []
    missing_desc = []
    missing_code = []
    missing_error = []
    for p, methods in paths.items():
        for method, details in methods.items():
            resp = details.get("responses", {})
            success = None
            success_code = None
            for code in ("200", "201", "202", "204"):
                if code in resp:
                    success = resp[code]
                    success_code = code
                    break
            # 204 No Content responses are allowed to have no content
            if success and success_code == "204" and not success.get("content"):
                continue
            if not (
                success
                and success.get("content")
                and success["content"].get("application/json")
                and "example" in success["content"]["application/json"]
            ):
                missing_example.append((p, method))
            if not details.get("description"):
                missing_desc.append((p, method))
            if "x-codeSamples" not in details:
                missing_code.append((p, method))
            for code in ["400", "401", "403", "404", "500"]:
                if code not in resp:
                    missing_error.append((p, method, code))
    # Pydantic model examples check
    from pathlib import Path

    models_dir = Path(r"C:\AIOps_Agent_bak\api")
    model_files = list(models_dir.rglob("*.py"))
    missing_model_examples = []
    for file in model_files:
        text = file.read_text(encoding="utf-8")
        if "class" in text and "BaseModel" in text:
            # Pydantic v2 uses model_config + json_schema_extra; v1 uses class Config + schema_extra
            has_example_config = ("model_config" in text and "json_schema_extra" in text) or (
                "class Config" in text and "schema_extra" in text
            )
            if not has_example_config:
                missing_model_examples.append(str(file))
    # Example files check
    examples_dir = Path(r"C:\AIOps_Agent_bak\examples")
    python_examples = list((examples_dir / "python").rglob("*.py"))
    curl_examples = list((examples_dir / "curl").rglob("*.sh"))
    js_examples = list((examples_dir / "js").rglob("*.js"))
    # Output report
    report = {
        "total_endpoints": total_endpoints,
        "missing_200_examples": len(missing_example),
        "missing_descriptions": len(missing_desc),
        "missing_codeSamples": len(missing_code),
        "missing_error_responses": len(missing_error),
        "pydantic_missing_examples": len(missing_model_examples),
        "python_example_files": len(python_examples),
        "curl_example_files": len(curl_examples),
        "js_example_files": len(js_examples),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
