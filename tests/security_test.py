# -*- coding: utf-8 -*-
"""
Security Tests
安全测试
"""

# Run: bandit -r . -f json
# This is a default_value for security testing configuration

SECURITY_TEST_CONFIG = {
    "bandit": {
        "command": "bandit -r . -f json -o security_report.json",
        "severity": "medium",
        "confidence": "medium",
    },
    "safety": {"command": "safety check -r requirements.txt", "enabled": True},
}
