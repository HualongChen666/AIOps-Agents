# -*- coding: utf-8 -*-
"""
sdk.py
------
RUM 建设 - SDK 集成模块。

功能：
- JavaScript SDK
- 移动端 SDK
- 性能数据采集
- 错误追踪
- 用户会话管理
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional  # noqa: F401

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ SDK 平台枚举
# ----------------------------------------------------------------------
class SDKPlatform(Enum):
    """SDK 平台"""

    WEB = "web"  # Web/JavaScript
    IOS = "ios"  # iOS
    ANDROID = "android"  # Android
    REACT_NATIVE = "react_native"  # React Native
    FLUTTER = "flutter"  # Flutter


# ----------------------------------------------------------------------
# 2️⃣ 性能指标
# ----------------------------------------------------------------------
@dataclass
class PerformanceMetric:
    """性能指标"""

    metric_name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


# ----------------------------------------------------------------------
# 3️⃣ 用户会话
# ----------------------------------------------------------------------
@dataclass
class UserSession:
    """用户会话"""

    session_id: str
    user_id: str
    platform: SDKPlatform
    app_version: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    page_views: int = 0
    errors: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """会话持续时间（秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "platform": self.platform.value,
            "app_version": self.app_version,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "page_views": self.page_views,
            "errors": self.errors,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 4️⃣ 页面加载事件
# ----------------------------------------------------------------------
@dataclass
class PageLoadEvent:
    """页面加载事件"""

    session_id: str
    page_url: str
    load_time: float  # 毫秒
    dom_content_loaded: float
    first_paint: float
    first_contentful_paint: float
    largest_contentful_paint: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "page_url": self.page_url,
            "load_time": self.load_time,
            "dom_content_loaded": self.dom_content_loaded,
            "first_paint": self.first_paint,
            "first_contentful_paint": self.first_contentful_paint,
            "largest_contentful_paint": self.largest_contentful_paint,
            "timestamp": self.timestamp.isoformat(),
        }


# ----------------------------------------------------------------------
# 5️⃣ 错误事件
# ----------------------------------------------------------------------
@dataclass
class ErrorEvent:
    """错误事件"""

    session_id: str
    error_type: str
    error_message: str
    stack_trace: str
    user_agent: str
    page_url: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "user_agent": self.user_agent,
            "page_url": self.page_url,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 6️⃣ SDK 配置
# ----------------------------------------------------------------------
@dataclass
class SDKConfig:
    """SDK 配置"""

    api_key: str
    api_endpoint: str
    sample_rate: float = 1.0  # 采样率
    enable_performance: bool = True
    enable_errors: bool = True
    enable_user_sessions: bool = True
    max_events_per_session: int = 100
    batch_size: int = 10
    flush_interval: int = 5000  # 毫秒

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "api_key": self.api_key,
            "api_endpoint": self.api_endpoint,
            "sample_rate": self.sample_rate,
            "enable_performance": self.enable_performance,
            "enable_errors": self.enable_errors,
            "enable_user_sessions": self.enable_user_sessions,
            "max_events_per_session": self.max_events_per_session,
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
        }


