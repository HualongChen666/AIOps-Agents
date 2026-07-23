# -*- coding: utf-8 -*-
"""
Service Worker Configuration
Service Worker配置

为前端提供Service Worker配置和离线支持策略。
"""

import logging

logger = logging.getLogger(__name__)

SERVICE_WORKER_CONFIG = {
    "version": "1.0.0",
    "cache_name": "aiops-cache-v1",
    "cache_urls": ["/", "/api/v1/health", "/static/css/main.css", "/static/js/main.js"],
    "offline_fallback": "/offline.html",
    "network_first_patterns": ["/api/v1/*"],
    "cache_first_patterns": ["/static/*", "/images/*"],
    "skip_waiting": True,
    "clients_claim": True,
}


def get_service_worker_script() -> str:
    """
    生成Service Worker脚本

    Returns:
        Service Worker JavaScript代码
    """
    return f"""
const CACHE_NAME = '{SERVICE_WORKER_CONFIG["cache_name"]}';
const CACHE_URLS = {SERVICE_WORKER_CONFIG["cache_urls"]};

self.addEventListener('install', (event) => {{
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(CACHE_URLS))
            .then(() => self.skipWaiting())
    );
}});

self.addEventListener('activate', (event) => {{
    event.waitUntil(
        caches.keys().then((cacheNames) => {{
            return Promise.all(
                cacheNames.map((cacheName) => {{
                    if (cacheName !== CACHE_NAME) {{
                        return caches.delete(cacheName);
                    }}
                }})
            );
        }}).then(() => self.clients.claim())
    );
}});

self.addEventListener('fetch', (event) => {{
    event.respondWith(
        caches.match(event.request).then((response) => {{
            if (response) {{
                return response;
            }}
            return fetch(event.request);
        }})
    );
}});
"""


def get_service_worker_registration_script() -> str:
    """
    生成Service Worker注册脚本

    Returns:
        注册JavaScript代码
    """
    return """
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('ServiceWorker registration successful');
            })
            .catch((error) => {
                console.log('ServiceWorker registration failed:', error);
            });
    });
}
"""
