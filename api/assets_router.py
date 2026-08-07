# -*- coding: utf-8 -*-
"""Asset management API router."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth_db import Asset, get_session
from core.auth_service import get_current_user, has_role, require_roles

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


class _AssetOut(BaseModel):
    id: int
    name: str
    service: Optional[str] = None
    business_unit: Optional[str] = None
    env: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class _AssetCreate(BaseModel):
    name: str
    service: Optional[str] = None
    business_unit: Optional[str] = None
    env: Optional[str] = None
    owner: Optional[str] = None


class _AssetUpdate(BaseModel):
    name: Optional[str] = None
    service: Optional[str] = None
    business_unit: Optional[str] = None
    env: Optional[str] = None
    owner: Optional[str] = None


def _asset_out(asset: Asset) -> _AssetOut:
    return _AssetOut.model_validate(asset)


@router.get("/", response_model=List[_AssetOut])
def list_assets(
    db: Session = Depends(get_session),
    current_user = Depends(require_roles("admin", "operator", "business")),
):
    return [_asset_out(a) for a in db.query(Asset).all()]


@router.post("/", response_model=_AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    req: _AssetCreate,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles("admin", "operator")),
):
    asset = Asset(
        name=req.name,
        service=req.service,
        business_unit=req.business_unit,
        env=req.env,
        owner=req.owner,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _asset_out(asset)


@router.get("/{id}", response_model=_AssetOut)
def get_asset(
    id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles("admin", "operator", "business")),
):
    asset = db.query(Asset).filter(Asset.id == id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return _asset_out(asset)


@router.put("/{id}", response_model=_AssetOut)
def update_asset(
    id: int,
    req: _AssetUpdate,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles("admin", "operator")),
):
    asset = db.query(Asset).filter(Asset.id == id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return _asset_out(asset)


@router.delete("/{id}")
def delete_asset(
    id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles("admin")),
):
    asset = db.query(Asset).filter(Asset.id == id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    db.delete(asset)
    db.commit()
    return {"detail": "Asset deleted"}
