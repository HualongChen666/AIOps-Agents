# -*- coding: utf-8 -*-
"""
Localization Advanced API Router
Provides comprehensive CRUD operations for localization management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from core.database import SessionLocal
from core.models import LocalizationLanguageDB, LocalizationResourceDB
from core.persistent_store import PersistentStore

router = APIRouter(prefix="/api/v1/localization", tags=["Localization Advanced"])


# Pydantic Models
class LanguageCreate(BaseModel):
    """Language creation model"""

    code: str = Field(..., description="Language code (e.g., 'zh-CN', 'en-US')")
    name: str = Field(..., description="Language name")
    native_name: str = Field(..., description="Native language name")
    enabled: bool = Field(default=True, description="Whether the language is enabled")
    is_default: bool = Field(default=False, description="Whether this is the default language")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or len(v) < 2:
            raise ValueError("Language code must be at least 2 characters")
        return v


class LanguageUpdate(BaseModel):
    """Language update model"""

    name: Optional[str] = None
    native_name: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class LanguageResponse(BaseModel):
    """Language response model"""

    id: str
    code: str
    name: str
    native_name: str
    enabled: bool
    is_default: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ResourceCreate(BaseModel):
    """Resource creation model"""

    language_code: str = Field(..., description="Language code")
    namespace: str = Field(..., description="Resource namespace")
    key: str = Field(..., description="Resource key")
    value: str = Field(..., description="Resource value")
    context: Optional[str] = Field(None, description="Translation context")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResourceUpdate(BaseModel):
    """Resource update model"""

    value: Optional[str] = None
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ResourceResponse(BaseModel):
    """Resource response model"""

    id: str
    language_code: str
    namespace: str
    key: str
    value: str
    context: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TranslationCreate(BaseModel):
    """Translation creation model"""

    source_language: str = Field(..., description="Source language code")
    target_language: str = Field(..., description="Target language code")
    namespace: str = Field(..., description="Translation namespace")
    key: str = Field(..., description="Translation key")
    source_value: str = Field(..., description="Source text")
    target_value: str = Field(..., description="Translated text")
    status: str = Field(default="draft", description="Translation status")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TranslationResponse(BaseModel):
    """Translation response model"""

    id: str
    source_language: str
    target_language: str
    namespace: str
    key: str
    source_value: str
    target_value: str
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AdapterCreate(BaseModel):
    """Adapter creation model"""

    name: str = Field(..., description="Adapter name")
    type: str = Field(..., description="Adapter type")
    config: Dict[str, Any] = Field(default_factory=dict, description="Adapter configuration")
    enabled: bool = Field(default=True, description="Whether the adapter is enabled")
    priority: int = Field(default=0, description="Adapter priority")


class AdapterResponse(BaseModel):
    """Adapter response model"""

    id: str
    name: str
    type: str
    config: Dict[str, Any]
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime


# In-memory storage (in production, use a database)
# Languages and resources are persisted in their dedicated ORM tables (the
# single source of truth used by the rest of the platform).  Translations and
# adapters use the durable document store.
_translations: PersistentStore = PersistentStore("localization", "translations")
_adapters: PersistentStore = PersistentStore("localization", "adapters")


def _row_to_language(row: LocalizationLanguageDB) -> LanguageResponse:
    """Convert a ``localization_languages`` row into the API model."""
    return LanguageResponse(
        id=row.id,
        code=row.code,
        name=row.name,
        native_name=row.native_name,
        enabled=row.enabled,
        is_default=row.is_default,
        metadata=row.meta_data or {},
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
    )


def _row_to_resource(row: LocalizationResourceDB) -> ResourceResponse:
    """Convert a ``localization_resources`` row into the API model."""
    return ResourceResponse(
        id=row.id,
        language_code=row.language_code,
        namespace=row.namespace,
        key=row.key,
        value=row.value,
        context=row.context,
        metadata=row.meta_data or {},
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
    )


def _seed_default_languages(db) -> None:
    """Bootstrap the first-run default language set (durable)."""
    defaults = [
        {
            "id": str(uuid4()),
            "code": "zh-CN",
            "name": "Chinese (Simplified)",
            "native_name": "简体中文",
            "enabled": True,
            "is_default": True,
            "meta_data": {"region": "CN", "locale": "zh_CN.UTF-8"},
        },
        {
            "id": str(uuid4()),
            "code": "en-US",
            "name": "English (United States)",
            "native_name": "English",
            "enabled": True,
            "is_default": False,
            "meta_data": {"region": "US", "locale": "en_US.UTF-8"},
        },
    ]
    for spec in defaults:
        db.add(LocalizationLanguageDB(**spec))
    db.commit()


def _initialize_default_data():
    """Initialize first-run adapter defaults (real localisation adapters)."""
    if not _adapters:
        default_adapters = [
            {
                "id": str(uuid4()),
                "name": "Default Date Adapter",
                "type": "date",
                "config": {"format": "YYYY-MM-DD"},
                "enabled": True,
                "priority": 10,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "id": str(uuid4()),
                "name": "Default Number Adapter",
                "type": "number",
                "config": {"decimal_separator": ".", "thousands_separator": ","},
                "enabled": True,
                "priority": 10,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        ]
        for adapter in default_adapters:
            _adapters[adapter["id"]] = adapter


_initialize_default_data()


# Language Endpoints
@router.get("/languages", response_model=List[LanguageResponse], summary="Get all languages")
async def get_languages(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    search: Optional[str] = Query(None, description="Search by name or code"),
):
    """
    Get all languages with optional filtering

    Args:
        enabled: Filter by enabled status
        search: Search by name or code

    Returns:
        List of languages
    """
    try:
        db = SessionLocal()
        try:
            if db.query(LocalizationLanguageDB).count() == 0:
                _seed_default_languages(db)

            query = db.query(LocalizationLanguageDB)
            if enabled is not None:
                query = query.filter(LocalizationLanguageDB.enabled == enabled)

            results = [_row_to_language(row) for row in query.all()]

            if search:
                search_lower = search.lower()
                results = [
                    lang
                    for lang in results
                    if search_lower in lang.name.lower() or search_lower in lang.code.lower()
                ]

            return results
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting languages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/languages", response_model=LanguageResponse, summary="Create a new language")
async def create_language(language: LanguageCreate):
    """
    Create a new language

    Args:
        language: Language data

    Returns:
        Created language
    """
    try:
        db = SessionLocal()
        try:
            # Check if language code already exists
            if (
                db.query(LocalizationLanguageDB)
                .filter(LocalizationLanguageDB.code == language.code)
                .first()
            ):
                raise HTTPException(
                    status_code=400, detail=f"Language code '{language.code}' already exists"
                )

            # If setting as default, remove default from others
            if language.is_default:
                db.query(LocalizationLanguageDB).update({LocalizationLanguageDB.is_default: False})

            row = LocalizationLanguageDB(
                id=str(uuid4()),
                code=language.code,
                name=language.name,
                native_name=language.native_name,
                enabled=language.enabled,
                is_default=language.is_default,
                meta_data=language.metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            logger.info(f"Created language: {language.code}")
            return _row_to_language(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating language: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/languages/{language_id}", response_model=LanguageResponse, summary="Get a language by ID"
)
async def get_language(language_id: str):
    """
    Get a language by ID

    Args:
        language_id: Language ID

    Returns:
        Language data
    """
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(LocalizationLanguageDB)
                .filter(LocalizationLanguageDB.id == language_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail="Language not found")
            return _row_to_language(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting language: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/languages/{language_id}", response_model=LanguageResponse, summary="Update a language"
)
async def update_language(language_id: str, language: LanguageUpdate):
    """
    Update a language

    Args:
        language_id: Language ID
        language: Updated language data

    Returns:
        Updated language
    """
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(LocalizationLanguageDB)
                .filter(LocalizationLanguageDB.id == language_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail="Language not found")

            if language.name is not None:
                row.name = language.name
            if language.native_name is not None:
                row.native_name = language.native_name
            if language.enabled is not None:
                row.enabled = language.enabled
            if language.is_default is not None:
                if language.is_default:
                    db.query(LocalizationLanguageDB).filter(
                        LocalizationLanguageDB.id != language_id
                    ).update({LocalizationLanguageDB.is_default: False})
                row.is_default = language.is_default
            if language.metadata is not None:
                row.meta_data = language.metadata

            db.commit()
            db.refresh(row)
            logger.info(f"Updated language: {language_id}")
            return _row_to_language(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating language: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/languages/{language_id}", summary="Delete a language")
async def delete_language(language_id: str):
    """
    Delete a language

    Args:
        language_id: Language ID

    Returns:
        Deletion result
    """
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(LocalizationLanguageDB)
                .filter(LocalizationLanguageDB.id == language_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail="Language not found")

            # Check if it's the default language
            if row.is_default:
                raise HTTPException(status_code=400, detail="Cannot delete default language")

            db.delete(row)
            db.commit()
            logger.info(f"Deleted language: {language_id}")
            return {"status": "success", "message": "Language deleted successfully"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting language: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Resource Endpoints
@router.get("/resources", response_model=List[ResourceResponse], summary="Get all resources")
async def get_resources(
    language_code: Optional[str] = Query(None, description="Filter by language code"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
):
    """
    Get all resources with optional filtering

    Args:
        language_code: Filter by language code
        namespace: Filter by namespace

    Returns:
        List of resources
    """
    try:
        db = SessionLocal()
        try:
            query = db.query(LocalizationResourceDB)
            if language_code:
                query = query.filter(LocalizationResourceDB.language_code == language_code)
            if namespace:
                query = query.filter(LocalizationResourceDB.namespace == namespace)
            return [_row_to_resource(row) for row in query.all()]
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources", response_model=ResourceResponse, summary="Create a new resource")
async def create_resource(resource: ResourceCreate):
    """
    Create a new resource

    Args:
        resource: Resource data

    Returns:
        Created resource
    """
    try:
        db = SessionLocal()
        try:
            # Check if resource key already exists for this language/namespace
            duplicate = (
                db.query(LocalizationResourceDB)
                .filter(
                    LocalizationResourceDB.language_code == resource.language_code,
                    LocalizationResourceDB.namespace == resource.namespace,
                    LocalizationResourceDB.key == resource.key,
                )
                .first()
            )
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Resource key '{resource.key}' already exists for language "
                        f"'{resource.language_code}' and namespace '{resource.namespace}'"
                    ),
                )

            row = LocalizationResourceDB(
                id=str(uuid4()),
                language_code=resource.language_code,
                namespace=resource.namespace,
                key=resource.key,
                value=resource.value,
                context=resource.context,
                meta_data=resource.metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            logger.info(f"Created resource: {resource.key}")
            return _row_to_resource(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/resources/{resource_id}", response_model=ResourceResponse, summary="Get a resource by ID"
)
async def get_resource(resource_id: str):
    """
    Get a resource by ID

    Args:
        resource_id: Resource ID

    Returns:
        Resource data
    """
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(LocalizationResourceDB)
                .filter(LocalizationResourceDB.id == resource_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail="Resource not found")
            return _row_to_resource(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/resources/{resource_id}", response_model=ResourceResponse, summary="Update a resource"
)
async def update_resource(resource_id: str, resource: ResourceUpdate):
    """
    Update a resource

    Args:
        resource_id: Resource ID
        resource: Updated resource data

    Returns:
        Updated resource
    """
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(LocalizationResourceDB)
                .filter(LocalizationResourceDB.id == resource_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail="Resource not found")

            if resource.value is not None:
                row.value = resource.value
            if resource.context is not None:
                row.context = resource.context
            if resource.metadata is not None:
                row.meta_data = resource.metadata

            db.commit()
            db.refresh(row)
            logger.info(f"Updated resource: {resource_id}")
            return _row_to_resource(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/resources/{resource_id}", summary="Delete a resource")
async def delete_resource(resource_id: str):
    """
    Delete a resource

    Args:
        resource_id: Resource ID

    Returns:
        Deletion result
    """
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(LocalizationResourceDB)
                .filter(LocalizationResourceDB.id == resource_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail="Resource not found")

            db.delete(row)
            db.commit()
            logger.info(f"Deleted resource: {resource_id}")
            return {"status": "success", "message": "Resource deleted successfully"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Translation Endpoints
@router.get(
    "/translations", response_model=List[TranslationResponse], summary="Get all translations"
)
async def get_translations(
    source_language: Optional[str] = Query(None, description="Filter by source language"),
    target_language: Optional[str] = Query(None, description="Filter by target language"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Get all translations with optional filtering

    Args:
        source_language: Filter by source language
        target_language: Filter by target language
        status: Filter by status

    Returns:
        List of translations
    """
    try:
        translations = list(_translations.values())

        if source_language:
            translations = [t for t in translations if t["source_language"] == source_language]

        if target_language:
            translations = [t for t in translations if t["target_language"] == target_language]

        if status:
            translations = [t for t in translations if t["status"] == status]

        return [TranslationResponse(**t) for t in translations]
    except Exception as e:
        logger.error(f"Error getting translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/translations", response_model=TranslationResponse, summary="Create a new translation"
)
async def create_translation(translation: TranslationCreate):
    """
    Create a new translation

    Args:
        translation: Translation data

    Returns:
        Created translation
    """
    try:
        new_translation = {
            "id": str(uuid4()),
            "source_language": translation.source_language,
            "target_language": translation.target_language,
            "namespace": translation.namespace,
            "key": translation.key,
            "source_value": translation.source_value,
            "target_value": translation.target_value,
            "status": translation.status,
            "metadata": translation.metadata,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        _translations[new_translation["id"]] = new_translation

        logger.info(f"Created translation: {translation.key}")
        return TranslationResponse(**new_translation)
    except Exception as e:
        logger.error(f"Error creating translation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Adapter Endpoints
@router.get("/adapters", response_model=List[AdapterResponse], summary="Get all adapters")
async def get_adapters(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    type: Optional[str] = Query(None, description="Filter by adapter type"),
):
    """
    Get all adapters with optional filtering

    Args:
        enabled: Filter by enabled status
        type: Filter by adapter type

    Returns:
        List of adapters
    """
    try:
        adapters = list(_adapters.values())

        if enabled is not None:
            adapters = [a for a in adapters if a["enabled"] == enabled]

        if type:
            adapters = [a for a in adapters if a["type"] == type]

        # Sort by priority
        adapters.sort(key=lambda x: x["priority"], reverse=True)

        return [AdapterResponse(**a) for a in adapters]
    except Exception as e:
        logger.error(f"Error getting adapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adapters", response_model=AdapterResponse, summary="Create a new adapter")
async def create_adapter(adapter: AdapterCreate):
    """
    Create a new adapter

    Args:
        adapter: Adapter data

    Returns:
        Created adapter
    """
    try:
        new_adapter = {
            "id": str(uuid4()),
            "name": adapter.name,
            "type": adapter.type,
            "config": adapter.config,
            "enabled": adapter.enabled,
            "priority": adapter.priority,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        _adapters[new_adapter["id"]] = new_adapter

        logger.info(f"Created adapter: {adapter.name}")
        return AdapterResponse(**new_adapter)
    except Exception as e:
        logger.error(f"Error creating adapter: {e}")
        raise HTTPException(status_code=500, detail=str(e))
