# -*- coding: utf-8 -*-
"""
Model Inference Service Configuration
======================================

Configuration for AI model inference services based on existing LLM router infrastructure.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class ModelInferenceConfig:
    """Model inference service configuration"""

    # Sentence Transformers for embedding
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    sentence_transformer_device: str = "cpu"

    # LLM Provider Configuration
    llm_provider: str = "openai"  # openai, anthropic, local
    llm_model: str = "gpt-3.5-turbo"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1000

    # Rate Limiting
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # Batch Processing
    batch_size: int = 10
    batch_timeout_seconds: int = 30

    # Security
    enable_content_moderation: bool = True
    max_input_length: int = 10000

    # Performance
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600


def get_inference_config() -> ModelInferenceConfig:
    """
    Get model inference configuration from environment or defaults.

    Returns:
        ModelInferenceConfig with loaded configuration
    """
    config = ModelInferenceConfig()

    # Load from environment variables
    config.sentence_transformer_model = os.getenv(
        "SENTENCE_TRANSFORMER_MODEL",
        config.sentence_transformer_model
    )
    config.sentence_transformer_device = os.getenv(
        "SENTENCE_TRANSFORMER_DEVICE",
        config.sentence_transformer_device
    )

    config.llm_provider = os.getenv(
        "LLM_PROVIDER",
        config.llm_provider
    )
    config.llm_model = os.getenv(
        "LLM_MODEL",
        config.llm_model
    )
    config.llm_temperature = float(os.getenv(
        "LLM_TEMPERATURE",
        str(config.llm_temperature)
    ))
    config.llm_max_tokens = int(os.getenv(
        "LLM_MAX_TOKENS",
        str(config.llm_max_tokens)
    ))

    config.requests_per_minute = int(os.getenv(
        "INFERENCE_RPM_LIMIT",
        str(config.requests_per_minute)
    ))
    config.requests_per_hour = int(os.getenv(
        "INFERENCE_RPH_LIMIT",
        str(config.requests_per_hour)
    ))

    config.batch_size = int(os.getenv(
        "INFERENCE_BATCH_SIZE",
        str(config.batch_size)
    ))
    config.batch_timeout_seconds = int(os.getenv(
        "INFERENCE_BATCH_TIMEOUT",
        str(config.batch_timeout_seconds)
    ))

    config.enable_content_moderation = os.getenv(
        "ENABLE_CONTENT_MODERATION",
        str(config.enable_content_moderation)
    ).lower() == "true"

    config.max_input_length = int(os.getenv(
        "MAX_INPUT_LENGTH",
        str(config.max_input_length)
    ))

    config.enable_caching = os.getenv(
        "ENABLE_INFERENCE_CACHE",
        str(config.enable_caching)
    ).lower() == "true"

    config.cache_ttl_seconds = int(os.getenv(
        "INFERENCE_CACHE_TTL",
        str(config.cache_ttl_seconds)
    ))

    return config


# Global configuration instance
_inference_config: Optional[ModelInferenceConfig] = None


def get_inference_config_singleton() -> ModelInferenceConfig:
    """Get or create global inference configuration singleton"""
    global _inference_config
    if _inference_config is None:
        _inference_config = get_inference_config()
    return _inference_config
