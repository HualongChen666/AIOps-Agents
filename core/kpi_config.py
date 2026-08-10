# -*- coding: utf-8 -*-
"""Backend-driven KPI configuration persistence (JSON file)."""

import json
import os
import threading
import uuid
from datetime import datetime
from typing import Any, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_KPI_CONFIG_PATH = os.path.join(_DATA_DIR, "kpi_config.json")

os.makedirs(_DATA_DIR, exist_ok=True)
_lock = threading.Lock()


def _default_configs() -> list[dict[str, Any]]:
    return [
        {"id": str(uuid.uuid4()), "name": "告警数量", "endpoint": "summary", "field_path": "total_alerts",
         "target": 50, "unit": "个", "visible": True, "order": 0, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "自愈成功率", "endpoint": "summary", "field_path": "heal_rate",
         "target": 85, "unit": "%", "visible": True, "order": 1, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "MTTD", "endpoint": "summary", "field_path": "mttd_min", "target": 30,
         "unit": "min", "visible": True, "order": 2, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "RCA准确率", "endpoint": "summary", "field_path": "rca_accuracy",
         "target": 85, "unit": "%", "visible": True, "order": 3, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "CPU 使用率", "endpoint": "snapshot", "field_path": "cpu.usage_percent",
         "target": 80, "unit": "%", "visible": True, "order": 4, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "内存使用率", "endpoint": "snapshot", "field_path": "memory.usage_percent",
         "target": 80, "unit": "%", "visible": True, "order": 5, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "磁盘使用率", "endpoint": "snapshot", "field_path": "disk.usage_percent",
         "target": 80, "unit": "%", "visible": True, "order": 6, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "决策准确率", "endpoint": "agent/decision-accuracy", "field_path": "accuracy",
         "target": 90, "unit": "%", "visible": True, "order": 7, "created_at": datetime.utcnow().isoformat()},
        {"id": str(uuid.uuid4()), "name": "反馈准确率", "endpoint": "agent/feedback-accuracy", "field_path": "accuracy",
         "target": 90, "unit": "%", "visible": True, "order": 8, "created_at": datetime.utcnow().isoformat()},
    ]


def _ensure_defaults() -> None:
    if not os.path.exists(_KPI_CONFIG_PATH):
        with _lock:
            if not os.path.exists(_KPI_CONFIG_PATH):
                _write_configs(_default_configs())


def _read_configs() -> list[dict[str, Any]]:
    _ensure_defaults()
    with open(_KPI_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_configs(configs: list[dict[str, Any]]) -> None:
    with _lock:
        with open(_KPI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(configs, f, ensure_ascii=False, indent=2)


def list_kpi_configs() -> list[dict[str, Any]]:
    configs = _read_configs()
    return sorted(configs, key=lambda x: x.get("order", 0))


def get_kpi_config(config_id: str) -> Optional[dict[str, Any]]:
    configs = _read_configs()
    for c in configs:
        if c.get("id") == config_id:
            return c
    return None


def create_kpi_config(data: dict[str, Any]) -> dict[str, Any]:
    configs = _read_configs()
    new_config: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": data.get("name", ""),
        "endpoint": data.get("endpoint", "summary"),
        "field_path": data.get("field_path", ""),
        "target": float(data.get("target", 0)),
        "unit": data.get("unit", ""),
        "visible": bool(data.get("visible", True)),
        "order": int(data.get("order", len(configs))),
        "created_at": datetime.utcnow().isoformat(),
    }
    configs.append(new_config)
    _write_configs(configs)
    return new_config


def update_kpi_config(config_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    configs = _read_configs()
    for c in configs:
        if c.get("id") == config_id:
            c["name"] = data.get("name", c.get("name"))
            c["endpoint"] = data.get("endpoint", c.get("endpoint"))
            c["field_path"] = data.get("field_path", c.get("field_path"))
            c["target"] = float(data.get("target", c.get("target", 0)))
            c["unit"] = data.get("unit", c.get("unit"))
            c["visible"] = data.get("visible", c.get("visible"))
            if "order" in data:
                c["order"] = int(data["order"])
            _write_configs(configs)
            return c
    return None


def delete_kpi_config(config_id: str) -> bool:
    configs = _read_configs()
    new_configs = [c for c in configs if c.get("id") != config_id]
    if len(new_configs) == len(configs):
        return False
    _write_configs(new_configs)
    return True


def resolve_field(data: dict[str, Any], field_path: str) -> Any:
    parts = field_path.split(".") if field_path else []
    value: Any = data
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value
