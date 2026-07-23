---
name: fastapi-development
description: FastAPI development patterns and best practices
argument-hint: "[endpoint]"
allowed-tools:
  - read_file
  - write_to_file
  - edit
  - multi_edit
  - grep_search
  - find_by_name
  - bash
  - command_status
  - todo_list
  - skill
  - list_resources
  - read_resource
  - search_web
  - read_url_content
triggers:
  - user
  - model
subagent: false
priority: high
auto-apply:
  - "创建 API 路由"
  - "添加 FastAPI 端点"
  - "API 设计"
  - "请求响应模型"
  - "API 错误处理"
  - "FastAPI 依赖注入"
file-patterns:
  - "api/**/*.py"
  - "**/main.py"
  - "**/app.py"
  - "**/router*.py"
excluded-patterns:
  - "**/venv/**"
  - "**/__pycache__/**"
---

# FastAPI Development Skill

## Purpose
Specialized skill for FastAPI development in the AIOps Agent project, ensuring consistent API design and implementation.

## Auto-approved Tools
- read
- write
- edit
- grep
- find_file_by_name
- exec

## Skill Instructions

### FastAPI Project Structure
All API routers should be located in the `api/` directory following the pattern:
```
api/
├── __init__.py
├── your_router.py
└── schemas/
    └── __init__.py
```

### Router Development Guidelines

#### Standard Router Template
```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

router = APIRouter(
    prefix="/your-resource",
    tags=["your-resource"],
    responses={404: {"description": "Not found"}}
)

# Request/Response Schemas
class YourResourceCreate(BaseModel):
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Optional description")

class YourResourceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    
    class Config:
        from_attributes = True

# Endpoints
@router.post("/", response_model=YourResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: YourResourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new resource."""
    try:
        # Implementation here
        logger.info(f"Creating resource: {resource.name}")
        return resource
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resource: {str(e)}"
        )

@router.get("/", response_model=List[YourResourceResponse])
async def list_resources(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all resources with pagination."""
    try:
        # Implementation here
        return []
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list resources: {str(e)}"
        )

@router.get("/{resource_id}", response_model=YourResourceResponse)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific resource by ID."""
    try:
        # Implementation here
        return {}
    except Exception as e:
        logger.error(f"Error getting resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: {str(e)}"
        )
```

### API Design Principles

#### RESTful Conventions
- Use nouns for resource names (plural)
- Use HTTP methods appropriately:
  - GET: Retrieve resources
  - POST: Create new resources
  - PUT/PATCH: Update resources
  - DELETE: Remove resources
- Use appropriate status codes:
  - 200: Success
  - 201: Created
  - 204: No Content
  - 400: Bad Request
  - 401: Unauthorized
  - 403: Forbidden
  - 404: Not Found
  - 500: Internal Server Error

#### Request Validation
- Use Pydantic models for all request bodies
- Add Field descriptions for API documentation
- Use proper validators (e.g., `@field_validator`)
- Validate query parameters

#### Response Formatting
- Use consistent response models
- Include proper HTTP status codes
- Add error details in error responses
- Use `from_attributes = True` for ORM models

### Dependency Injection Patterns

#### Database Session
```python
from aiops_core.database import get_db

@router.get("/")
async def endpoint(db: AsyncSession = Depends(get_db)):
    # Use db for database operations
    pass
```

#### Authentication
```python
from aiops_core.auth import get_current_user

@router.get("/protected")
async def protected_endpoint(current_user = Depends(get_current_user)):
    # Current user is available
    pass
```

#### Common Dependencies
- `get_db`: Database session
- `get_current_user`: Current authenticated user
- `get_redis`: Redis client
- Rate limiting dependencies
- Cache dependencies

### Async Database Operations

