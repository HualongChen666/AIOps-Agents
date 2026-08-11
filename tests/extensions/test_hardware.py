# -*- coding: utf-8 -*-
"""Smoke tests for extensions/hardware_remediation."""

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "extensions.hardware_remediation",
        "extensions.hardware_remediation.ipmi_actions",
        "extensions.hardware_remediation.node_lifecycle",
        "extensions.hardware_remediation.raid_storcli",
        "extensions.hardware_remediation.redfish_actions",
        "extensions.hardware_remediation.smartctl",
        "extensions.hardware_remediation.ticket_integration",
    ],
)
def test_hardware_module_imports(module_name):
    __import__(module_name)
