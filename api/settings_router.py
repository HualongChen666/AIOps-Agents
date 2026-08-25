# -*- coding: utf-8 -*-
"""Settings API router backed by a JSON file in data/."""

import json
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/settings", tags=["settings"])

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_SETTINGS_FILE = os.path.join(_DATA_DIR, "settings.json")


class SettingsUpdate(BaseModel):
    system_name: str | None = Field(default=None, alias="system_name")
    timezone: str | None = Field(default=None, alias="timezone")
    language: str | None = Field(default=None, alias="language")
    data_retention: str | None = Field(default=None, alias="data_retention")

    model_config = {"populate_by_name": True}


def _load_settings() -> Dict[str, Any]:
    if not os.path.exists(_SETTINGS_FILE):
        return {}
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.warning(f"Failed to load settings: {e}")
    return {}


def _save_settings(settings: Dict[str, Any]) -> None:
    import stat

    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        # Set restrictive permissions for settings file (600 - owner read/write only)
        try:
            os.chmod(_SETTINGS_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            # chmod may fail on Windows or non-Unix systems
            pass
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail="保存设置失败")


@router.get("/", summary="获取系统设置")
async def get_settings() -> Dict[str, Any]:
    return {"settings": _load_settings()}


@router.put("/", summary="更新系统设置")
async def update_settings(payload: SettingsUpdate) -> Dict[str, Any]:
    settings = _load_settings()
    update = payload.model_dump(by_alias=True, exclude_unset=True)
    settings.update({k: v for k, v in update.items() if v is not None})
    _save_settings(settings)
    return {"settings": settings}
