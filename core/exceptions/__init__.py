# -*- coding: utf-8 -*-
"""
异常类模块

导出所有自定义异常类。
"""

from .base import AIOpsBaseException, ErrorCategory, ErrorSeverity
from .business import (
    BusinessException,
    BusinessLogicException,
    QuotaExceededException,
    ResourceNotFoundException,
    StateInvalidException,
    ValidationException,
    WorkflowException,
)
from .critical import CriticalException, DataCorruptionException, SystemFatalException
from .security import (
    AuthenticationException,
    AuthorizationException,
    PermissionDeniedException,
    SecurityException,
)
from .system import (
    CacheException,
    ConfigurationException,
    DatabaseException,
    NetworkException,
    ResourceException,
    SystemException,
    VersionMismatchException,
)
from .third_party import (
    AIModelException,
    ExternalServiceException,
    IntegrationException,
    ThirdPartyException,
)

__all__ = [
    # Base
    "AIOpsBaseException",
    "ErrorSeverity",
    "ErrorCategory",
    # Business
    "BusinessException",
    "ValidationException",
    "ResourceNotFoundException",
    "BusinessLogicException",
    "StateInvalidException",
    "WorkflowException",
    "QuotaExceededException",
    # System
    "SystemException",
    "DatabaseException",
    "NetworkException",
    "CacheException",
    "ConfigurationException",
    "ResourceException",
    "VersionMismatchException",
    # Security
    "SecurityException",
    "AuthenticationException",
    "AuthorizationException",
    "PermissionDeniedException",
    # Third Party
    "ThirdPartyException",
    "ExternalServiceException",
    "AIModelException",
    "IntegrationException",
    # Critical
    "CriticalException",
    "SystemFatalException",
    "DataCorruptionException",
]
