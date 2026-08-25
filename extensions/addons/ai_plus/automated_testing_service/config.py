# -*- coding: utf-8 -*-
"""Configuration for Automated Testing Service."""

import os
from typing import Optional


class Config:
    """Configuration settings for the service."""

    # Service settings
    SERVICE_NAME: str = "automated_testing_service"
    PORT: int = int(os.getenv("PORT", "8001"))
    HOST: str = os.getenv("HOST", "127.0.0.1")

    # gRPC settings
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))
    GRPC_HOST: str = os.getenv("GRPC_HOST", "127.0.0.1")

    # Test execution settings
    DEFAULT_TEST_TIMEOUT: int = int(os.getenv("TEST_TIMEOUT", "300"))  # 5 minutes
    MAX_CONCURRENT_TESTS: int = int(os.getenv("MAX_CONCURRENT_TESTS", "4"))
    TEST_RESULTS_DIR: str = os.getenv("TEST_RESULTS_DIR", "./test_results")
    COVERAGE_DIR: str = os.getenv("COVERAGE_DIR", "./coverage")

    # Scheduler settings
    SCHEDULER_CHECK_INTERVAL: int = int(os.getenv("SCHEDULER_CHECK_INTERVAL", "60"))  # seconds

    # Framework settings
    SUPPORTED_FRAMEWORKS: list = ["pytest", "unittest"]
    DEFAULT_FRAMEWORK: str = "pytest"

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings."""
        if cls.PORT < 1 or cls.PORT > 65535:
            raise ValueError(f"Invalid PORT: {cls.PORT}")
        if cls.GRPC_PORT < 1 or cls.GRPC_PORT > 65535:
            raise ValueError(f"Invalid GRPC_PORT: {cls.GRPC_PORT}")
        if cls.DEFAULT_TEST_TIMEOUT <= 0:
            raise ValueError(f"Invalid TEST_TIMEOUT: {cls.DEFAULT_TEST_TIMEOUT}")
        if cls.MAX_CONCURRENT_TESTS <= 0:
            raise ValueError(f"Invalid MAX_CONCURRENT_TESTS: {cls.MAX_CONCURRENT_TESTS}")
        if cls.DEFAULT_FRAMEWORK not in cls.SUPPORTED_FRAMEWORKS:
            raise ValueError(f"Unsupported framework: {cls.DEFAULT_FRAMEWORK}")
