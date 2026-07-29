# -*- coding: utf-8 -*-
"""Enhance FastAPI routes with description, codeSamples and error responses.

This module provides a single helper, ``enhance_app_routes``, that patches the
OpenAPI schema generation of a FastAPI application. After the normal schema is
built, every operation is enriched to ensure it exposes:

* a non-empty ``description``
* a ``responses`` mapping with standard error schemas
* an ``x-codeSamples`` entry with curl/Python examples
* a ``200`` response example when JSON content is returned

It is called once in ``main.py`` after all routers have been included, so the
change is applied globally without editing each router file.
"""

from typing import Any

from fastapi import FastAPI

# Common HTTP error descriptions used in every API endpoint
DEFAULT_ERROR_RESPONSES: dict[str, dict[str, Any]] = {
    "400": {"description": "Bad request"},
    "401": {"description": "Unauthorized"},
    "403": {"description": "Forbidden"},
    "404": {"description": "Not found"},
    "500": {"description": "Internal server error"},
}


def _build_code_samples(method: str, path: str) -> list[dict[str, str]]:
    """Generate curl and Python requests code samples for a route."""
    method = method.upper() if method else "GET"
    url = f"http://localhost:8000{path}"
    curl = f"curl -X {method} {url} -H 'Content-Type: application/json'"
    if method in ("POST", "PUT", "PATCH"):
        curl += " -d '{}'"
        python = (
            f"import requests\n"
            f'resp = requests.{method.lower()}("{url}", json={{}})\n'
            f"print(resp.json())"
        )
    else:
        python = (
            f"import requests\n"
            f'resp = requests.{method.lower()}("{url}")\n'
            f"print(resp.json())"
        )
    return [
        {"lang": "Shell", "label": "curl", "source": curl},
        {"lang": "Python", "label": "requests", "source": python},
    ]


def _enrich_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Post-process an OpenAPI schema and fill missing documentation fields."""
    paths = schema.get("paths") or {}
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.lower() in ("parameters", "servers"):
                continue
            if not isinstance(operation, dict):
                continue

            # description
            if not operation.get("description"):
                operation["description"] = operation.get("summary") or f"{method.upper()} {path}"

            # codeSamples
            if "x-codeSamples" not in operation:
                operation["x-codeSamples"] = _build_code_samples(method, path)

            # error responses
            responses = operation.setdefault("responses", {})
            for code, info in DEFAULT_ERROR_RESPONSES.items():
                if code not in responses:
                    responses[code] = {"description": info["description"]}

            # success response examples (200/201/202; 204 is intentionally no-content)
            for code in ("200", "201", "202"):
                ok_resp = responses.get(code)
                if isinstance(ok_resp, dict):
                    content = ok_resp.setdefault("content", {})
                    if "application/json" not in content:
                        content["application/json"] = {"schema": {"type": "object"}}
                    content["application/json"].setdefault("example", {})

    return schema


def enhance_app_routes(app: FastAPI) -> None:
    """Patch ``app.openapi`` so generated OpenAPI schema is fully documented.

    Args:
        app: The FastAPI application to enhance in-place.
    """
    original_openapi = app.openapi

    def custom_openapi() -> dict[str, Any]:
        schema = original_openapi()
        return _enrich_openapi_schema(schema)

    app.openapi = custom_openapi  # type: ignore[method-assign]
