# -*- coding: utf-8 -*-
"""
安全头配置中间件
配置HTTP安全头以增强API安全性
"""

import logging
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy (basic)
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
            
            # Strict Transport Security (only for HTTPS)
            # "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """处理请求并添加安全头"""
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # Add custom security headers
        response.headers["X-API-Version"] = "1.0"
        response.headers["X-Request-ID"] = self._generate_request_id(request)
        
        return response
    
    def _generate_request_id(self, request: Request) -> str:
        """生成请求ID"""
        import uuid
        return str(uuid.uuid4())


def add_security_headers(app: FastAPI):
    """添加安全头中间件到FastAPI应用"""
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware added")


class SecurityHeadersConfig:
    """安全头配置类"""
    
    # Default security headers
    DEFAULT_HEADERS = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    
    # CORS headers (for development)
    CORS_HEADERS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
    }
    
    @classmethod
    def get_headers(cls, include_cors: bool = False) -> dict:
        """获取安全头配置"""
        headers = cls.DEFAULT_HEADERS.copy()
        if include_cors:
            headers.update(cls.CORS_HEADERS)
        return headers
    
    @classmethod
    def get_csp_policy(cls, custom_policy: Optional[str] = None) -> str:
        """获取内容安全策略"""
        if custom_policy:
            return custom_policy
        return cls.DEFAULT_HEADERS["Content-Security-Policy"]
