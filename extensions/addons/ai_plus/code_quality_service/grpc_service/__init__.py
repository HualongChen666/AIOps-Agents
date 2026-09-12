"""
gRPC module for Code Quality Service
"""

try:
    from .server import CodeQualityServiceImpl, serve, GRPC_AVAILABLE
    from .client import CodeQualityClient, CodeQualityClientContext
    
    __all__ = [
        'CodeQualityServiceImpl',
        'serve',
        'CodeQualityClient',
        'CodeQualityClientContext',
        'GRPC_AVAILABLE',
    ]
except ImportError:
    GRPC_AVAILABLE = False
    __all__ = ['GRPC_AVAILABLE']
