# -*- coding: utf-8 -*-
"""
Pagination Utilities

Provides standardized pagination for all API endpoints to ensure
consistent query optimization and memory management.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel):
    """Standard paginated response format"""
    items: List[Any]
    pagination: Dict[str, Any]
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginationHelper:
    """Helper class for pagination operations"""
    
    @staticmethod
    def apply_pagination(
        query: Query,
        params: PaginationParams
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Apply pagination to a SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            params: Pagination parameters
            
        Returns:
            Tuple of (results, pagination_info)
        """
        # Apply sorting if specified
        if params.sort_by:
            sort_column = getattr(query.column_described, params.sort_by, None)
            if sort_column:
                if params.sort_order == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
        
        # Calculate offset
        offset = (params.page - 1) * params.per_page
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        results = query.offset(offset).limit(params.per_page).all()
        
        # Calculate pagination info
        total_pages = (total + params.per_page - 1) // params.per_page if total > 0 else 0
        
        pagination_info = {
            "page": params.page,
            "per_page": params.per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": params.page < total_pages,
            "has_prev": params.page > 1,
            "next_page": params.page + 1 if params.page < total_pages else None,
            "prev_page": params.page - 1 if params.page > 1 else None
        }
        
        return results, pagination_info
    
    @staticmethod
    def create_paginated_response(
        items: List[Any],
        pagination_info: Dict[str, Any]
    ) -> PaginatedResponse:
        """
        Create a standardized paginated response
        
        Args:
            items: List of items
            pagination_info: Pagination information dictionary
            
        Returns:
            PaginatedResponse object
        """
        return PaginatedResponse(
            items=items,
            pagination=pagination_info,
            total=pagination_info["total"],
            page=pagination_info["page"],
            per_page=pagination_info["per_page"],
            total_pages=pagination_info["total_pages"]
        )
    
    @staticmethod
    def validate_pagination_params(params: Dict[str, Any]) -> PaginationParams:
        """
        Validate and convert pagination parameters
        
        Args:
            params: Raw pagination parameters from request
            
        Returns:
            Validated PaginationParams object
        """
        return PaginationParams(
            page=params.get("page", 1),
            per_page=params.get("per_page", 50),
            sort_by=params.get("sort_by"),
            sort_order=params.get("sort_order", "asc")
        )


# Export commonly used utilities
__all__ = [
    "PaginationParams",
    "PaginatedResponse",
    "PaginationHelper",
]