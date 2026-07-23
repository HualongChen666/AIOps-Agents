# -*- coding: utf-8 -*-
"""Vectorization pipeline based on sentence‑transformers.

The pipeline provides a simple, thread‑safe interface for converting
plain text (documents or queries) into dense embeddings that can be used
with the Qdrant vector store (or any other similarity engine).

Key features
------------
* **Singleton model loading** – the heavy ``SentenceTransformer`` model is
  instantiated only once per process.
* **Configurable model** – the model name can be overridden via the
  ``SENTENCE_TRANSFORMERS_MODEL`` environment variable.  A sensible
  default (``all-MiniLM-L6-v2``) is provided, which balances quality and
  speed.
* **Batch encoding** – ``embed_documents`` accepts an iterable of strings
  and returns a ``list`` of ``list[float]`` embeddings.  Internally the
  underlying model performs efficient batch processing.
* **Query encoding** – ``embed_query`` is a thin wrapper around the batch
  encoder for a single query string.
* **Error handling** – any failure to load the model (e.g. missing
  ``sentence_transformers`` package) raises a clear ``RuntimeError`` with
  instructions for installing the optional dependency.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, List

# The project already uses Loguru for logging, but importing the standard
# library logger keeps this module lightweight and avoids circular imports.
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# ``SENTENCE_TRANSFORMERS_MODEL`` can be set in ``.env`` or the runtime
# environment.  The default model works well for English and many other
# languages while keeping the memory footprint below ~500 MiB.
_SENTENCE_MODEL_NAME: str = os.getenv(
    "SENTENCE_TRANSFORMERS_MODEL",
    "all-MiniLM-L6-v2",
)

# ---------------------------------------------------------------------------
# Lazy singleton loader for the SentenceTransformer model
# ---------------------------------------------------------------------------
_model_instance = None


def _load_model() -> Any:
    """Load the SentenceTransformer model lazily.

    The import of ``sentence_transformers`` is optional – the rest of the
    project (e.g. FastAPI routes) can operate without it.  When the model
    cannot be imported we raise a ``RuntimeError`` with a helpful error
    message so that developers know how to install the extra dependency.
    """
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for the vector pipeline. "
            "Install it via 'pip install sentence-transformers'."
        ) from exc

    _logger.info("Loading SentenceTransformer model: %s", _SENTENCE_MODEL_NAME)
    _model_instance = SentenceTransformer(_SENTENCE_MODEL_NAME)
    _logger.info("SentenceTransformer model loaded successfully.")
    return _model_instance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def embed_documents(texts: Iterable[str]) -> List[List[float]]:
    """Encode a batch of documents.

    Parameters
    ----------
    texts: Iterable[str]
        The raw document strings.

    Returns
    -------
    List[List[float]]
        A list of embedding vectors (each vector is a ``list`` of ``float``).
    """
    model = _load_model()
    # ``model.encode`` accepts a list/iterable and returns a NumPy array.
    # We convert each row to a plain Python list for JSON‑serialisation.
    embeddings = model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
    result: List[List[float]] = embeddings.tolist()
    return result


def embed_query(query: str) -> List[float]:
    """Encode a single search query.

    This is a convenience wrapper around :func:`embed_documents` for the
    common case where only one query string needs to be embedded.
    """
    return embed_documents([query])[0]


# ---------------------------------------------------------------------------
# Optional utility for debugging – prints model dimension.
# ---------------------------------------------------------------------------
def model_dimension() -> int:
    """Return the dimensionality of the underlying embedding model.

    Useful for validating that Qdrant collections are created with the
    correct ``vector_size``.
    """
    model = _load_model()
    result: int = model.get_sentence_embedding_dimension()
    return result


# ---------------------------------------------------------------------------
# End of file
# ---------------------------------------------------------------------------
