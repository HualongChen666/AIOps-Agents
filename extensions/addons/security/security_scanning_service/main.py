# -*- coding: utf-8 -*-
"""Real business logic for the security_scanning_service add-on microservice."""

import logging
import os
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

SERVICE_NAME = "security_scanning_service"
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)


class Vulnerability(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    target: str
    severity: str
    cve: str
    status: str


class InvokeRequest(BaseModel):
    action: str = Field(
        ..., pattern="^(create|list|get|update|delete|query|run|evaluate|export|import)$"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME
    vulnerability_count: int


class InfoResponse(BaseModel):
    service: str
    version: str = "1.0.0"
    status: str = "running"


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


store: Dict[str, Vulnerability] = {}


def _create(payload: Dict[str, Any]) -> Dict[str, Any]:
    item = Vulnerability(**payload)
    store[item.id] = item
    logger.info("[%s] created %s id=%s", SERVICE_NAME, "vulnerability", item.id)
    return item.model_dump()


def _list(_: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item.model_dump() for item in store.values()]


def _get(payload: Dict[str, Any]) -> Dict[str, Any]:
    item_id = payload.get("id")
    if not item_id or item_id not in store:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    return store[item_id].model_dump()


def _update(payload: Dict[str, Any]) -> Dict[str, Any]:
    item_id = payload.pop("id", None)
    if not item_id or item_id not in store:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    existing = store[item_id].model_dump()
    existing.update(payload)
    updated = Vulnerability(**existing)
    store[item_id] = updated
    logger.info("[%s] updated %s id=%s", SERVICE_NAME, "vulnerability", item_id)
    return updated.model_dump()


def _delete(payload: Dict[str, Any]) -> Dict[str, Any]:
    item_id = payload.get("id")
    if not item_id or item_id not in store:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    del store[item_id]
    logger.info("[%s] deleted %s id=%s", SERVICE_NAME, "vulnerability", item_id)
    return {"deleted": item_id}


def _query(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    for item in store.values():
        d = item.model_dump()
        if all(d.get(k) == v for k, v in payload.items() if k != "id"):
            results.append(d)
    return results


def _scan_content(content: str) -> List[Dict[str, Any]]:
    """Scan text for hardcoded secrets and suspicious patterns."""
    patterns = {
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "private_key": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "api_token": r"[Tt]oken\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
        "password": r"[Pp]assword\s*[:=]\s*['\"][^'\"]{6,}['\"]",
    }
    findings: List[Dict[str, Any]] = []
    for label, pattern in patterns.items():
        for match in re.finditer(pattern, content):
            findings.append(
                {
                    "type": label,
                    "position": match.start(),
                    "matched": content[match.start() : min(match.end() + 6, len(content))],
                }
            )
    return findings


def _run(payload: Dict[str, Any]) -> Dict[str, Any]:
    content = payload.get("content") or payload.get("target")
    if isinstance(content, str):
        findings = _scan_content(content)
        logger.info("[%s] scanned %s characters, %s findings", SERVICE_NAME, len(content), len(findings))
        return {"status": "scanned", "findings": findings, "service": SERVICE_NAME}

    item_id = payload.get("id")
    if item_id and item_id in store:
        logger.info("[%s] ran %s id=%s", SERVICE_NAME, "vulnerability", item_id)
        return {"status": "executed", "id": item_id, "service": SERVICE_NAME}
    return {"status": "noop", "service": SERVICE_NAME, "matched": len(store)}


def _evaluate(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"total": len(store), "service": SERVICE_NAME, "action": "evaluate"}


def _export(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"items": [item.model_dump() for item in store.values()], "service": SERVICE_NAME}


def _import(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = payload.get("items", [])
    imported = 0
    for item_data in items:
        item = Vulnerability(**item_data)
        store[item.id] = item
        imported += 1
    logger.info("[%s] imported %s %s items", SERVICE_NAME, imported, "vulnerability")
    return {"imported": imported}


HANDLERS = {
    "create": _create,
    "list": _list,
    "get": _get,
    "update": _update,
    "delete": _delete,
    "query": _query,
    "run": _run,
    "evaluate": _evaluate,
    "export": _export,
    "import": _import,
}


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, vulnerability_count=len(store))


@app.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    return InfoResponse(service=SERVICE_NAME)


@app.get("/vulnerabilities", response_model=List[Dict[str, Any]])
async def list_vulnerabilities():
    return _list({})


@app.get("/vulnerabilities/{item_id}", response_model=Dict[str, Any])
async def get_vulnerability(item_id: str):
    return _get({"id": item_id})


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    handler = HANDLERS.get(req.action)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
    result = handler(req.payload)
    return InvokeResponse(success=True, service=SERVICE_NAME, action=req.action, result=result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
