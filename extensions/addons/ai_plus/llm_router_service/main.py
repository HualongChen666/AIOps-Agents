# -*- coding: utf-8 -*-
"""Real LLM router add-on microservice.

Selects the best model for a request based on priority, cost and latency
constraints. ``/invoke`` forwards to the selected model backend. If the
backend is unavailable, a 5xx error is returned instead of a fake response.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

SERVICE_NAME = "llm_router_service"
PORT = int(os.getenv("PORT", "8000"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)


MODELS: List[Dict[str, Any]] = [
    {
        "id": "gpt-4o",
        "provider": "openai",
        "max_tokens": 128000,
        "usd_per_1k_input": 0.005,
        "usd_per_1k_output": 0.015,
        "latency_ms": 400,
        "capabilities": ["chat", "code", "analysis"],
    },
    {
        "id": "gpt-4o-mini",
        "provider": "openai",
        "max_tokens": 128000,
        "usd_per_1k_input": 0.00015,
        "usd_per_1k_output": 0.0006,
        "latency_ms": 200,
        "capabilities": ["chat", "summarization"],
    },
    {
        "id": "claude-3-5-sonnet",
        "provider": "anthropic",
        "max_tokens": 200000,
        "usd_per_1k_input": 0.003,
        "usd_per_1k_output": 0.015,
        "latency_ms": 600,
        "capabilities": ["chat", "long_context", "analysis"],
    },
    {
        "id": "local-llama-3-8b",
        "provider": "local",
        "max_tokens": 8192,
        "usd_per_1k_input": 0.0,
        "usd_per_1k_output": 0.0,
        "latency_ms": 1200,
        "capabilities": ["chat"],
    },
]


class HealthResponse(BaseModel):
    status: str
    service: str
    models: int


class ModelsResponse(BaseModel):
    models: List[Dict[str, Any]]


class RouteRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    priority: str = Field(default="balanced", pattern="^(speed|cost|quality|balanced)$")
    max_cost_usd: Optional[float] = Field(default=None, ge=0)
    max_latency_ms: Optional[float] = Field(default=None, ge=0)
    required_capability: Optional[str] = Field(default=None)


class RouteResponse(BaseModel):
    selected_model: str
    provider: str
    estimated_cost_usd: float
    estimated_latency_ms: float


class InvokeRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=2)


class InvokeResponse(BaseModel):
    success: bool
    model: str
    provider: str
    response: str
    latency_ms: int


def _estimate_cost(model: Dict[str, Any], prompt: str) -> float:
    tokens = len(prompt.split())
    return tokens * (model["usd_per_1k_input"] / 1000) + tokens * (
        model["usd_per_1k_output"] / 2000
    )


def _select(req: RouteRequest) -> Dict[str, Any]:
    candidates = MODELS[:]
    if req.required_capability:
        candidates = [m for m in candidates if req.required_capability in m["capabilities"]]
    if req.max_cost_usd is not None:
        candidates = [m for m in candidates if _estimate_cost(m, req.prompt) <= req.max_cost_usd]
    if req.max_latency_ms is not None:
        candidates = [m for m in candidates if m["latency_ms"] <= req.max_latency_ms]
    if not candidates:
        raise HTTPException(status_code=400, detail="No model satisfies the constraints")
    if req.priority == "speed":
        return min(candidates, key=lambda m: m["latency_ms"])
    if req.priority == "cost":
        return min(candidates, key=lambda m: _estimate_cost(m, req.prompt))
    if req.priority == "quality":
        return max(candidates, key=lambda m: m["max_tokens"])
    # balanced: minimize latency * cost product
    return min(candidates, key=lambda m: m["latency_ms"] * _estimate_cost(m, req.prompt))


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, models=len(MODELS))


@app.get("/models", response_model=ModelsResponse)
async def models() -> ModelsResponse:
    return ModelsResponse(models=MODELS)


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest) -> RouteResponse:
    """Pick the best model for a prompt and constraints."""
    selected = _select(req)
    return RouteResponse(
        selected_model=selected["id"],
        provider=selected["provider"],
        estimated_cost_usd=_estimate_cost(selected, req.prompt),
        estimated_latency_ms=selected["latency_ms"],
    )


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    """Call the selected model (or simulate)."""
    route = RouteRequest(prompt=req.prompt, priority="balanced")
    selected = (
        _select(route)
        if req.model is None
        else next((m for m in MODELS if m["id"] == req.model), None)
    )
    if not selected:
        raise HTTPException(status_code=404, detail="Unknown model")

    start = time.monotonic()

    if selected["provider"] == "openai" and OPENAI_API_KEY:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{OPENAI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": selected["id"],
                        "messages": [{"role": "user", "content": req.prompt}],
                        "temperature": req.temperature,
                    },
                )
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("OpenAI call failed: %s", e)
            raise HTTPException(status_code=502, detail=f"OpenAI backend error: {e}") from e
    elif selected["provider"] == "local":
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": selected["id"].replace("local-", ""),
                        "prompt": req.prompt,
                        "stream": False,
                    },
                    timeout=60.0,
                )
                r.raise_for_status()
                data = r.json()
                text = data.get("response", "")
        except Exception as e:
            logger.error("Local LLM backend failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Local LLM backend error: {e}") from e
    else:
        raise HTTPException(
            status_code=503, detail=f"No backend available for provider {selected['provider']}"
        )

    latency_ms = int((time.monotonic() - start) * 1000) or selected["latency_ms"]
    return InvokeResponse(
        success=True,
        model=selected["id"],
        provider=selected["provider"],
        response=text,
        latency_ms=latency_ms,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=PORT)
