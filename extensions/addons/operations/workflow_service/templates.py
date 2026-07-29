# -*- coding: utf-8 -*-
"""Workflow template management based on Jinja2."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from services.workflow_service.metrics import WORKFLOW_TEMPLATE_RENDERS
from services.workflow_service.schemas import WorkflowTemplate


class TemplateManager:
    """Manage and render Jinja2-like workflow templates."""

    def __init__(self) -> None:
        self._templates: Dict[str, WorkflowTemplate] = {}

    async def register(self, template: WorkflowTemplate) -> str:
        self._templates[template.template_id] = template
        return template.template_id

    async def get(self, template_id: str) -> Optional[WorkflowTemplate]:
        return self._templates.get(template_id)

    async def list_templates(self, limit: int = 100) -> List[WorkflowTemplate]:
        return list(self._templates.values())[:limit]

    async def render(
        self,
        template_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render a template with parameters (lightweight Jinja2-like)."""
        start = time.perf_counter()
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        merged = {**(template.default_params or {}), **(params or {})}
        result = self._render_source(template.source, merged)
        WORKFLOW_TEMPLATE_RENDERS.labels(template_id=template_id).inc()
        logger.info(f"Rendered template {template_id} in {time.perf_counter() - start:.4f}s")
        return result

    def _render_source(self, source: str, params: Dict[str, Any]) -> str:
        """Simple variable substitution to avoid Jinja2 dependency."""
        result = source
        for key, value in params.items():
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
            result = pattern.sub(str(value), result)
        return result
