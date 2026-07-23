# -*- coding: utf-8 -*-
"""
Shared fixtures for core/ai tests.

Prevents external model downloads from sentence-transformers and
sentence-transformers CrossEncoder during tests.
"""

import pytest


@pytest.fixture(autouse=True)
def mock_sentence_transformers(monkeypatch):
    """Patch sentence-transformers classes to raise ImportError on instantiation."""
    try:
        import sentence_transformers
    except ImportError:
        return

    class _FailingModel:
        def __init__(self, *args, **kwargs):
            raise ImportError("sentence-transformers not available for tests")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", _FailingModel)
    monkeypatch.setattr(sentence_transformers, "CrossEncoder", _FailingModel)