# ----------------------------------------------------------------------
# 7️⃣ RUM SDK 生成器
# ----------------------------------------------------------------------
class RUMSDKGenerator:
    """RUM SDK 生成器"""

    def __init__(self):
        self.sdk_templates = {
            SDKPlatform.WEB: self._generate_web_sdk,
            SDKPlatform.IOS: self._generate_ios_sdk,
            SDKPlatform.ANDROID: self._generate_android_sdk,
        }

    def generate_sdk(
        self,
        platform: SDKPlatform,
        config: SDKConfig,
    ) -> str:
        """
        生成 SDK 代码

        Parameters
        ----------
        platform : SDKPlatform
            平台
        config : SDKConfig
            配置

        Returns
        -------
        str
            SDK 代码
        """
        generator = self.sdk_templates.get(platform)
        if generator:
            return generator(config)
        else:
            return f"# SDK for {platform.value} not yet implemented"

    def _generate_web_sdk_class(self) -> str:
        """
        生成Web SDK类定义

        Returns:
            Web SDK类定义字符串
        """
        return """
    class AIOpsRUM {
        constructor(config) {
            this.config = config;
            this.sessionId = this.generateSessionId();
            this.events = [];
            this.sessionStartTime = Date.now();
            this.pageViews = 0;
            this.errors = 0;

            this.init();
        }

        generateSessionId() {
            return 'rum-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
        }

        init() {
            // 初始化性能监控
            if (this.config.enable_performance) {
                this.initPerformanceMonitoring();
            }

            // 初始化错误监控
            if (this.config.enable_errors) {
                this.initErrorMonitoring();
            }

            // 页面可见性变化
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    this.flush();
                }
            });

            // 定期刷新
            setInterval(() => this.flush(), this.config.flush_interval);
        }

        initPerformanceMonitoring() {
            // 监听页面加载
            window.addEventListener('load', () => {
                if (performance.timing) {
                    const timing = performance.timing;
                    const pageLoadEvent = {
                        sessionId: this.sessionId,
                        pageUrl: window.location.href,
                        loadTime: timing.loadEventEnd - timing.navigationStart,
                        domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                        firstPaint: timing.responseStart - timing.navigationStart,
                        firstContentfulPaint: timing.responseStart - timing.navigationStart,
                        largestContentfulPaint: timing.loadEventEnd - timing.navigationStart,
                        timestamp: new Date().toISOString()
                    };
                    this.track('page_load', pageLoadEvent);
                }
            });

            // 监听 Largest Contentful Paint
            if ('PerformanceObserver' in window) {
                const observer = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach(entry => {
                        this.track('lcp', {
                            value: entry.startTime,
                            timestamp: new Date().toISOString()
                        });
                    });
                });
                observer.observe({ type: 'largest-contentful-paint', buffered: true });
            }
        }

        initErrorMonitoring() {
            window.addEventListener('error', (event) => {
                const errorEvent = {
                    sessionId: this.sessionId,
                    errorType: event.error?.name || 'Error',
                    errorMessage: event.error?.message || event.message,
                    stackTrace: event.error?.stack || '',
                    userAgent: navigator.userAgent,
                    pageUrl: window.location.href,
                    timestamp: new Date().toISOString()
                };
                this.track('error', errorEvent);
                this.errors++;
            });

            window.addEventListener('unhandledrejection', (event) => {
                const errorEvent = {
                    sessionId: this.sessionId,
                    errorType: 'PromiseRejection',
                    errorMessage: event.reason?.message || String(event.reason),
                    stackTrace: event.reason?.stack || '',
                    userAgent: navigator.userAgent,
                    pageUrl: window.location.href,
                    timestamp: new Date().toISOString()
                };
                this.track('error', errorEvent);
                this.errors++;
            });
        }

        track(eventName, data) {
            if (Math.random() > this.config.sample_rate) {
                return;
            }

            this.events.push({
                type: eventName,
                data: data,
                timestamp: Date.now()
            });

            if (this.events.length >= this.config.batchSize) {
                this.flush();
            }
        }

        trackPageView(pageUrl) {
            this.pageViews++;
            this.track('page_view', {
                sessionId: this.sessionId,
                pageUrl: pageUrl || window.location.href,
                timestamp: new Date().toISOString()
            });
        }

        trackCustomEvent(eventName, properties) {
            this.track('custom', {
                sessionId: this.sessionId,
                eventName: eventName,
                properties: properties,
                timestamp: new Date().toISOString()
            });
        }

        async flush() {
            if (this.events.length === 0) {
                return;
            }

            const payload = {
                apiKey: this.config.apiKey,
                sessionId: this.sessionId,
                events: this.events,
                session: {
                    startTime: new Date(this.sessionStartTime).toISOString(),
                    pageViews: this.pageViews,
                    errors: this.errors,
                    duration: Date.now() - this.sessionStartTime
                }
            };

            try {
                const response = await fetch(this.config.api_endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    this.events = [];
                }
            } catch (error) {
                console.error('Failed to send RUM data:', error);
            }
        }
    }
"""

    def _generate_web_sdk_initialization(self, config: SDKConfig) -> str:
        """
        生成Web SDK初始化代码

        Args:
            config: SDK配置

        Returns:
            初始化代码字符串
        """
        return f"""
    // 初始化 SDK
    window.AIOpsRUM = new AIOpsRUM({{
        apiKey: '{config.api_key}',
        apiEndpoint: '{config.api_endpoint}',
        sampleRate: {config.sample_rate},
        enablePerformance: {str(config.enable_performance).lower()},
        enableErrors: {str(config.enable_errors).lower()},
        batchSize: {config.batch_size},
        flushInterval: {config.flush_interval}
    }});

    // 自动追踪页面视图
    window.AIOpsRUM.trackPageView();
"""

    def _generate_web_sdk(self, config: SDKConfig) -> str:
        """生成 Web SDK"""
        class_def = self._generate_web_sdk_class()
        init_code = self._generate_web_sdk_initialization(config)

        return f"""
// AIOps RUM Web SDK
// Generated at: {datetime.now().isoformat()}

(function(window) {{
{class_def}
{init_code}
}})(window);
"""

    def _generate_ios_sdk(self, config: SDKConfig) -> str:
        """生成 iOS SDK"""
        return f"""
// AIOps RUM iOS SDK (Swift)
// Generated at: {datetime.now().isoformat()}

import Foundation

class AIOpsRUM {{
    private static let shared = AIOpsRUM()

    var config: SDKConfig
    var sessionId: String
    var events: [[String: Any]] = []
    var sessionStartTime: Date
    var pageViews: Int = 0
    var errors: Int = 0

    private init() {{
        self.config = SDKConfig(
            apiKey: "{config.api_key}",
            apiEndpoint: "{config.api_endpoint}",
            sampleRate: {config.sample_rate},
            enablePerformance: {str(config.enable_performance).lower()},
            enableErrors: {str(config.enable_errors).lower()}
        )
        self.sessionId = generateSessionId()
        self.sessionStartTime = Date()
    }}

    static var instance: AIOpsRUM {{
        return shared
    }}

    private func generateSessionId() -> String {{
        return "rum-\\(UUID().uuidString.prefix(8))-\\(Int(Date().timeIntervalSince1970))"
    }}

    func track(eventName: String, data: [String: Any]) {{
        guard Double.random(in: 0...1) <= config.sampleRate else {{ return }}

        var eventData = data
        eventData["sessionId"] = sessionId
        eventData["timestamp"] = ISO8601DateFormatter().string(from: Date())

        events.append(eventData)

        if events.count >= config.batchSize {{
            flush()
        }}
    }}

    func trackScreenView(screenName: String) {{
        pageViews += 1
        track("screen_view", [
            "screenName": screenName,
            "sessionId": sessionId
        ])
    }}

    func trackError(error: Error, stackTrace: String) {{
        errors += 1
        track("error", [
            "errorType": String(describing: type(of: error)),
            "errorMessage": error.localizedDescription,
            "stackTrace": stackTrace,
            "sessionId": sessionId
        ])
    }}

    func flush() {{
        guard !events.isEmpty else {{ return }}

        let payload: [String: Any] = [
            "apiKey": config.apiKey,
            "sessionId": sessionId,
            "events": events,
            "session": [
                "startTime": ISO8601DateFormatter().string(from: sessionStartTime),
                "pageViews": pageViews,
                "errors": errors,
                "duration": Date().timeIntervalSince(sessionStartTime)
            ]
        ]

        // 发送到服务器
        // 实际实现应使用 URLSession
        events.removeAll()
    }}
}}

struct SDKConfig {{
    let apiKey: String
    let apiEndpoint: String
    let sampleRate: Double
    let enablePerformance: Bool
    let enableErrors: Bool
    let batchSize: Int = 10
    let flushInterval: TimeInterval = 5.0
}}
"""

    def _generate_android_sdk(self, config: SDKConfig) -> str:
        """生成 Android SDK"""
        return f"""
// AIOps RUM Android SDK (Kotlin)
// Generated at: {datetime.now().isoformat()}

package com.aiops.rum

import android.content.Context
import org.json.JSONObject
import java.util.UUID
import java.util.concurrent.ConcurrentLinkedQueue

class AIOpsRUM private constructor(context: Context) {{
    private val config = SDKConfig(
        apiKey = "{config.api_key}",
        apiEndpoint = "{config.api_endpoint}",
        sampleRate = {config.sample_rate},
        enablePerformance = {str(config.enable_performance).lower()},
        enableErrors = {str(config.enable_errors).lower()}
    )

    val sessionId = generateSessionId()
    private val events = ConcurrentLinkedQueue<JSONObject>()
    private val sessionStartTime = System.currentTimeMillis()
    var pageViews = 0
    var errors = 0

    init {{
        // 初始化监控
        if (config.enablePerformance) {{
            initPerformanceMonitoring()
        }}
        if (config.enableErrors) {{
            initErrorMonitoring()
        }}
    }}

    private fun generateSessionId(): String {{
        return "rum-${{UUID.randomUUID().toString().substring(0, 8)}}-${{System.currentTimeMillis() / 1000}}"  # noqa: E501
    }}

    fun track(eventName: String, data: Map<String, Any>) {{
        if (Math.random() > config.sampleRate) return

        val eventData = JSONObject(data)
        eventData.put("sessionId", sessionId)
        eventData.put("timestamp", System.currentTimeMillis())

        events.add(eventData)

        if (events.size >= config.batchSize) {{
            flush()
        }}
    }}

    fun trackScreenView(screenName: String) {{
        pageViews++
        track("screen_view", mapOf(
            "screenName" to screenName,
            "sessionId" to sessionId
        ))
    }}

    fun trackError(error: Throwable, stackTrace: String) {{
        errors++
        track("error", mapOf(
            "errorType" to error.javaClass.simpleName,
            "errorMessage" to error.message,
            "stackTrace" to stackTrace,
            "sessionId" to sessionId
        ))
    }}

    fun flush() {{
        if (events.isEmpty) return

        val payload = JSONObject().apply {{
            put("apiKey", config.apiKey)
            put("sessionId", sessionId)
            put("events", events.toList())
            put("session", JSONObject().apply {{
                put("startTime", sessionStartTime)
                put("pageViews", pageViews)
                put("errors", errors)
                put("duration", System.currentTimeMillis() - sessionStartTime)
            }})
        }}

        // 发送到服务器
        // 实际实现应使用 OkHttp 或 Retrofit
        events.clear()
    }}

    private fun initPerformanceMonitoring() {{
        // 初始化性能监控
    }}

    private fun initErrorMonitoring() {{
        // 初始化错误监控
        Thread.setDefaultUncaughtExceptionHandler {{ thread, throwable ->
            trackError(throwable, Log.getStackTraceString(throwable))
        }}
    }}

    companion object {{
        @Volatile
        private var instance: AIOpsRUM? = null

        fun getInstance(context: Context): AIOpsRUM {{
            return instance ?: synchronized(this) {{
                instance ?: AIOpsRUM(context).also {{ instance = it }}
            }}
        }}
    }}
}}

data class SDKConfig(
    val apiKey: String,
    val apiEndpoint: String,
    val sampleRate: Double,
    val enablePerformance: Boolean,
    val enableErrors: Boolean,
    val batchSize: Int = 10,
    val flushInterval: Long = 5000L
)
"""


