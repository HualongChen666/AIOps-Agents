# -*- coding: utf-8 -*-
"""Smoke tests for the extensions/addons plugin loader."""

import pytest

import extensions


@pytest.mark.timeout(120)
def test_load_all_addons():
    """All addon files must be discovered and at least partially loaded."""
    summary = extensions.load_all_addons()
    assert summary["total"] > 0
    assert isinstance(summary["loaded"], list)
    assert isinstance(summary["failed"], list)
    # Expect that some files load successfully; failures are recorded, not fatal.
    assert len(summary["loaded"]) > 0, summary["failed"][:5]


def test_list_addons():
    addons = extensions.list_addons()
    assert isinstance(addons, list)
    assert len(addons) > 0


def test_get_addon_after_load():
    summary = extensions.load_all_addons()
    if summary["loaded"]:
        module = extensions.get_addon(summary["loaded"][0])
        assert module is not None
