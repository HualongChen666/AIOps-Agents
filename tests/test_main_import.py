# -*- coding: utf-8 -*-
"""Smoke test that imports the main application to exercise top-level code of active core/api modules."""  # noqa: E501


def test_import_main() -> None:
    """Importing main should load all routers and core modules without side-effect failures."""
    import main  # noqa: F401

    assert hasattr(main, "app")
