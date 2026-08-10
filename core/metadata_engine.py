# -*- coding: utf-8 -*-
# core/metadata_engine.py
# ------------------------------------------------------------
# 元数据 & 数据血缘（DataHub / Amundsen） 简易包装。
# 本项目仅需要向外提供「登记数据集、服务、血缘」的 API。
# 为了在 CI 环境不强依赖大型元数据系统，所有实现均为
# **安全懒加载**：如果对应客户端库未安装或连接不可用，则仅记录日志
# 并返回占位对象。
# ------------------------------------------------------------

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from config import DATAHUB_REST_URL

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Lazy imports – DataHub and Amundsen clients are optional.
# -----------------------------------------------------------------
try:
    from datahub.emitter.mce_builder import make_dataset_urn
    from datahub.emitter.rest_emitter import DatahubRestEmitter
except Exception as exc:  # pragma: no cover
    logger.warning("DataHub client not available – %s", exc)
    DatahubRestEmitter = None  # type: ignore
    make_dataset_urn = None  # type: ignore

try:
    from amundsen_rds.models import Column as AmundsenColumn
    from amundsen_rds.models import Table as AmundsenTable
    from amundsen_rds.models import User as AmundsenUser

    # Assuming an Amundsen loader/producer – fallback imports.
except Exception as exc:  # pragma: no cover
    logger.warning("Amundsen client not available – %s", exc)
    AmundsenTable = None  # type: ignore
    AmundsenColumn = None  # type: ignore
    AmundsenUser = None  # type: ignore

# ------------------------------------------------------------
# Configuration – endpoints and credentials.
# ------------------------------------------------------------
DATAHUB_TOKEN = os.getenv("DATAHUB_TOKEN", "")
AMUNDSEN_METADATA_DB = os.getenv("AMUNDSEN_METADATA_DB", "amundsen")


# -----------------------------------------------------------------
# Helper to obtain a DataHub emitter (lazy singleton).
# -----------------------------------------------------------------
def _get_datahub_emitter() -> Any:
    if DatahubRestEmitter is None:
        logger.error("DataHub emitter requested but library missing.")
        return None
    return DatahubRestEmitter(
        server=DATAHUB_REST_URL,
        token=DATAHUB_TOKEN or None,
    )


# -----------------------------------------------------------------
# Public APIs – minimal set used by the rest of the project.
# -----------------------------------------------------------------
def register_dataset(
    platform: str,
    name: str,
    schema: str = "public",
    description: str = "",
    tags: List[str] | None = None,
) -> bool:
    """Register a dataset in DataHub (or Amundsen) if available.

    Returns ``True`` when the registration succeeds, ``False`` otherwise.
    """
    if make_dataset_urn is None:
        logger.warning("register_dataset called without DataHub support – %s.%s", platform, name)
        return False
    try:
        urn = make_dataset_urn(platform=platform, name=name, env="PROD")
        emitter = _get_datahub_emitter()
        if emitter is None:
            return False
        # Emit a simple dataset snapshot – in a real deployment you would
        # populate more fields (schema, owners, tags, etc.).
        from datahub.emitter.mce_builder import DatasetPropertiesClass, DatasetSnapshot
        from datahub.metadata.schema_classes import CorpUserUrn, OwnerClass, OwnershipClass

        snapshot = DatasetSnapshot(
            urn=urn,
            aspects=[
                DatasetPropertiesClass(description=description, customProperties={}),
                OwnershipClass(
                    owners=[
                        OwnerClass(owner=CorpUserUrn("urn:li:corpUser:aiops"), type="DATAOWNER")
                    ]
                ),
            ],
        )
        emitter.emit(snapshot)
        logger.info("DataHub dataset registered: %s.%s", platform, name)
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to register dataset %s.%s in DataHub: %s", platform, name, exc)
        return False


def register_lineage(
    upstream: Dict[str, str],
    downstream: Dict[str, str],
    description: str = "",
) -> bool:
    """Register a simple lineage edge between two datasets.

    ``upstream`` and ``downstream`` are dicts with keys ``platform``, ``name``.
    """
    if make_dataset_urn is None:
        logger.warning("register_lineage called without DataHub support.")
        return False
    try:
        upstream_urn = make_dataset_urn(
            platform=upstream["platform"], name=upstream["name"], env="PROD"
        )
        downstream_urn = make_dataset_urn(
            platform=downstream["platform"], name=downstream["name"], env="PROD"
        )
        emitter = _get_datahub_emitter()
        if emitter is None:
            return False
        from datahub.emitter.mce_builder import LineagePatchBuilder

        lineage = LineagePatchBuilder().add_edge(upstream_urn, downstream_urn).build()
        emitter.emit(lineage)
        logger.info("DataHub lineage registered: %s -> %s", upstream_urn, downstream_urn)
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to register lineage in DataHub: %s", exc)
        return False


# -----------------------------------------------------------------
# Amundsen fallback – in many CI environments Amundsen client is not
# installed, so we expose a no‑op API that logs calls.
# -----------------------------------------------------------------
def amundsen_register_table(table_name: str, schema: str = "public") -> bool:
    if AmundsenTable is None:
        logger.warning(
            "Amundsen client not available, skipping table registration for %s.%s",
            schema,
            table_name,
        )
        return True
    return True
