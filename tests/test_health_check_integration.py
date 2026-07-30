# -*- coding: utf-8 -*-
# tests/test_health_check_integration.py
import sys

import pytest

from core.health_check import perform_health_checks

sys.path.insert(0, "C://AIOps_Agent_bak")

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_checks():
    # Test health checks
    health_status = await perform_health_checks()
    assert health_status is not None
    assert "status" in health_status
