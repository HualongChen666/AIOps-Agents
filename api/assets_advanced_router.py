# -*- coding: utf-8 -*-
"""
Advanced Asset Management API Router
====================================

Provides comprehensive asset management endpoints including inventory,
relationships, lifecycle tracking, and dependency analysis.

Endpoints:
- GET/POST   /api/v1/assets/inventory
- GET/PATCH/DELETE /api/v1/assets/inventory/{id}
- GET        /api/v1/assets/relationships
- GET        /api/v1/assets/lifecycle
- GET        /api/v1/assets/dependencies
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth_db import Asset, get_session
from core.auth_service import require_roles
from core.database import get_db
from core.models import (
    AssetInventoryMetadata,
    AssetRelationshipDB,
    AssetLifecycleDB,
    AssetDependencyDB,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assets", tags=["assets-advanced"])


# ============================================================================
# Enums and Models
# ============================================================================


class AssetType(str, Enum):
    """Asset type enumeration."""

    SERVER = "server"
    DATABASE = "database"
    STORAGE = "storage"
    NETWORK = "network"
    APPLICATION = "application"
    SERVICE = "service"
    CONTAINER = "container"
    VIRTUAL_MACHINE = "virtual_machine"


class AssetStatus(str, Enum):
    """Asset status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DECOMMISSIONED = "decommissioned"
    MAINTENANCE = "maintenance"
    PROVISIONING = "provisioning"


class LifecycleStage(str, Enum):
    """Asset lifecycle stage."""

    PLANNING = "planning"
    PROCUREMENT = "procurement"
    DEPLOYMENT = "deployment"
    OPERATION = "operation"
    RETIREMENT = "retirement"


class RelationshipType(str, Enum):
    """Relationship type between assets."""

    DEPENDS_ON = "depends_on"
    HOSTS = "hosts"
    CONNECTS_TO = "connects_to"
    CONTAINS = "contains"
    MANAGES = "manages"
    BACKUP_OF = "backup_of"


# ============================================================================
# Pydantic Models
# ============================================================================


class AssetInventoryCreate(BaseModel):
    """Model for creating an asset in inventory."""

    name: str = Field(..., description="Asset name", min_length=1, max_length=255)
    asset_type: AssetType = Field(default=AssetType.SERVER, description="Type of asset")
    status: AssetStatus = Field(default=AssetStatus.ACTIVE, description="Asset status")
    service: Optional[str] = Field(None, description="Associated service")
    business_unit: Optional[str] = Field(None, description="Business unit")
    env: Optional[str] = Field(None, description="Environment (dev/staging/prod)")
    owner: Optional[str] = Field(None, description="Asset owner")
    ip_address: Optional[str] = Field(None, description="IP address")
    hostname: Optional[str] = Field(None, description="Hostname")
    location: Optional[str] = Field(None, description="Physical location")
    specifications: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Technical specifications"
    )
    tags: Optional[List[str]] = Field(default_factory=list, description="Asset tags")
    cost_center: Optional[str] = Field(None, description="Cost center for billing")
    purchase_date: Optional[datetime] = Field(None, description="Purchase date")
    warranty_expiry: Optional[datetime] = Field(None, description="Warranty expiry date")


