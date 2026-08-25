# -*- coding: utf-8 -*-
"""Unit tests for router_enhancer.py to achieve 90%+ coverage without app initialization."""

import os

# Direct import to avoid app initialization
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

api_dir = os.path.join(os.path.dirname(__file__), "..", "..", "api")
sys.path.insert(0, api_dir)

# Import the module directly
import importlib.util

spec = importlib.util.spec_from_file_location(
    "router_enhancer", os.path.join(api_dir, "router_enhancer.py")
)
router_enhancer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router_enhancer)


class TestBuildCodeSamples:
    """Test the _build_code_samples helper function."""

    def test_build_code_samples_get(self):
        """Test code samples for GET method."""
        samples = router_enhancer._build_code_samples("GET", "/api/test")
        assert len(samples) == 2
        assert samples[0]["lang"] == "Shell"
        assert samples[0]["label"] == "curl"
        assert "curl -X GET" in samples[0]["source"]
        assert samples[1]["lang"] == "Python"
        assert samples[1]["label"] == "requests"
        assert "requests.get" in samples[1]["source"]

    def test_build_code_samples_post(self):
        """Test code samples for POST method."""
        samples = router_enhancer._build_code_samples("POST", "/api/test")
        assert len(samples) == 2
        assert "curl -X POST" in samples[0]["source"]
        assert "-d '{}'" in samples[0]["source"]
        assert "requests.post" in samples[1]["source"]
        assert "json={}" in samples[1]["source"]

    def test_build_code_samples_put(self):
        """Test code samples for PUT method."""
        samples = router_enhancer._build_code_samples("PUT", "/api/test")
        assert "curl -X PUT" in samples[0]["source"]
        assert "-d '{}'" in samples[0]["source"]
        assert "requests.put" in samples[1]["source"]

    def test_build_code_samples_patch(self):
        """Test code samples for PATCH method."""
        samples = router_enhancer._build_code_samples("PATCH", "/api/test")
        assert "curl -X PATCH" in samples[0]["source"]
        assert "-d '{}'" in samples[0]["source"]
        assert "requests.patch" in samples[1]["source"]

    def test_build_code_samples_delete(self):
        """Test code samples for DELETE method."""
        samples = router_enhancer._build_code_samples("DELETE", "/api/test")
        assert "curl -X DELETE" in samples[0]["source"]
        assert "-d '{}'" not in samples[0]["source"]
        assert "requests.delete" in samples[1]["source"]

    def test_build_code_samples_none_method(self):
        """Test code samples when method is None (line 33)."""
        samples = router_enhancer._build_code_samples(None, "/api/test")
        assert "curl -X GET" in samples[0]["source"]

    def test_build_code_samples_empty_method(self):
        """Test code samples when method is empty string."""
        samples = router_enhancer._build_code_samples("", "/api/test")
        assert "curl -X GET" in samples[0]["source"]

    def test_build_code_samples_lowercase_method(self):
        """Test that method is uppercased (line 33)."""
        samples = router_enhancer._build_code_samples("get", "/api/test")
        assert "curl -X GET" in samples[0]["source"]

    def test_build_code_samples_path_with_special_chars(self):
        """Test code samples with path containing special characters."""
        samples = router_enhancer._build_code_samples("GET", "/api/test/{id}")
        assert "/api/test/{id}" in samples[0]["source"]
        assert "/api/test/{id}" in samples[1]["source"]


