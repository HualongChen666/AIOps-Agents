# -*- coding: utf-8 -*-
"""Tests for open-source community artifacts."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "relative",
    [
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "LICENSE",
        "docs/sphinx/conf.py",
        "docs/sphinx/index.rst",
        "docs/sphinx/Makefile",
        "docs/sphinx/make.bat",
        "docs/open_source/README.md",
    ],
)
def test_community_artifacts_exist(relative: str) -> None:
    """Verify each expected open-source artifact exists."""
    path = ROOT / relative
    assert path.exists(), f"Missing artifact: {relative}"
    assert path.read_text(encoding="utf-8").strip()