class AssetInventoryUpdate(BaseModel):
    """Model for updating an asset in inventory."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    asset_type: Optional[AssetType] = None
    status: Optional[AssetStatus] = None
    service: Optional[str] = None
    business_unit: Optional[str] = None
    env: Optional[str] = None
    owner: Optional[str] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    location: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    cost_center: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None


class AssetInventoryResponse(BaseModel):
    """Model for asset inventory response."""

    id: int
    name: str
    asset_type: AssetType
    status: AssetStatus
    service: Optional[str] = None
    business_unit: Optional[str] = None
    env: Optional[str] = None
    owner: Optional[str] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    location: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    cost_center: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssetRelationship(BaseModel):
    """Model for asset relationship."""

    source_id: int = Field(..., description="Source asset ID")
    target_id: int = Field(..., description="Target asset ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    description: Optional[str] = Field(None, description="Relationship description")


class AssetLifecycle(BaseModel):
    """Model for asset lifecycle information."""

    asset_id: int
    current_stage: LifecycleStage
    stage_start_date: datetime
    estimated_end_date: Optional[datetime] = None
    stage_duration_days: int
    total_lifecycle_days: int
    next_stage: Optional[LifecycleStage] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetDependency(BaseModel):
    """Model for asset dependency."""

    asset_id: int
    asset_name: str
    dependency_type: str
    criticality: str = Field(..., description="Dependency criticality (high/medium/low)")
    depends_on: List[int] = Field(
        default_factory=list, description="List of asset IDs this depends on"
    )
    depended_by: List[int] = Field(
        default_factory=list, description="List of asset IDs that depend on this"
    )
    impact_score: float = Field(..., ge=0, le=100, description="Impact score if this asset fails")


# ============================================================================
# In-Memory Data Storage (for advanced features - fallback)
# ============================================================================

# Store additional asset metadata that extends the base Asset model
# This serves as fallback when database is unavailable
_asset_inventory_metadata: Dict[int, Dict[str, Any]] = {}
_asset_relationships: List[AssetRelationship] = []
_asset_lifecycle_data: Dict[int, AssetLifecycle] = {}
_asset_dependencies: Dict[int, AssetDependency] = {}


def _get_inventory_metadata(asset_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """Get inventory metadata for an asset from database with fallback to memory."""
    try:
        if db:
            metadata_record = db.query(AssetInventoryMetadata).filter(
                AssetInventoryMetadata.asset_id == asset_id
            ).first()
            if metadata_record:
                return metadata_record.inventory_metadata
        # Fallback to memory storage
        return _asset_inventory_metadata.get(asset_id, {})
    except Exception as e:
        logger.error(f"Failed to get inventory metadata from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _asset_inventory_metadata.get(asset_id, {})


def _set_inventory_metadata(asset_id: int, metadata: Dict[str, Any], db: Optional[Session] = None) -> None:
    """Set inventory metadata for an asset in database with fallback to memory."""
    try:
        if db:
            existing_metadata = db.query(AssetInventoryMetadata).filter(
                AssetInventoryMetadata.asset_id == asset_id
            ).first()
            if existing_metadata:
                existing_metadata.inventory_metadata = metadata
                existing_metadata.updated_at = datetime.utcnow()
            else:
                new_metadata = AssetInventoryMetadata(
                    asset_id=asset_id,
                    inventory_metadata=metadata
                )
                db.add(new_metadata)
            db.commit()
        else:
            # Fallback to memory storage
            _asset_inventory_metadata[asset_id] = metadata
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to set inventory metadata in database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_inventory_metadata[asset_id] = metadata


def _delete_inventory_metadata(asset_id: int, db: Optional[Session] = None) -> None:
    """Delete inventory metadata for an asset from database with fallback to memory."""
    try:
        if db:
            db.query(AssetInventoryMetadata).filter(
                AssetInventoryMetadata.asset_id == asset_id
            ).delete()
            db.commit()
        else:
            # Fallback to memory storage
            _asset_inventory_metadata.pop(asset_id, None)
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to delete inventory metadata from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_inventory_metadata.pop(asset_id, None)


def _get_asset_relationships(db: Optional[Session] = None) -> List[AssetRelationship]:
    """Get asset relationships from database with fallback to memory."""
    try:
        if db:
            db_relationships = db.query(AssetRelationshipDB).all()
            return [
                AssetRelationship(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    relationship_type=RelationshipType(rel.relationship_type),
                    description=rel.properties.get("description") if rel.properties else None,
                )
                for rel in db_relationships
            ]
        # Fallback to memory storage
        return _asset_relationships
    except Exception as e:
        logger.error(f"Failed to get asset relationships from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _asset_relationships


def _add_asset_relationship(relationship: AssetRelationship, db: Optional[Session] = None) -> None:
    """Add asset relationship to database with fallback to memory."""
    try:
        if db:
            db_relationship = AssetRelationshipDB(
                source_id=relationship.source_id,
                target_id=relationship.target_id,
                relationship_type=relationship.relationship_type.value,
                properties={"description": relationship.description} if relationship.description else None,
            )
            db.add(db_relationship)
            db.commit()
        else:
            # Fallback to memory storage
            _asset_relationships.append(relationship)
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to add asset relationship to database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_relationships.append(relationship)


def _delete_asset_relationships(asset_id: int, db: Optional[Session] = None) -> None:
    """Delete asset relationships from database with fallback to memory."""
    global _asset_relationships
    try:
        if db:
            db.query(AssetRelationshipDB).filter(
                (AssetRelationshipDB.source_id == asset_id) | (AssetRelationshipDB.target_id == asset_id)
            ).delete()
            db.commit()
        else:
            # Fallback to memory storage
            _asset_relationships = [
                r for r in _asset_relationships if r.source_id != asset_id and r.target_id != asset_id
            ]
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to delete asset relationships from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_relationships = [
            r for r in _asset_relationships if r.source_id != asset_id and r.target_id != asset_id
        ]


def _get_asset_lifecycle(asset_id: int, db: Optional[Session] = None) -> Optional[AssetLifecycle]:
    """Get asset lifecycle from database with fallback to memory."""
    try:
        if db:
            db_lifecycle = db.query(AssetLifecycleDB).filter(
                AssetLifecycleDB.asset_id == asset_id
            ).first()
            if db_lifecycle:
                return AssetLifecycle(
                    asset_id=db_lifecycle.asset_id,
                    current_stage=LifecycleStage(db_lifecycle.stage),
                    stage_start_date=db_lifecycle.start_date,
                    estimated_end_date=db_lifecycle.end_date,
                    stage_duration_days=0,  # Calculate if needed
                    total_lifecycle_days=0,  # Calculate if needed
                    next_stage=None,  # Determine if needed
                    metadata={"notes": db_lifecycle.notes} if db_lifecycle.notes else None,
                )
        # Fallback to memory storage
        return _asset_lifecycle_data.get(asset_id)
    except Exception as e:
        logger.error(f"Failed to get asset lifecycle from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _asset_lifecycle_data.get(asset_id)


def _set_asset_lifecycle(asset_id: int, lifecycle: AssetLifecycle, db: Optional[Session] = None) -> None:
    """Set asset lifecycle in database with fallback to memory."""
    try:
        if db:
            existing_lifecycle = db.query(AssetLifecycleDB).filter(
                AssetLifecycleDB.asset_id == asset_id
            ).first()
            if existing_lifecycle:
                existing_lifecycle.stage = lifecycle.current_stage.value
                existing_lifecycle.start_date = lifecycle.stage_start_date
                existing_lifecycle.end_date = lifecycle.estimated_end_date
                existing_lifecycle.status = "active"
                existing_lifecycle.notes = lifecycle.metadata.get("notes") if lifecycle.metadata else None
            else:
                db_lifecycle = AssetLifecycleDB(
                    asset_id=asset_id,
                    stage=lifecycle.current_stage.value,
                    start_date=lifecycle.stage_start_date,
                    end_date=lifecycle.estimated_end_date,
                    status="active",
                    notes=lifecycle.metadata.get("notes") if lifecycle.metadata else None,
                )
                db.add(db_lifecycle)
            db.commit()
        else:
            # Fallback to memory storage
            _asset_lifecycle_data[asset_id] = lifecycle
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to set asset lifecycle in database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_lifecycle_data[asset_id] = lifecycle


def _delete_asset_lifecycle(asset_id: int, db: Optional[Session] = None) -> None:
    """Delete asset lifecycle from database with fallback to memory."""
    try:
        if db:
            db.query(AssetLifecycleDB).filter(
                AssetLifecycleDB.asset_id == asset_id
            ).delete()
            db.commit()
        else:
            # Fallback to memory storage
            _asset_lifecycle_data.pop(asset_id, None)
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to delete asset lifecycle from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_lifecycle_data.pop(asset_id, None)


def _get_asset_dependencies(db: Optional[Session] = None) -> Dict[int, AssetDependency]:
    """Get asset dependencies from database with fallback to memory."""
    try:
        if db:
            db_dependencies = db.query(AssetDependencyDB).all()
            return {
                dep.asset_id: AssetDependency(
                    asset_id=dep.asset_id,
                    asset_name="",  # Would need to join with Asset table
                    dependency_type=dep.dependency_type,
                    criticality=dep.criticality,
                    depends_on=dep.dependency_details.get("depends_on", []),
                    depended_by=dep.dependency_details.get("depended_by", []),
                    impact_score=dep.dependency_details.get("impact_score", 50.0),
                )
                for dep in db_dependencies
            }
        # Fallback to memory storage
        return _asset_dependencies
    except Exception as e:
        logger.error(f"Failed to get asset dependencies from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _asset_dependencies


def _set_asset_dependency(asset_id: int, dependency: AssetDependency, db: Optional[Session] = None) -> None:
    """Set asset dependency in database with fallback to memory."""
    try:
        if db:
            existing_dependency = db.query(AssetDependencyDB).filter(
                AssetDependencyDB.asset_id == asset_id
            ).first()
            dependency_details = {
                "depends_on": dependency.depends_on,
                "depended_by": dependency.depended_by,
                "impact_score": dependency.impact_score,
            }
            if existing_dependency:
                existing_dependency.dependency_type = dependency.dependency_type
                existing_dependency.dependency_details = dependency_details
                existing_dependency.criticality = dependency.criticality
            else:
                db_dependency = AssetDependencyDB(
                    asset_id=asset_id,
                    dependency_type=dependency.dependency_type,
                    dependency_details=dependency_details,
                    criticality=dependency.criticality,
                )
                db.add(db_dependency)
            db.commit()
        else:
            # Fallback to memory storage
            _asset_dependencies[asset_id] = dependency
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to set asset dependency in database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_dependencies[asset_id] = dependency


def _delete_asset_dependency(asset_id: int, db: Optional[Session] = None) -> None:
    """Delete asset dependency from database with fallback to memory."""
    try:
        if db:
            db.query(AssetDependencyDB).filter(
                AssetDependencyDB.asset_id == asset_id
            ).delete()
            db.commit()
        else:
            # Fallback to memory storage
            _asset_dependencies.pop(asset_id, None)
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to delete asset dependency from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _asset_dependencies.pop(asset_id, None)


# ============================================================================
# API Endpoints - Inventory
# ============================================================================


@router.get("/inventory", response_model=List[AssetInventoryResponse])
async def list_inventory(
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    status: Optional[AssetStatus] = Query(None, description="Filter by status"),
    env: Optional[str] = Query(None, description="Filter by environment"),
    business_unit: Optional[str] = Query(None, description="Filter by business unit"),
    owner: Optional[str] = Query(None, description="Filter by owner"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List all assets in inventory with optional filtering.

    Supports pagination and filtering by asset type, status, environment,
    business unit, and owner.
    """
    try:
        query = db.query(Asset)

        if asset_type:
            # Filter by asset_type from metadata
            matching_ids = [
                aid
                for aid, meta in _asset_inventory_metadata.items()
                if meta.get("asset_type") == asset_type.value
            ]
            if matching_ids:
                query = query.filter(Asset.id.in_(matching_ids))
            else:
                return []

        if status:
            # Filter by status from metadata
            matching_ids = [
                aid
                for aid, meta in _asset_inventory_metadata.items()
                if meta.get("status") == status.value
            ]
            if matching_ids:
                query = query.filter(Asset.id.in_(matching_ids))
            else:
                return []

        if env:
            query = query.filter(Asset.env == env)

        if business_unit:
            query = query.filter(Asset.business_unit == business_unit)

        if owner:
            query = query.filter(Asset.owner == owner)

        assets = query.offset(skip).limit(limit).all()

        # Build response with metadata from database
        result = []
        for asset in assets:
            metadata = _get_inventory_metadata(asset.id, db_core)
            result.append(
                AssetInventoryResponse(
                    id=asset.id,
                    name=asset.name,
                    asset_type=AssetType(metadata.get("asset_type", AssetType.SERVER)),
                    status=AssetStatus(metadata.get("status", AssetStatus.ACTIVE)),
                    service=asset.service,
                    business_unit=asset.business_unit,
                    env=asset.env,
                    owner=asset.owner,
                    ip_address=metadata.get("ip_address"),
                    hostname=metadata.get("hostname"),
                    location=metadata.get("location"),
                    specifications=metadata.get("specifications", {}),
                    tags=metadata.get("tags", []),
                    cost_center=metadata.get("cost_center"),
                    purchase_date=metadata.get("purchase_date"),
                    warranty_expiry=metadata.get("warranty_expiry"),
                    created_at=asset.created_at,
                    updated_at=metadata.get("updated_at"),
                )
            )

        return result
    except Exception as e:
        logger.error(f"Error listing asset inventory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list inventory: {str(e)}")


