# -*- coding: utf-8 -*-
"""Tenant REST API router."""

from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.tenant_engine import (
    create_tenant,
    delete_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
)

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(default="basic", pattern="^(free|basic|pro|enterprise)$")
    status: str = Field(default="active", pattern="^(active|suspended|expired)$")
    contact: str = Field(default="", max_length=200)

    model_config = {"extra": "ignore"}


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan: Optional[str] = Field(None, pattern="^(free|basic|pro|enterprise)$")
    status: Optional[str] = Field(None, pattern="^(active|suspended|expired)$")
    contact: Optional[str] = Field(None, max_length=200)
    quota: Optional[dict] = Field(None, description="Quota overrides")
    usage: Optional[dict] = Field(None, description="Usage overrides")

    model_config = {"extra": "ignore"}


class TenantResponse(BaseModel):
    id: str
    name: str
    status: str
    contact: str
    plan: str
    quota: dict
    usage: dict
    billing: dict
    created_at: str

    model_config = {"extra": "ignore"}


@router.get("/", response_model=List[TenantResponse])
async def get_all_tenants() -> List[TenantResponse]:
    return [TenantResponse(**asdict(t)) for t in list_tenants()]


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_new_tenant(payload: TenantCreate) -> TenantResponse:
    tenant = create_tenant(
        name=payload.name,
        plan=payload.plan,
        status=payload.status,
        contact=payload.contact,
    )
    return TenantResponse(**asdict(tenant))


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_one_tenant(tenant_id: str) -> TenantResponse:
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse(**asdict(tenant))


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_existing_tenant(tenant_id: str, payload: TenantUpdate) -> TenantResponse:
    updates = payload.model_dump(exclude_unset=True)
    tenant = update_tenant(tenant_id, **updates)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse(**asdict(tenant))


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_tenant(tenant_id: str) -> None:
    if not delete_tenant(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return None
