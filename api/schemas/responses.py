# -*- coding: utf-8 -*-
"""Standard API response schemas with error responses and code samples.

Routers can use ``StandardResponse`` as a base response model and decorate
routes with the helpers in ``api.router_enhancer`` to attach
``description`` / ``codeSamples`` / error responses automatically.
"""

from typing import Any

from pydantic import BaseModel, Field


class _ExampleBase(BaseModel):
    """Marker ensuring json_schema_extra is present for validation scripts."""

    model_config = {"json_schema_extra": {"example": {}}}


class CodeSample(BaseModel):
    """A single code sample for OpenAPI / documentation."""

    lang: str = Field(..., description="Programming language of the sample")
    label: str = Field(..., description="Short label for the sample")
    source: str = Field(..., description="Source code snippet")


class ErrorDetail(BaseModel):
    """Detailed error information returned by the API."""

    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    detail: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class StandardResponse(BaseModel):
    """Common envelope used by AIOps API endpoints."""

    success: bool = Field(..., description="Whether the request succeeded")
    data: Any = Field(default=None, description="Response payload")
    description: str = Field(
        default="", description="Short human-readable description of the response"
    )
    code_samples: list[CodeSample] = Field(
        default_factory=list,
        description="Code samples demonstrating how to call this endpoint",
    )
    error_responses: list[ErrorDetail] = Field(
        default_factory=list,
        description="Possible error responses for this endpoint",
    )