@router.post(
    "/inventory", response_model=AssetInventoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_inventory_item(
    item: AssetInventoryCreate,
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a new asset in inventory.

    Creates both the base asset record and extended inventory metadata.
    """
    try:
        # Create base asset
        asset = Asset(
            name=item.name,
            service=item.service,
            business_unit=item.business_unit,
            env=item.env,
            owner=item.owner,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        # Store inventory metadata
        metadata = {
            "asset_type": item.asset_type.value,
            "status": item.status.value,
            "ip_address": item.ip_address,
            "hostname": item.hostname,
            "location": item.location,
            "specifications": item.specifications,
            "tags": item.tags,
            "cost_center": item.cost_center,
            "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
            "warranty_expiry": item.warranty_expiry.isoformat() if item.warranty_expiry else None,
            "updated_at": datetime.utcnow().isoformat(),
        }
        _set_inventory_metadata(asset.id, metadata, db_core)

        # Initialize lifecycle data
        lifecycle = AssetLifecycle(
            asset_id=asset.id,
            current_stage=LifecycleStage.PROVISIONING,
            stage_start_date=datetime.utcnow(),
            estimated_end_date=None,
            stage_duration_days=0,
            total_lifecycle_days=0,
            next_stage=LifecycleStage.OPERATION,
            metadata={
                "created_by": (
                    current_user.username if hasattr(current_user, "username") else "system"
                )
            },
        )
        _asset_lifecycle_data[asset.id] = lifecycle

        logger.info(f"Created inventory item: {asset.id} - {item.name}")

        return AssetInventoryResponse(
            id=asset.id,
            name=asset.name,
            asset_type=item.asset_type,
            status=item.status,
            service=asset.service,
            business_unit=asset.business_unit,
            env=asset.env,
            owner=asset.owner,
            ip_address=item.ip_address,
            hostname=item.hostname,
            location=item.location,
            specifications=item.specifications,
            tags=item.tags,
            cost_center=item.cost_center,
            purchase_date=item.purchase_date,
            warranty_expiry=item.warranty_expiry,
            created_at=asset.created_at,
            updated_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Error creating inventory item: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create inventory item: {str(e)}")


@router.get("/inventory/{asset_id}", response_model=AssetInventoryResponse)
async def get_inventory_item(
    asset_id: int,
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get a specific asset from inventory by ID.
    """
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

        metadata = _get_inventory_metadata(asset_id, db_core)

        return AssetInventoryResponse(
            id=asset.id,
            name=asset.name,
            asset_type=AssetType(metadata.get("asset_type", AssetType.SERVER)),
            status=AssetStatus(metadata.get("status", AssetStatus.ACTIVE)),
            service=asset.service,
            business_unit=asset.business_unit,
            env=asset.env,
            owner=asset.owner,
            ip_address=metadata.get("ip_address"),
            hostname=metadata.get("hostname"),
            location=metadata.get("location"),
            specifications=metadata.get("specifications", {}),
            tags=metadata.get("tags", []),
            cost_center=metadata.get("cost_center"),
            purchase_date=(
                datetime.fromisoformat(metadata["purchase_date"])
                if metadata.get("purchase_date")
                else None
            ),
            warranty_expiry=(
                datetime.fromisoformat(metadata["warranty_expiry"])
                if metadata.get("warranty_expiry")
                else None
            ),
            created_at=asset.created_at,
            updated_at=(
                datetime.fromisoformat(metadata["updated_at"])
                if metadata.get("updated_at")
                else None
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inventory item {asset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get inventory item: {str(e)}")


@router.patch("/inventory/{asset_id}", response_model=AssetInventoryResponse)
async def update_inventory_item(
    asset_id: int,
    item: AssetInventoryUpdate,
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Update an existing asset in inventory.

    Updates both the base asset record and extended inventory metadata.
    """
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

        # Update base asset fields
        update_data = item.model_dump(
            exclude_unset=True,
            exclude={
                "asset_type",
                "status",
                "ip_address",
                "hostname",
                "location",
                "specifications",
                "tags",
                "cost_center",
                "purchase_date",
                "warranty_expiry",
            },
        )
        for field, value in update_data.items():
            setattr(asset, field, value)

        db.commit()
        db.refresh(asset)

        # Update inventory metadata
        metadata = _get_inventory_metadata(asset_id, db_core)
        if item.asset_type is not None:
            metadata["asset_type"] = item.asset_type.value
        if item.status is not None:
            metadata["status"] = item.status.value
        if item.ip_address is not None:
            metadata["ip_address"] = item.ip_address
        if item.hostname is not None:
            metadata["hostname"] = item.hostname
        if item.location is not None:
            metadata["location"] = item.location
        if item.specifications is not None:
            metadata["specifications"] = item.specifications
        if item.tags is not None:
            metadata["tags"] = item.tags
        if item.cost_center is not None:
            metadata["cost_center"] = item.cost_center
        if item.purchase_date is not None:
            metadata["purchase_date"] = item.purchase_date.isoformat()
        if item.warranty_expiry is not None:
            metadata["warranty_expiry"] = item.warranty_expiry.isoformat()
        metadata["updated_at"] = datetime.utcnow().isoformat()

        _set_inventory_metadata(asset_id, metadata, db_core)

        logger.info(f"Updated inventory item: {asset_id}")

        return AssetInventoryResponse(
            id=asset.id,
            name=asset.name,
            asset_type=AssetType(metadata.get("asset_type", AssetType.SERVER)),
            status=AssetStatus(metadata.get("status", AssetStatus.ACTIVE)),
            service=asset.service,
            business_unit=asset.business_unit,
            env=asset.env,
            owner=asset.owner,
            ip_address=metadata.get("ip_address"),
            hostname=metadata.get("hostname"),
            location=metadata.get("location"),
            specifications=metadata.get("specifications", {}),
            tags=metadata.get("tags", []),
            cost_center=metadata.get("cost_center"),
            purchase_date=(
                datetime.fromisoformat(metadata["purchase_date"])
                if metadata.get("purchase_date")
                else None
            ),
            warranty_expiry=(
                datetime.fromisoformat(metadata["warranty_expiry"])
                if metadata.get("warranty_expiry")
                else None
            ),
            created_at=asset.created_at,
            updated_at=datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating inventory item {asset_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update inventory item: {str(e)}")


@router.delete("/inventory/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    asset_id: int,
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """
    Delete an asset from inventory.

    Deletes both the base asset record and all associated metadata.
    """
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

        db.delete(asset)
        db.commit()

        # Clean up metadata
        _delete_inventory_metadata(asset_id, db_core)
        _delete_asset_lifecycle(asset_id, db_core)
        _delete_asset_dependency(asset_id, db_core)
        _delete_asset_relationships(asset_id, db_core)

        logger.info(f"Deleted inventory item: {asset_id}")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting inventory item {asset_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete inventory item: {str(e)}")


# ============================================================================
# API Endpoints - Relationships
# ============================================================================


@router.get("/relationships", response_model=List[AssetRelationship])
async def get_asset_relationships(
    asset_id: Optional[int] = Query(None, description="Filter by source asset ID"),
    relationship_type: Optional[RelationshipType] = Query(
        None, description="Filter by relationship type"
    ),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get asset relationships with optional filtering.

    Returns relationships between assets such as dependencies, hosting,
    connections, etc.
    """
    try:
        relationships = _get_asset_relationships(db_core)

        if asset_id is not None:
            relationships = [
                r for r in relationships if r.source_id == asset_id or r.target_id == asset_id
            ]

        if relationship_type is not None:
            relationships = [r for r in relationships if r.relationship_type == relationship_type]

        return relationships
    except Exception as e:
        logger.error(f"Error getting asset relationships: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get relationships: {str(e)}")


@router.post(
    "/relationships", response_model=AssetRelationship, status_code=status.HTTP_201_CREATED
)
async def create_asset_relationship(
    relationship: AssetRelationship,
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a new asset relationship.

    Establishes a relationship between two assets (e.g., dependency, hosting).
    """
    try:
        # Validate that both assets exist
        source_asset = db.query(Asset).filter(Asset.id == relationship.source_id).first()
        target_asset = db.query(Asset).filter(Asset.id == relationship.target_id).first()

        if not source_asset:
            raise HTTPException(
                status_code=404, detail=f"Source asset {relationship.source_id} not found"
            )
        if not target_asset:
            raise HTTPException(
                status_code=404, detail=f"Target asset {relationship.target_id} not found"
            )

        # Check for duplicate relationship
        existing_relationships = _get_asset_relationships(db_core)
        for existing in existing_relationships:
            if (
                existing.source_id == relationship.source_id
                and existing.target_id == relationship.target_id
                and existing.relationship_type == relationship.relationship_type
            ):
                raise HTTPException(status_code=400, detail="Relationship already exists")

        _add_asset_relationship(relationship, db_core)

        logger.info(
            f"Created relationship: {relationship.source_id} -> {relationship.target_id} "
            f"({relationship.relationship_type})"
        )

        return relationship
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating asset relationship: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {str(e)}")


# ============================================================================
# API Endpoints - Lifecycle
# ============================================================================


@router.get("/lifecycle", response_model=List[AssetLifecycle])
async def get_asset_lifecycle(
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    current_stage: Optional[LifecycleStage] = Query(None, description="Filter by lifecycle stage"),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get asset lifecycle information.

    Returns lifecycle stage information for assets including current stage,
    duration, and next planned stage.
    """
    try:
        # Get all assets to build lifecycle data
        if db_core:
            # Use database
            db_lifecycles = db_core.query(AssetLifecycleDB).all()
            lifecycle_data = []
            for db_lifecycle in db_lifecycles:
                lifecycle = AssetLifecycle(
                    asset_id=db_lifecycle.asset_id,
                    current_stage=LifecycleStage(db_lifecycle.stage),
                    stage_start_date=db_lifecycle.start_date,
                    estimated_end_date=db_lifecycle.end_date,
                    stage_duration_days=0,  # Calculate if needed
                    total_lifecycle_days=0,  # Calculate if needed
                    next_stage=None,  # Determine if needed
                    metadata={"notes": db_lifecycle.notes} if db_lifecycle.notes else None,
                )
                lifecycle_data.append(lifecycle)
        else:
            # Fallback to memory storage
            lifecycle_data = list(_asset_lifecycle_data.values())

        if asset_id is not None:
            lifecycle_data = [lc for lc in lifecycle_data if lc.asset_id == asset_id]

        if current_stage is not None:
            lifecycle_data = [lc for lc in lifecycle_data if lc.current_stage == current_stage]

        return lifecycle_data
    except Exception as e:
        logger.error(f"Error getting asset lifecycle: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get lifecycle data: {str(e)}")


@router.patch("/lifecycle/{asset_id}", response_model=AssetLifecycle)
async def update_asset_lifecycle(
    asset_id: int,
    current_stage: LifecycleStage,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Update asset lifecycle stage.

    Transitions an asset to a new lifecycle stage and updates timing information.
    """
    try:
        lifecycle = _get_asset_lifecycle(asset_id, db_core)
        if not lifecycle:
            raise HTTPException(
                status_code=404, detail=f"Lifecycle data for asset {asset_id} not found"
            )

        # Calculate stage duration
        old_start = lifecycle.stage_start_date
        stage_duration = (datetime.utcnow() - old_start).days

        # Update lifecycle
        lifecycle.current_stage = current_stage
        lifecycle.stage_start_date = datetime.utcnow()
        lifecycle.stage_duration_days = stage_duration
        lifecycle.total_lifecycle_days += stage_duration

        # Determine next stage
        stage_order = [
            LifecycleStage.PLANNING,
            LifecycleStage.PROCUREMENT,
            LifecycleStage.DEPLOYMENT,
            LifecycleStage.OPERATION,
            LifecycleStage.RETIREMENT,
        ]
        try:
            current_idx = stage_order.index(current_stage)
            if current_idx < len(stage_order) - 1:
                lifecycle.next_stage = stage_order[current_idx + 1]
            else:
                lifecycle.next_stage = None
        except ValueError:
            lifecycle.next_stage = None

        if lifecycle.metadata is None:
            lifecycle.metadata = {}
        lifecycle.metadata["updated_by"] = (
            current_user.username if hasattr(current_user, "username") else "system"
        )
        lifecycle.metadata["last_transition"] = datetime.utcnow().isoformat()

        # Save to database with fallback
        _set_asset_lifecycle(asset_id, lifecycle, db_core)

        logger.info(f"Updated lifecycle for asset {asset_id} to stage {current_stage}")

        return lifecycle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating asset lifecycle: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update lifecycle: {str(e)}")


# ============================================================================
# API Endpoints - Dependencies
# ============================================================================


@router.get("/dependencies", response_model=List[AssetDependency])
async def get_asset_dependencies(
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    criticality: Optional[str] = Query(None, description="Filter by criticality (high/medium/low)"),
    db: Session = Depends(get_session),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get asset dependency information.

    Returns dependency graphs showing which assets depend on others,
    along with criticality and impact scores.
    """
    try:
        # Build dependency data from database with fallback
        dependencies_dict = _get_asset_dependencies(db_core)
        
        # If empty, try to build from relationships
        if not dependencies_dict:
            _build_dependency_graph(db, db_core)
            dependencies_dict = _get_asset_dependencies(db_core)

        dependencies = list(dependencies_dict.values())

        if asset_id is not None:
            dependencies = [d for d in dependencies if d.asset_id == asset_id]

        if criticality is not None:
            dependencies = [d for d in dependencies if d.criticality == criticality]

        return dependencies
    except Exception as e:
        logger.error(f"Error getting asset dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get dependencies: {str(e)}")


def _build_dependency_graph(db: Session, db_core: Optional[Session] = None) -> None:
    """Build dependency graph from asset relationships."""
    global _asset_dependencies, _asset_relationships

    assets = db.query(Asset).all()
    
    # Get relationships from database if available, otherwise use memory
    if db_core:
        relationships = _get_asset_relationships(db_core)
    else:
        relationships = _asset_relationships

    for asset in assets:
        # Find dependencies based on relationships
        depends_on = []
        depended_by = []

        for rel in relationships:
            if rel.source_id == asset.id and rel.relationship_type == RelationshipType.DEPENDS_ON:
                depends_on.append(rel.target_id)
            elif rel.target_id == asset.id and rel.relationship_type == RelationshipType.DEPENDS_ON:
                depended_by.append(rel.source_id)

        # Calculate impact score based on dependency count and criticality
        impact_score = min(100, len(depended_by) * 10 + len(depends_on) * 5)

        # Determine criticality based on impact score
        if impact_score >= 70:
            criticality = "high"
        elif impact_score >= 40:
            criticality = "medium"
        else:
            criticality = "low"

        dependency = AssetDependency(
            asset_id=asset.id,
            asset_name=asset.name,
            dependency_type="operational",
            criticality=criticality,
            depends_on=depends_on,
            depended_by=depended_by,
            impact_score=impact_score,
        )
        
        # Store in database if available, otherwise use memory
        if db_core:
            _set_asset_dependency(asset.id, dependency, db_core)
        else:
            _asset_dependencies[asset.id] = dependency