# ----------------------------------------------------------------------
# 8️⃣ SDK 管理器
# ----------------------------------------------------------------------
class SDKManager:
    """SDK 管理器"""

    def __init__(self):
        self.generated_sdks: Dict[str, str] = {}
        self.sdk_configs: Dict[str, SDKConfig] = {}
        self.generator = RUMSDKGenerator()

    def create_config(
        self,
        config_id: str,
        api_key: str,
        api_endpoint: str,
        **kwargs,
    ) -> SDKConfig:
        """
        创建 SDK 配置

        Parameters
        ----------
        config_id : str
            配置 ID
        api_key : str
            API 密钥
        api_endpoint : str
            API 端点
        **kwargs
            其他配置参数

        Returns
        -------
        SDKConfig
            SDK 配置
        """
        config = SDKConfig(
            api_key=api_key,
            api_endpoint=api_endpoint,
            **kwargs,
        )

        self.sdk_configs[config_id] = config
        logger.info(f"Created SDK config: {config_id}")

        return config

    def generate_sdk(
        self,
        config_id: str,
        platform: SDKPlatform,
    ) -> str:
        """
        生成 SDK

        Parameters
        ----------
        config_id : str
            配置 ID
        platform : SDKPlatform
            平台

        Returns
        -------
        str
            SDK 代码
        """
        if config_id not in self.sdk_configs:
            raise ValueError(f"Config not found: {config_id}")

        config = self.sdk_configs[config_id]
        sdk_code = self.generator.generate_sdk(platform, config)

        self.generated_sdks[f"{config_id}_{platform.value}"] = sdk_code

        logger.info(f"Generated SDK for {platform.value}")

        return sdk_code

    def get_sdk(
        self,
        config_id: str,
        platform: SDKPlatform,
    ) -> Optional[str]:
        """获取已生成的 SDK"""
        key = f"{config_id}_{platform.value}"
        return self.generated_sdks.get(key)


# ----------------------------------------------------------------------
# 9️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_sdk_manager() -> SDKManager:
    """创建 SDK 管理器"""
    return SDKManager()


# ----------------------------------------------------------------------
# 🔟 CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试 SDK 管理器
    logger.info("Testing SDK manager")

    manager = create_sdk_manager()

    # 创建配置
    config = manager.create_config(
        config_id="default",
        api_key="test-api-key",
        api_endpoint="https://api.aiops.com/rum",
        sample_rate=1.0,
        enable_performance=True,
        enable_errors=True,
    )

    # 生成 Web SDK
    web_sdk = manager.generate_sdk("default", SDKPlatform.WEB)
    logger.info(f"Web SDK generated: {len(web_sdk)} characters")

    # 生成 iOS SDK
    ios_sdk = manager.generate_sdk("default", SDKPlatform.IOS)
    logger.info(f"iOS SDK generated: {len(ios_sdk)} characters")

    # 生成 Android SDK
    android_sdk = manager.generate_sdk("default", SDKPlatform.ANDROID)
    logger.info(f"Android SDK generated: {len(android_sdk)} characters")

    logger.info("Test passed!")
