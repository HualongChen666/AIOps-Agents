# -*- coding: utf-8 -*-
"""Compliance report templates and data (task 28.4)."""

from __future__ import annotations

from typing import Any, Dict


class ComplianceTemplate:
    """Compliance report template definition."""

    TEMPLATES: Dict[str, str] = {
        "soc2": (
            "SOC2 compliance report for {{ tenant_id }} " "from {{ start_time }} to {{ end_time }}"
        ),
        "gdpr": "GDPR audit report for {{ tenant_id }} with {{ total }} events",
    }

    @classmethod
    def render(cls, name: str, context: Dict[str, Any]) -> str:
        template = cls.TEMPLATES.get(name, cls.TEMPLATES["soc2"])
        for key, value in context.items():
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        return template
