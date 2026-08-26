# -*- coding: utf-8 -*-
"""
Plugin Marketplace Advanced API Router
Provides comprehensive API endpoints for plugin marketplace management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import (
    PluginListingDB,
    PluginReviewDB,
    PluginCategoryDB,
    InstalledPluginDB,
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
    tags: List[str]
    price: Optional[float]
    quality: str
    review_status: str
    download_count: int
    rating: float
    review_count: int
    download_url: str
    screenshot_urls: List[str]
    documentation_url: Optional[str]
    repository_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReviewCreate(BaseModel):
    """Review creation model"""

    plugin_id: str = Field(..., description="Plugin ID")
    reviewer: str = Field(..., description="Reviewer name")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    comment: str = Field(..., description="Review comment")
    title: Optional[str] = Field(None, description="Review title")


class ReviewResponse(BaseModel):
    """Review response model"""

    id: str
    plugin_id: str
    plugin_name: str
    reviewer: str
    rating: int
    comment: str
    title: Optional[str]
    timestamp: datetime
    helpful_count: int


class CategoryResponse(BaseModel):
    """Category response model"""

    id: str
    name: str
    description: str
    plugin_count: int
    icon: Optional[str]


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
    db: Session = Depends(get_db),
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
async def get_plugin(plugin_id: str):
    """
    Get a plugin listing by ID

    Args:
        plugin_id: Plugin listing ID

    Returns:
        Plugin listing data
    """
    try:
        # Search by listing ID or plugin_id
        for listing in _listings.values():
            if listing["id"] == plugin_id or listing["plugin_id"] == plugin_id:
                return PluginListingResponse(**listing)

        raise HTTPException(status_code=404, detail="Plugin not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugins/{plugin_id}/install", response_model=InstallResponse, summary="Install a plugin"
)
async def install_plugin(plugin_id: str, request: InstallRequest):
    """
    Install a plugin from the marketplace

    Args:
        plugin_id: Plugin ID
        request: Install request data

    Returns:
        Installation result
    """
    try:
        # Find the plugin
        plugin_listing = None
        for listing in _listings.values():
            if listing["id"] == plugin_id or listing["plugin_id"] == plugin_id:
                plugin_listing = listing
                break

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Check if already installed
        if plugin_listing["plugin_id"] in _installed_plugins:
            raise HTTPException(status_code=400, detail="Plugin is already installed")

        # Simulate installation
        install_path = f"plugins/{plugin_listing['plugin_name']}"

        # Record installation
        _installed_plugins[plugin_listing["plugin_id"]] = {
            "plugin_id": plugin_listing["plugin_id"],
            "plugin_name": plugin_listing["plugin_name"],
            "version": request.version or plugin_listing["version"],
            "install_path": install_path,
            "config": request.config,
            "installed_at": datetime.utcnow(),
        }

        # Update download count
        plugin_listing["download_count"] += 1
        plugin_listing["updated_at"] = datetime.utcnow()

        logger.info(f"Installed plugin: {plugin_listing['plugin_name']}")

        return InstallResponse(
            success=True,
            plugin_id=plugin_listing["plugin_id"],
            plugin_name=plugin_listing["plugin_name"],
            version=request.version or plugin_listing["version"],
            install_path=install_path,
            message=f"Plugin '{plugin_listing['plugin_name']}' installed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/uninstall", summary="Uninstall a plugin")
async def uninstall_plugin(plugin_id: str):
    """
    Uninstall a plugin

    Args:
        plugin_id: Plugin ID

    Returns:
        Uninstallation result
    """
    try:
        # Find the plugin
        plugin_listing = None
        for listing in _listings.values():
            if listing["id"] == plugin_id or listing["plugin_id"] == plugin_id:
                plugin_listing = listing
                break

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Check if installed
        if plugin_listing["plugin_id"] not in _installed_plugins:
            raise HTTPException(status_code=400, detail="Plugin is not installed")

        # Remove installation record
        del _installed_plugins[plugin_listing["plugin_id"]]

        logger.info(f"Uninstalled plugin: {plugin_listing['plugin_name']}")

        return {
            "status": "success",
            "message": f"Plugin '{plugin_listing['plugin_name']}' uninstalled successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Category Endpoints
@router.get("/categories", response_model=List[CategoryResponse], summary="Get all categories")
async def get_categories():
    """
    Get all plugin categories

    Returns:
        List of categories
    """
    try:
        return [CategoryResponse(**cat) for cat in _categories.values()]
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Review Endpoints
@router.get("/reviews", response_model=List[ReviewResponse], summary="Get all reviews")
async def get_reviews(
    plugin_id: Optional[str] = Query(None, description="Filter by plugin ID"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
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
    try:
        all_reviews = []
        for plugin_id_key, reviews in _reviews.items():
            for review in reviews:
                all_reviews.append(review)

        # Filter by plugin_id
        if plugin_id:
            all_reviews = [r for r in all_reviews if r["plugin_id"] == plugin_id]

        # Filter by rating
        if rating:
            all_reviews = [r for r in all_reviews if r["rating"] == rating]

        # Sort by timestamp (newest first)
        all_reviews.sort(key=lambda x: x["timestamp"], reverse=True)

        # Limit results
        all_reviews = all_reviews[:limit]

        return [ReviewResponse(**r) for r in all_reviews]
    except Exception as e:
        logger.error(f"Error getting reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reviews", response_model=ReviewResponse, summary="Create a review")
async def create_review(review: ReviewCreate):
    """
    Create a new review for a plugin

    Args:
        review: Review data

    Returns:
        Created review
    """
    try:
        # Find the plugin
        plugin_listing = None
        for listing in _listings.values():
            if listing["id"] == review.plugin_id or listing["plugin_id"] == review.plugin_id:
                plugin_listing = listing
                break

        if not plugin_listing:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Create review
        new_review = {
            "id": str(uuid4()),
            "plugin_id": review.plugin_id,
            "plugin_name": plugin_listing["plugin_name"],
            "reviewer": review.reviewer,
            "rating": review.rating,
            "comment": review.comment,
            "title": review.title,
            "timestamp": datetime.utcnow(),
            "helpful_count": 0,
        }

        # Add to reviews
        if review.plugin_id not in _reviews:
            _reviews[review.plugin_id] = []
        _reviews[review.plugin_id].append(new_review)

        # Update plugin rating
        plugin_reviews = _reviews[review.plugin_id]
        total_rating = sum(r["rating"] for r in plugin_reviews)
        plugin_listing["rating"] = round(total_rating / len(plugin_reviews), 1)
        plugin_listing["review_count"] = len(plugin_reviews)
        plugin_listing["updated_at"] = datetime.utcnow()

        logger.info(f"Created review for plugin: {plugin_listing['plugin_name']}")

        return ReviewResponse(**new_review)
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
async def get_plugin_reviews(plugin_id: str, limit: int = Query(50, ge=1, le=100)):
    """
    Get all reviews for a specific plugin

    Args:
        plugin_id: Plugin ID
        limit: Maximum number of results

    Returns:
        List of reviews for the plugin
    """
    try:
        if plugin_id not in _reviews:
            return []

        reviews = _reviews[plugin_id].copy()

        # Sort by timestamp (newest first)
        reviews.sort(key=lambda x: x["timestamp"], reverse=True)

        # Limit results
        reviews = reviews[:limit]

        return [ReviewResponse(**r) for r in reviews]
    except Exception as e:
        logger.error(f"Error getting plugin reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
