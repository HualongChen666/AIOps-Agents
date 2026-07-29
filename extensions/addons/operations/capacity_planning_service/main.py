# -*- coding: utf-8 -*-
"""capacity_planning_service add-on microservice."""

import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel, Field

SERVICE_NAME = "capacity_planning_service"
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME


class InfoResponse(BaseModel):
    service: str
    version: str
    status: str


class InvokeRequest(BaseModel):
    action: str = Field(..., description="Operation to invoke")
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check."""
    return HealthResponse(service=SERVICE_NAME)


@app.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    """Service metadata."""
    return InfoResponse(service=SERVICE_NAME, version="1.0.0", status="running")


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    """Execute a domain-specific action."""
    logger.info(
        "[%s] invoke action=%s payload_keys=%s", SERVICE_NAME, req.action, list(req.payload.keys())
    )
    return InvokeResponse(
        success=True,
        service=SERVICE_NAME,
        action=req.action,
        result={"received": True, "payload": req.payload},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
