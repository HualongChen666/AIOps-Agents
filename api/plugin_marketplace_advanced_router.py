# -*- coding: utf-8 -*-
"""
Plugin Marketplace Advanced API Router
Provides comprehensive API endpoints for plugin marketplace management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.auth import check_rate_limit, get_current_user, require_permission
from core.database import get_db
from core.models import (
    PluginListingDB,
    PluginReviewDB,
    PluginCategoryDB,
    InstalledPluginDB,
    User,
)

router = APIRouter(prefix="/api/v1/plugin/marketplace", tags=["Plugin Marketplace Advanced"])


# Pydantic Models
class PluginListingCreate(BaseModel):
    """Plugin listing creation model"""

    plugin_id: str = Field(..., description="Plugin ID")
    plugin_name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(..., description="Plugin description")
    author: str = Field(..., description="Plugin author")
    category: str = Field(default="general", description="Plugin category")
    tags: List[str] = Field(default_factory=list, description="Plugin tags")
    price: Optional[float] = Field(None, description="Plugin price (None for free)")
    quality: str = Field(
        default="community",
        description="Quality level (certified, verified, community, experimental)",
    )
    download_url: str = Field(..., description="Download URL")
    screenshot_urls: List[str] = Field(default_factory=list, description="Screenshot URLs")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    repository_url: Optional[str] = Field(None, description="Repository URL")

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        valid_qualities = ["certified", "verified", "community", "experimental"]
        if v not in valid_qualities:
            raise ValueError(f"Invalid quality level. Must be one of: {', '.join(valid_qualities)}")
        return v


class PluginListingUpdate(BaseModel):
    """Plugin listing update model"""

    plugin_name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    price: Optional[float] = None
    quality: Optional[str] = None
    download_url: Optional[str] = None
    screenshot_urls: Optional[List[str]] = None
    documentation_url: Optional[str] = None
    repository_url: Optional[str] = None


class PluginListingResponse(BaseModel):
    """Plugin listing response model"""

    id: str
    plugin_id: str
    plugin_name: str
    version: str
    description: str
    author: str
    category: str
    tags: Optional[List[str]]
    price: Optional[float]
    quality: str
    download_count: int
    rating: float
    review_count: int
    download_url: str
    screenshot_urls: Optional[List[str]]
    documentation_url: Optional[str]
    repository_url: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ReviewCreate(BaseModel):
    """Review creation model"""

    plugin_id: str = Field(..., description="Plugin ID")
    reviewer_id: str = Field(..., description="Reviewer ID")
    reviewer_name: str = Field(..., description="Reviewer name")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    review_text: str = Field(..., description="Review text")


class ReviewResponse(BaseModel):
    """Review response model"""

    id: str
    plugin_id: str
    reviewer_id: str
    reviewer_name: str
    rating: int
    review_text: str
    created_at: datetime
    updated_at: datetime


class CategoryResponse(BaseModel):
    """Category response model"""

    id: str
    category_name: str
    category_description: Optional[str]
    parent_category_id: Optional[str]
    enabled: bool


class InstallRequest(BaseModel):
    """Plugin install request model"""

    version: Optional[str] = Field(
        None, description="Specific version to install (latest if not specified)"
    )
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")


class InstallResponse(BaseModel):
    """Install response model"""

    success: bool
    plugin_id: str
    plugin_name: str
    version: str
    install_path: str
    message: str


# ============================================================================
# Database Storage Migration
# ============================================================================
# All in-memory storage has been migrated to PostgreSQL database models
# - PluginListingDB -> plugin_listings table
# - PluginReviewDB -> plugin_reviews table
# - PluginCategoryDB -> plugin_categories table
# - InstalledPluginDB -> installed_plugins table
# ============================================================================


# Plugin Endpoints
@router.get(
    "/plugins", response_model=List[PluginListingResponse], summary="Get all plugin listings"
)
async def get_plugin_listings(
    category: Optional[str] = Query(None, description="Filter by category"),
    quality: Optional[str] = Query(None, description="Filter by quality level"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    sort_by: str = Query(
        "updated_at", description="Sort field (name, rating, download_count, updated_at)"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get all plugin listings with optional filtering and sorting

    Args:
        category: Filter by category
        quality: Filter by quality level
        search: Search by name or description
        sort_by: Sort field
        limit: Maximum number of results

    Returns:
        List of plugin listings
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin marketplace listings requested by user {current_user.username} from {client_ip}")
    
    try:
        # Try to get listings from database
        query = db.query(PluginListingDB).filter(PluginListingDB.enabled == True)
        
        # Filter by category
        if category:
            query = query.filter(PluginListingDB.category == category)
        
        # Filter by quality
        if quality:
            query = query.filter(PluginListingDB.quality == quality)
        
        # Search by name or description
        if search:
            query = query.filter(
                (PluginListingDB.plugin_name.ilike(f"%{search}%")) |
                (PluginListingDB.description.ilike(f"%{search}%"))
            )
        
        # Sort
        if sort_by == "name":
            query = query.order_by(PluginListingDB.plugin_name)
        elif sort_by == "rating":
            query = query.order_by(PluginListingDB.rating.desc())
        elif sort_by == "download_count":
            query = query.order_by(PluginListingDB.download_count.desc())
        else:
            query = query.order_by(PluginListingDB.updated_at.desc())
        
        # Limit
        listings = query.limit(limit).all()
        
        # Convert to response format
        return [
            PluginListingResponse(
                id=str(listing.id),
                plugin_id=listing.plugin_id,
                plugin_name=listing.plugin_name,
                version=listing.version,
                description=listing.description,
                author=listing.author,
                category=listing.category,
                tags=listing.tags or [],
                price=listing.price,
                quality=listing.quality,
                download_url=listing.download_url,
                screenshot_urls=listing.screenshot_urls or [],
                documentation_url=listing.documentation_url,
                repository_url=listing.repository_url,
                download_count=listing.download_count,
                rating=listing.rating,
                review_count=listing.review_count,
                enabled=listing.enabled,
                created_at=listing.created_at,
                updated_at=listing.updated_at,
            )
            for listing in listings
        ]
        
    except Exception as e:
        logger.error(f"Error getting plugin listings: {e}")
        # Fallback to empty list
        return []


@router.get(
    "/plugins/{plugin_id}", response_model=PluginListingResponse, summary="Get a plugin by ID"
)
async def get_plugin(
    plugin_id: str,
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get a plugin listing by ID

    Args:
        plugin_id: Plugin listing ID

    Returns:
        Plugin listing data
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin details requested by user {current_user.username} from {client_ip}")
    
    try:
        # Search by listing ID or plugin_id
        plugin_listing = db.query(PluginListingDB).filter(
            (PluginListingDB.id == plugin_id) | (PluginListingDB.plugin_id == plugin_id)
        ).first()

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        return PluginListingResponse(
            id=str(plugin_listing.id),
            plugin_id=plugin_listing.plugin_id,
            plugin_name=plugin_listing.plugin_name,
            version=plugin_listing.version,
            description=plugin_listing.description,
            author=plugin_listing.author,
            category=plugin_listing.category,
            tags=plugin_listing.tags or [],
            price=plugin_listing.price,
            quality=plugin_listing.quality,
            download_url=plugin_listing.download_url,
            screenshot_urls=plugin_listing.screenshot_urls or [],
            documentation_url=plugin_listing.documentation_url,
            repository_url=plugin_listing.repository_url,
            download_count=plugin_listing.download_count,
            rating=plugin_listing.rating,
            review_count=plugin_listing.review_count,
            enabled=plugin_listing.enabled,
            created_at=plugin_listing.created_at,
            updated_at=plugin_listing.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugins/{plugin_id}/install", response_model=InstallResponse, summary="Install a plugin"
)
async def install_plugin(
    plugin_id: str,
    request: InstallRequest,
    current_user: User = Depends(require_permission("plugin", "execute")),
    db: Session = Depends(get_db),
    request_obj: Request = None,
):
    """
    Install a plugin from the marketplace

    Args:
        plugin_id: Plugin ID
        request: Install request data

    Returns:
        Installation result
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request_obj.client.host if request_obj else "unknown"
    logger.info(f"Plugin installation requested by user {current_user.username} from {client_ip}")
    
    try:
        # Find the plugin
        plugin_listing = db.query(PluginListingDB).filter(
            (PluginListingDB.id == plugin_id) | (PluginListingDB.plugin_id == plugin_id)
        ).first()

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Check if already installed
        existing_install = db.query(InstalledPluginDB).filter(
            InstalledPluginDB.plugin_id == plugin_listing.plugin_id
        ).first()
        if existing_install:
            raise HTTPException(status_code=400, detail="Plugin is already installed")

        # Simulate installation
        install_path = f"plugins/{plugin_listing.plugin_name}"

        # Record installation
        new_install = InstalledPluginDB(
            id=str(uuid4()),
            plugin_id=plugin_listing.plugin_id,
            installed_version=request.version or plugin_listing.version,
            status="active",
            configuration=request.config,
        )
        db.add(new_install)
        db.commit()
        db.refresh(new_install)

        # Update download count
        plugin_listing.download_count += 1
        plugin_listing.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Installed plugin: {plugin_listing.plugin_name}")

        return InstallResponse(
            success=True,
            plugin_id=plugin_listing.plugin_id,
            plugin_name=plugin_listing.plugin_name,
            version=request.version or plugin_listing.version,
            install_path=install_path,
            message=f"Plugin '{plugin_listing.plugin_name}' installed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/uninstall", summary="Uninstall a plugin")