#### Query Patterns
```python
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

# Read
async def get_items(db: AsyncSession):
    result = await db.execute(select(Item).where(Item.active == True))
    return result.scalars().all()

# Read with relationships
async def get_items_with_relations(db: AsyncSession):
    result = await db.execute(
        select(Item).options(selectinload(Item.related))
    )
    return result.scalars().all()

# Create
async def create_item(db: AsyncSession, item_data: dict):
    item = Item(**item_data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

# Update
async def update_item(db: AsyncSession, item_id: int, update_data: dict):
    await db.execute(
        update(Item).where(Item.id == item_id).values(**update_data)
    )
    await db.commit()

# Delete
async def delete_item(db: AsyncSession, item_id: int):
    await db.execute(delete(Item).where(Item.id == item_id))
    await db.commit()
```

### Error Handling

#### Standard Error Response
```python
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

@router.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}
    )
```

#### Custom Exceptions
```python
class ResourceNotFoundException(Exception):
    pass

class ValidationException(Exception):
    pass

@router.exception_handler(ResourceNotFoundException)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )
```

### Performance Optimization

#### Caching Strategy
```python
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@router.get("/cached")
@cache(expire=60)  # Cache for 60 seconds
async def cached_endpoint():
    return expensive_operation()
```

#### Pagination
```python
from typing import List

class PaginatedResponse(BaseModel):
    items: List[YourResourceResponse]
    total: int
    page: int
    page_size: int

@router.get("/", response_model=PaginatedResponse)
async def list_resources(
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db)
):
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Query with pagination
    result = await db.execute(
        select(Resource).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(select(func.count(Resource.id)))
    total = count_result.scalar()
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
```

### Testing FastAPI Endpoints

#### Test Template
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_resource(client: AsyncClient, db: AsyncSession):
    response = await client.post(
        "/your-resource/",
        json={"name": "test", "description": "test description"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test"

@pytest.mark.asyncio
async def test_list_resources(client: AsyncClient):
    response = await client.get("/your-resource/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### OpenAPI Documentation

#### Enhancing Documentation
```python
@router.post(
    "/",
    response_model=YourResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new resource",
    description="Creates a new resource with the provided data.",
    responses={
        201: {"description": "Resource created successfully"},
        400: {"description": "Invalid request data"},
        500: {"description": "Internal server error"}
    }
)
async def create_resource(resource: YourResourceCreate):
    """Create a new resource.
    
    Args:
        resource: The resource data to create
        
    Returns:
        The created resource
        
    Raises:
        HTTPException: If creation fails
    """
    pass
```

### Monitoring and Observability

#### Logging
```python
from loguru import logger

@router.get("/")
async def monitored_endpoint():
    logger.info("Endpoint called")
    logger.debug("Debug information")
    logger.warning("Warning condition")
    logger.error("Error condition")
```

#### Metrics
```python
from prometheus_client import Counter

request_counter = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method']
)

@router.get("/")
async def monitored_endpoint():
    request_counter.labels(endpoint='/your-resource/', method='GET').inc()
    return {}
```

## When to Invoke
Invoke this skill automatically when:
- Creating new API endpoints
- Modifying existing routers
- Adding request/response models
- Implementing authentication/authorization
- Adding database operations to endpoints
- Writing API tests
- Performance optimization for APIs

## GitLab 上传权限控制

### 项目配置
- **项目目录**: `C:\AIOps_Agent_bak`
- **GitLab项目**: `Hualong_Chen/neurosync-agent-tool-platform`
- **上传控制**: 严格启用，需要明确用户指令

### 上传权限规则
- ❌ **禁止**: 未经用户明确指令的任何GitLab上传操作
- ✅ **允许**: 仅在用户明确给出上传指令时执行上传
- **上传指令格式**: "将某一个目录(含目录中的子目录和文件)或者某一个/几个文件(具体文件名)上传到我的gitlab中"

### API开发安全检查
在执行任何可能涉及GitLab操作时：
1. 验证是否为只读操作（代码搜索、查看等）
2. 如果是写入操作，检查是否有明确的上传指令
3. 确认操作不会违反上传控制规则
4. 记录所有GitLab相关操作

## Project-Specific Context
This project uses:
- FastAPI with async/await patterns
- SQLAlchemy 2.0 with async support
- Pydantic v2 for validation
- OpenTelemetry for observability
- Comprehensive error handling
- 70+ existing routers to reference for patterns