class TestEnrichOpenapiSchema:
    """Test the _enrich_openapi_schema function."""

    def test_enrich_schema_empty_paths(self):
        """Test enrichment with empty paths dict (line 57)."""
        schema = {"paths": {}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched == schema

    def test_enrich_schema_no_paths_key(self):
        """Test enrichment when paths key is missing (line 57)."""
        schema = {}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched == schema

    def test_enrich_schema_none_paths(self):
        """Test enrichment when paths is None (line 57)."""
        schema = {"paths": None}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched == schema

    def test_enrich_schema_add_description_from_summary(self):
        """Test adding description from summary (line 67)."""
        schema = {"paths": {"/api/test": {"get": {"summary": "Test endpoint"}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["get"]["description"] == "Test endpoint"

    def test_enrich_schema_add_description_from_method_path(self):
        """Test adding description from method and path (line 67)."""
        schema = {"paths": {"/api/test": {"get": {}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["get"]["description"] == "GET /api/test"

    def test_enrich_schema_skip_existing_description(self):
        """Test skipping when description already exists (line 66)."""
        schema = {"paths": {"/api/test": {"get": {"description": "Existing description"}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["get"]["description"] == "Existing description"

    def test_enrich_schema_add_code_samples(self):
        """Test adding code samples (line 71)."""
        schema = {"paths": {"/api/test": {"get": {}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert "x-codeSamples" in enriched["paths"]["/api/test"]["get"]
        assert len(enriched["paths"]["/api/test"]["get"]["x-codeSamples"]) == 2

    def test_enrich_schema_skip_existing_code_samples(self):
        """Test skipping when code samples already exist (line 70)."""
        schema = {
            "paths": {
                "/api/test": {"get": {"x-codeSamples": [{"lang": "Shell", "source": "existing"}]}}
            }
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert len(enriched["paths"]["/api/test"]["get"]["x-codeSamples"]) == 1

    def test_enrich_schema_add_error_responses(self):
        """Test adding default error responses (lines 74-77)."""
        schema = {"paths": {"/api/test": {"get": {"responses": {}}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        responses = enriched["paths"]["/api/test"]["get"]["responses"]
        for code in router_enhancer.DEFAULT_ERROR_RESPONSES:
            assert code in responses
            assert (
                responses[code]["description"]
                == router_enhancer.DEFAULT_ERROR_RESPONSES[code]["description"]
            )

    def test_enrich_schema_skip_existing_error_responses(self):
        """Test skipping when error responses already exist (line 76)."""
        schema = {
            "paths": {"/api/test": {"get": {"responses": {"400": {"description": "Custom error"}}}}}
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert (
            enriched["paths"]["/api/test"]["get"]["responses"]["400"]["description"]
            == "Custom error"
        )

    def test_enrich_schema_add_200_response_example(self):
        """Test adding 200 response example (lines 80-86)."""
        schema = {
            "paths": {
                "/api/test": {
                    "get": {
                        "responses": {
                            "200": {"content": {"application/json": {"schema": {"type": "object"}}}}
                        }
                    }
                }
            }
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert (
            "example"
            in enriched["paths"]["/api/test"]["get"]["responses"]["200"]["content"][
                "application/json"
            ]
        )

    def test_enrich_schema_add_201_response_example(self):
        """Test adding 201 response example."""
        schema = {
            "paths": {
                "/api/test": {
                    "post": {
                        "responses": {
                            "201": {"content": {"application/json": {"schema": {"type": "object"}}}}
                        }
                    }
                }
            }
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert (
            "example"
            in enriched["paths"]["/api/test"]["post"]["responses"]["201"]["content"][
                "application/json"
            ]
        )

    def test_enrich_schema_add_202_response_example(self):
        """Test adding 202 response example."""
        schema = {
            "paths": {
                "/api/test": {
                    "post": {
                        "responses": {
                            "202": {"content": {"application/json": {"schema": {"type": "object"}}}}
                        }
                    }
                }
            }
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert (
            "example"
            in enriched["paths"]["/api/test"]["post"]["responses"]["202"]["content"][
                "application/json"
            ]
        )

    def test_enrich_schema_skip_204_response(self):
        """Test that 204 is intentionally skipped (line 79)."""
        schema = {
            "paths": {
                "/api/test": {
                    "delete": {
                        "responses": {
                            "204": {"content": {"application/json": {"schema": {"type": "object"}}}}
                        }
                    }
                }
            }
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        # 204 should not get an example added
        assert "example" not in enriched["paths"]["/api/test"]["delete"]["responses"]["204"].get(
            "content", {}
        ).get("application/json", {})

    def test_enrich_schema_skip_non_dict_operation(self):
        """Test skipping non-dict operations (line 62)."""
        schema = {"paths": {"/api/test": {"get": "not a dict"}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["get"] == "not a dict"

    def test_enrich_schema_skip_parameters_method(self):
        """Test skipping 'parameters' method (line 60)."""
        schema = {"paths": {"/api/test": {"parameters": {}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["parameters"] == {}

    def test_enrich_schema_skip_servers_method(self):
        """Test skipping 'servers' method (line 60)."""
        schema = {"paths": {"/api/test": {"servers": []}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["servers"] == []

    def test_enrich_schema_case_insensitive_method_skip(self):
        """Test that method skip is case-insensitive (line 60)."""
        schema = {"paths": {"/api/test": {"PARAMETERS": {}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["PARAMETERS"] == {}

    def test_enrich_schema_add_content_when_missing(self):
        """Test adding content when missing (line 83-85)."""
        schema = {"paths": {"/api/test": {"get": {"responses": {"200": {}}}}}}
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert "content" in enriched["paths"]["/api/test"]["get"]["responses"]["200"]
        assert (
            "application/json"
            in enriched["paths"]["/api/test"]["get"]["responses"]["200"]["content"]
        )

    def test_enrich_schema_preserve_existing_example(self):
        """Test preserving existing example (line 86)."""
        schema = {
            "paths": {
                "/api/test": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"type": "object"},
                                        "example": {"existing": "data"},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        enriched = router_enhancer._enrich_openapi_schema(schema)
        assert enriched["paths"]["/api/test"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["example"] == {"existing": "data"}


class TestEnhanceAppRoutes:
    """Test the enhance_app_routes function."""

    def test_enhance_app_routes_patches_openapi(self):
        """Test that enhance_app_routes patches app.openapi (lines 97-103)."""
        app = FastAPI()
        original_openapi = app.openapi

        router_enhancer.enhance_app_routes(app)

        # Verify openapi was patched
        assert app.openapi != original_openapi

    def test_enhance_app_routes_calls_enrich_schema(self):
        """Test that patched openapi calls _enrich_openapi_schema."""
        app = FastAPI()
        app.openapi = lambda: {"paths": {}, "info": {"title": "Test"}}

        with patch.object(router_enhancer, "_enrich_openapi_schema") as mock_enrich:
            mock_enrich.return_value = {"enriched": True}
            router_enhancer.enhance_app_routes(app)
            result = app.openapi()
            mock_enrich.assert_called_once()

    def test_enhance_app_routes_preserves_original_behavior(self):
        """Test that enhancement preserves original OpenAPI generation."""
        app = FastAPI(title="Test App")
        router_enhancer.enhance_app_routes(app)

        schema = app.openapi()
        assert "paths" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Test App"

    def test_enhance_app_routes_multiple_enhancements(self):
        """Test that calling enhance_app_routes multiple times works."""
        app = FastAPI()
        router_enhancer.enhance_app_routes(app)
        router_enhancer.enhance_app_routes(app)

        schema = app.openapi()
        assert "paths" in schema


class TestDefaultErrorResponses:
    """Test DEFAULT_ERROR_RESPONSES constant."""

    def test_default_error_responses_structure(self):
        """Test that DEFAULT_ERROR_RESPONSES has correct structure."""
        assert isinstance(router_enhancer.DEFAULT_ERROR_RESPONSES, dict)
        assert "400" in router_enhancer.DEFAULT_ERROR_RESPONSES
        assert "401" in router_enhancer.DEFAULT_ERROR_RESPONSES
        assert "403" in router_enhancer.DEFAULT_ERROR_RESPONSES
        assert "404" in router_enhancer.DEFAULT_ERROR_RESPONSES
        assert "500" in router_enhancer.DEFAULT_ERROR_RESPONSES

    def test_default_error_responses_content(self):
        """Test that each error response has description."""
        for code, info in router_enhancer.DEFAULT_ERROR_RESPONSES.items():
            assert isinstance(info, dict)
            assert "description" in info
            assert isinstance(info["description"], str)