async def uninstall_plugin(
    plugin_id: str,
    current_user: User = Depends(require_permission("plugin", "execute")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Uninstall a plugin

    Args:
        plugin_id: Plugin ID

    Returns:
        Uninstallation result
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin uninstallation requested by user {current_user.username} from {client_ip}")
    
    try:
        # Find the plugin
        plugin_listing = db.query(PluginListingDB).filter(
            (PluginListingDB.id == plugin_id) | (PluginListingDB.plugin_id == plugin_id)
        ).first()

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Check if installed
        installed_plugin = db.query(InstalledPluginDB).filter(
            InstalledPluginDB.plugin_id == plugin_listing.plugin_id
        ).first()
        if not installed_plugin:
            raise HTTPException(status_code=400, detail="Plugin is not installed")

        # Remove installation record
        db.delete(installed_plugin)
        db.commit()

        logger.info(f"Uninstalled plugin: {plugin_listing.plugin_name}")

        return {
            "status": "success",
            "message": f"Plugin '{plugin_listing.plugin_name}' uninstalled successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Category Endpoints
@router.get("/categories", response_model=List[CategoryResponse], summary="Get all categories")
async def get_categories(
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get all plugin categories

    Returns:
        List of categories
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin categories requested by user {current_user.username} from {client_ip}")
    
    try:
        categories = db.query(PluginCategoryDB).all()
        return [
            CategoryResponse(
                id=str(category.id),
                category_name=category.category_name,
                category_description=category.category_description,
                parent_category_id=category.parent_category_id,
                enabled=category.enabled,
            )
            for category in categories
        ]
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Review Endpoints
@router.get("/reviews", response_model=List[ReviewResponse], summary="Get all reviews")
async def get_reviews(
    plugin_id: Optional[str] = Query(None, description="Filter by plugin ID"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get all reviews with optional filtering

    Args:
        plugin_id: Filter by plugin ID
        rating: Filter by rating
        limit: Maximum number of results

    Returns:
        List of reviews
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin reviews requested by user {current_user.username} from {client_ip}")
    
    try:
        query = db.query(PluginReviewDB)

        # Filter by plugin_id
        if plugin_id:
            query = query.filter(PluginReviewDB.plugin_id == plugin_id)

        # Filter by rating
        if rating:
            query = query.filter(PluginReviewDB.rating == rating)

        reviews = query.limit(limit).all()

        return [
            ReviewResponse(
                id=str(review.id),
                plugin_id=review.plugin_id,
                reviewer_id=review.reviewer_id,
                reviewer_name=review.reviewer_name,
                rating=review.rating,
                review_text=review.review_text,
                created_at=review.created_at,
                updated_at=review.updated_at,
            )
            for review in reviews
        ]
    except Exception as e:
        logger.error(f"Error getting reviews: {e}")
        return []


@router.post("/reviews", response_model=ReviewResponse, summary="Create a review")
async def create_review(
    review: ReviewCreate,
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Create a new review for a plugin

    Args:
        review: Review data

    Returns:
        Created review
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin review creation requested by user {current_user.username} from {client_ip}")
    
    try:
        # Find the plugin
        plugin_listing = db.query(PluginListingDB).filter(
            (PluginListingDB.id == review.plugin_id) | (PluginListingDB.plugin_id == review.plugin_id)
        ).first()

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Create review
        new_review = PluginReviewDB(
            id=str(uuid4()),
            plugin_id=review.plugin_id,
            reviewer_id=review.reviewer_id,
            reviewer_name=review.reviewer_name,
            rating=review.rating,
            review_text=review.review_text,
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        # Update plugin review count
        plugin_listing.review_count += 1
        db.commit()

        return ReviewResponse(
            id=str(new_review.id),
            plugin_id=new_review.plugin_id,
            reviewer_id=new_review.reviewer_id,
            reviewer_name=new_review.reviewer_name,
            rating=new_review.rating,
            review_text=new_review.review_text,
            created_at=new_review.created_at,
            updated_at=new_review.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/plugins/{plugin_id}/reviews",
    response_model=List[ReviewResponse],
    summary="Get reviews for a plugin",
)
async def get_plugin_reviews(
    plugin_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get all reviews for a specific plugin

    Args:
        plugin_id: Plugin ID
        limit: Maximum number of results

    Returns:
        List of reviews for the plugin
    """
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin reviews for {plugin_id} requested by user {current_user.username} from {client_ip}")
    
    try:
        reviews = db.query(PluginReviewDB).filter(PluginReviewDB.plugin_id == plugin_id).limit(limit).all()

        return [
            ReviewResponse(
                id=str(review.id),
                plugin_id=review.plugin_id,
                reviewer_id=review.reviewer_id,
                reviewer_name=review.reviewer_name,
                rating=review.rating,
                review_text=review.review_text,
                created_at=review.created_at,
                updated_at=review.updated_at,
            )
            for review in reviews
        ]
    except Exception as e:
        logger.error(f"Error getting plugin reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
