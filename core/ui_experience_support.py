# -*- coding: utf-8 -*-
"""
UI Experience Support Module
UI体验支持模块

Provides backend support for enhanced UI experience:
- Real-time monitoring dashboard (WebSocket support)
- Interactive topology visualization (D3.js/Cytoscape.js backend support)
- Custom report generation (backend API)
- Mobile-optimized API responses
- Theme switching support (dark/light mode)
- Internationalization support (i18n backend API)
"""

import asyncio
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union  # noqa: F401

from loguru import logger

# Optional WebSocket imports
try:
    from fastapi import WebSocket

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket not available")


class ThemeMode(Enum):
    """主题模式"""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class ChartType(Enum):
    """图表类型"""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"


class VisualizationType(Enum):
    """可视化类型"""

    TOPOLOGY = "topology"
    FLOW = "flow"
    TREE = "tree"
    GRAPH = "graph"


@dataclass
class DashboardWidget:
    """仪表板组件"""

    id: str
    type: str
    title: str
    configuration: Dict[str, Any]
    position: Dict[str, int]
    size: Dict[str, int]
    data_source: str
    refresh_interval: int = 30


@dataclass
class TopologyNode:
    """拓扑节点（UI用）"""

    id: str
    label: str
    type: str
    position: Dict[str, float]
    properties: Dict[str, Any] = field(default_factory=dict)
    status: str = "healthy"


@dataclass
class TopologyEdge:
    """拓扑边（UI用）"""

    source: str
    target: str
    label: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """报表配置"""

    id: str
    name: str
    type: str
    time_range: str
    metrics: List[str]
    filters: Dict[str, Any] = field(default_factory=dict)
    group_by: Optional[str] = None
    chart_type: ChartType = ChartType.LINE


@dataclass
class UISettings:
    """UI设置"""

    user_id: str
    theme: ThemeMode = ThemeMode.LIGHT
    language: str = "en"
    dashboard_layout: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)


class UIExperienceSupport:
    """UI体验支持模块"""

    def __init__(self):
        """初始化UI体验支持模块"""
        # WebSocket连接管理
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.connection_subscriptions: Dict[str, List[str]] = defaultdict(list)

        # 仪表板配置
        self.dashboard_widgets: Dict[str, DashboardWidget] = {}
        self.dashboard_templates: Dict[str, Dict[str, Any]] = {}

        # 拓扑可视化数据
        self.topology_nodes: Dict[str, TopologyNode] = {}
        self.topology_edges: List[TopologyEdge] = []

        # 报表配置
        self.report_configs: Dict[str, ReportConfig] = {}
        self.report_cache: Dict[str, Dict[str, Any]] = {}

        # UI设置
        self.ui_settings: Dict[str, UISettings] = {}

        # 国际化
        self.translations: Dict[str, Dict[str, str]] = defaultdict(dict)

        # 实时数据缓存
        self.realtime_data_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # 配置
        self.max_websocket_connections = 100
        self.dashboard_refresh_interval = 30
        self.topology_update_interval = 60

    async def initialize(self):
        """初始化UI体验支持模块"""
        logger.info("Initializing UI Experience Support")

        # 加载仪表板模板
        await self._load_dashboard_templates()

        # 加载翻译
        await self._load_translations()

        # 启动实时数据推送循环
        asyncio.create_task(self._realtime_data_push_loop())

        # 启动拓扑更新循环
        asyncio.create_task(self._topology_update_loop())

        logger.info("UI Experience Support initialized successfully")

    async def _load_dashboard_templates(self):
        """加载仪表板模板"""
        logger.info("Loading dashboard templates")

        # 默认仪表板模板
        self.dashboard_templates["default"] = {
            "name": "Default Dashboard",
            "widgets": [
                {
                    "type": "metric",
                    "title": "CPU Usage",
                    "position": {"x": 0, "y": 0},
                    "size": {"width": 6, "height": 3},
                    "data_source": "cpu_usage",
                },
                {
                    "type": "metric",
                    "title": "Memory Usage",
                    "position": {"x": 6, "y": 0},
                    "size": {"width": 6, "height": 3},
                    "data_source": "memory_usage",
                },
                {
                    "type": "chart",
                    "title": "Request Rate",
                    "position": {"x": 0, "y": 3},
                    "size": {"width": 12, "height": 4},
                    "data_source": "request_rate",
                    "chart_type": "line",
                },
                {
                    "type": "topology",
                    "title": "Service Topology",
                    "position": {"x": 0, "y": 7},
                    "size": {"width": 12, "height": 6},
                    "data_source": "topology",
                },
            ],
        }

        logger.info("Dashboard templates loaded")

    async def _load_translations(self):
        """加载翻译"""
        logger.info("Loading translations")

        # 默认英文翻译
        self.translations["en"] = {
            "dashboard": "Dashboard",
            "alerts": "Alerts",
            "monitoring": "Monitoring",
            "topology": "Topology",
            "reports": "Reports",
            "settings": "Settings",
            "cpu_usage": "CPU Usage",
            "memory_usage": "Memory Usage",
            "disk_usage": "Disk Usage",
            "network_io": "Network I/O",
            "response_time": "Response Time",
            "throughput": "Throughput",
            "error_rate": "Error Rate",
        }

        # 中文翻译
        self.translations["zh"] = {
            "dashboard": "仪表板",
            "alerts": "告警",
            "monitoring": "监控",
            "topology": "拓扑",
            "reports": "报表",
            "settings": "设置",
            "cpu_usage": "CPU使用率",
            "memory_usage": "内存使用率",
            "disk_usage": "磁盘使用率",
            "network_io": "网络I/O",
            "response_time": "响应时间",
            "throughput": "吞吐量",
            "error_rate": "错误率",
        }

        logger.info("Translations loaded")

    async def connect_websocket(self, websocket: WebSocket, client_id: str):
        """连接WebSocket"""
        logger.info(f"WebSocket connection: {client_id}")

        if not WEBSOCKET_AVAILABLE:
            logger.error("WebSocket not available")
            return False

        # 检查连接数量限制
        if len(self.websocket_connections) >= self.max_websocket_connections:
            logger.warning("Maximum WebSocket connections reached")
            return False

        self.websocket_connections[client_id] = websocket
        return True

    async def disconnect_websocket(self, client_id: str):
        """断开WebSocket连接"""
        logger.info(f"WebSocket disconnection: {client_id}")

        if client_id in self.websocket_connections:
            del self.websocket_connections[client_id]

        if client_id in self.connection_subscriptions:
            del self.connection_subscriptions[client_id]

    async def subscribe_to_updates(self, client_id: str, topics: List[str]):
        """订阅更新"""
        logger.info(f"Client {client_id} subscribing to topics: {topics}")

        if client_id in self.connection_subscriptions:
            self.connection_subscriptions[client_id].extend(topics)
        else:
            self.connection_subscriptions[client_id] = topics

    async def unsubscribe_from_updates(self, client_id: str, topics: List[str]):
        """取消订阅更新"""
        logger.info(f"Client {client_id} unsubscribing from topics: {topics}")

        if client_id in self.connection_subscriptions:
            for topic in topics:
                if topic in self.connection_subscriptions[client_id]:
                    self.connection_subscriptions[client_id].remove(topic)

    async def broadcast_update(self, topic: str, data: Dict[str, Any]):
        """广播更新"""
        logger.info(f"Broadcasting update to topic: {topic}")

        if not WEBSOCKET_AVAILABLE:
            return

        # 找出订阅了该主题的客户端
        for client_id, subscriptions in self.connection_subscriptions.items():
            if topic in subscriptions and client_id in self.websocket_connections:
                try:
                    websocket = self.websocket_connections[client_id]
                    await websocket.send_json(
                        {"topic": topic, "data": data, "timestamp": datetime.now().isoformat()}
                    )
                except Exception as e:
                    logger.error(f"Failed to send update to {client_id}: {e}")

    async def _realtime_data_push_loop(self):
        """实时数据推送循环"""
        while True:
            try:
                await asyncio.sleep(self.dashboard_refresh_interval)

                # 推送实时指标数据
                await self._push_realtime_metrics()

                # 推送告警更新
                await self._push_alert_updates()

            except Exception as e:
                logger.error(f"Realtime data push loop error: {e}")

    async def _push_realtime_metrics(self):
        """推送实时指标"""
        # 模拟实时数据
        metrics_data = {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 55.3,
            "network_io": {"in": 1024, "out": 2048},
            "response_time": 125,
            "throughput": 850,
            "error_rate": 0.02,
        }

        # 缓存数据
        for metric_name, value in metrics_data.items():
            self.realtime_data_cache[metric_name].append(
                {"value": value, "timestamp": datetime.now().isoformat()}
            )

        # 广播更新
        await self.broadcast_update("metrics", metrics_data)

    async def _push_alert_updates(self):
        """推送告警更新"""
        # 模拟告警数据
        alerts: list[Dict[str, Any]] = []

        # 广播告警更新
        if alerts:
            await self.broadcast_update("alerts", {"alerts": alerts})

    async def _topology_update_loop(self):
        """拓扑更新循环"""
        while True:
            try:
                await asyncio.sleep(self.topology_update_interval)

                # 更新拓扑数据
                await self._update_topology_data()

                # 广播拓扑更新
                await self._broadcast_topology_update()

            except Exception as e:
                logger.error(f"Topology update loop error: {e}")

    async def _update_topology_data(self):
        """更新拓扑数据"""
        # 模拟拓扑更新

    async def _broadcast_topology_update(self):
        """广播拓扑更新"""
        topology_data = {
            "nodes": [self._node_to_dict(node) for node in self.topology_nodes.values()],
            "edges": [self._edge_to_dict(edge) for edge in self.topology_edges],
        }

        await self.broadcast_update("topology", topology_data)

    def _node_to_dict(self, node: TopologyNode) -> Dict[str, Any]:
        """节点转字典"""
        return {
            "id": node.id,
            "label": node.label,
            "type": node.type,
            "position": node.position,
            "properties": node.properties,
            "status": node.status,
        }

    def _edge_to_dict(self, edge: TopologyEdge) -> Dict[str, Any]:
        """边转字典"""
        return {
            "source": edge.source,
            "target": edge.target,
            "label": edge.label,
            "type": edge.type,
            "properties": edge.properties,
        }

    async def get_dashboard_data(self, user_id: str, time_range: str = "1h") -> Dict[str, Any]:
        """获取仪表板数据"""
        logger.info(f"Getting dashboard data for user {user_id}")

        # 获取用户的仪表板配置
        user_settings = self.ui_settings.get(user_id)
        if not user_settings:
            user_settings = UISettings(user_id=user_id)
            self.ui_settings[user_id] = user_settings

        # 使用默认模板或用户自定义布局
        layout = user_settings.dashboard_layout or self.dashboard_templates["default"]

        # 收集组件数据
        widgets_data = []
        for widget_config in layout.get("widgets", []):
            widget_data = await self._get_widget_data(widget_config, time_range)
            widgets_data.append(widget_data)

        return {
            "layout": layout,
            "widgets": widgets_data,
            "theme": user_settings.theme.value,
            "timestamp": datetime.now().isoformat(),
        }

    async def _get_widget_data(
        self, widget_config: Dict[str, Any], time_range: str
    ) -> Dict[str, Any]:
        """获取组件数据"""
        widget_type = widget_config.get("type")
        data_source = widget_config.get("data_source")

        if widget_type == "metric":
            if data_source is None:
                return {"type": widget_type, "data": None}
            return await self._get_metric_data(data_source)
        elif widget_type == "chart":
            return await self._get_chart_data(widget_config, time_range)
        elif widget_type == "topology":
            return await self.get_topology_data()
        else:
            return {"type": widget_type, "data": None}

    async def _get_metric_data(self, metric_name: str) -> Dict[str, Any]:
        """获取指标数据"""
        # 从缓存中获取最新数据
        if metric_name in self.realtime_data_cache and self.realtime_data_cache[metric_name]:
            latest_data = self.realtime_data_cache[metric_name][-1]
            return {
                "type": "metric",
                "data": latest_data["value"],
                "timestamp": latest_data["timestamp"],
            }

        return {"type": "metric", "data": None}

    async def _get_chart_data(
        self, widget_config: Dict[str, Any], time_range: str
    ) -> Dict[str, Any]:
        """获取图表数据"""
        data_source = widget_config.get("data_source")
        chart_type = widget_config.get("chart_type", "line")

        # 从缓存中获取历史数据
        if data_source in self.realtime_data_cache:
            data_points = list(self.realtime_data_cache[data_source])

            # 根据时间范围过滤
            cutoff_time = datetime.now() - self._parse_time_range(time_range)
            filtered_data = [
                dp for dp in data_points if datetime.fromisoformat(dp["timestamp"]) > cutoff_time
            ]

            return {
                "type": "chart",
                "chart_type": chart_type,
                "data": {
                    "timestamps": [dp["timestamp"] for dp in filtered_data],
                    "values": [dp["value"] for dp in filtered_data],
                },
            }

        return {"type": "chart", "data": None}

    def _parse_time_range(self, time_range: str) -> timedelta:
        """解析时间范围"""
        if time_range == "1h":
            return timedelta(hours=1)
        elif time_range == "6h":
            return timedelta(hours=6)
        elif time_range == "24h":
            return timedelta(hours=24)
        elif time_range == "7d":
            return timedelta(days=7)
        else:
            return timedelta(hours=1)

    async def get_topology_data(
        self, visualization_type: VisualizationType = VisualizationType.TOPOLOGY
    ) -> Dict[str, Any]:
        """获取拓扑数据"""
        logger.info(f"Getting topology data: {visualization_type.value}")

        nodes = [self._node_to_dict(node) for node in self.topology_nodes.values()]
        edges = [self._edge_to_dict(edge) for edge in self.topology_edges]

        return {
            "visualization_type": visualization_type.value,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "last_updated": datetime.now().isoformat(),
            },
        }

    async def create_report(self, config: ReportConfig) -> Dict[str, Any]:
        """创建报表"""
        logger.info(f"Creating report: {config.name}")

        # 生成报表ID
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        # 保存配置
        self.report_configs[report_id] = config

        # 生成报表数据
        report_data = await self._generate_report_data(config)

        return {
            "report_id": report_id,
            "config": config,
            "data": report_data,
            "generated_at": datetime.now().isoformat(),
        }

    async def _generate_report_data(self, config: ReportConfig) -> Dict[str, Any]:
        """生成报表数据"""
        # 根据报表类型生成数据
        if config.chart_type == ChartType.LINE:
            return await self._generate_line_chart_data(config)
        elif config.chart_type == ChartType.BAR:
            return await self._generate_bar_chart_data(config)
        elif config.chart_type == ChartType.PIE:
            return await self._generate_pie_chart_data(config)
        else:
            return {}

    async def _generate_line_chart_data(self, config: ReportConfig) -> Dict[str, Any]:
        """生成折线图数据"""
        # 模拟数据生成
        time_points = []
        values = []

        for i in range(24):
            time_points.append((datetime.now() - timedelta(hours=23 - i)).isoformat())
            values.append(50 + (i % 10) * 5)

        return {"chart_type": "line", "data": {"timestamps": time_points, "values": values}}

    async def _generate_bar_chart_data(self, config: ReportConfig) -> Dict[str, Any]:
        """生成柱状图数据"""
        # 模拟数据生成
        categories = ["CPU", "Memory", "Disk", "Network"]
        values = [45, 67, 55, 32]

        return {"chart_type": "bar", "data": {"categories": categories, "values": values}}

    async def _generate_pie_chart_data(self, config: ReportConfig) -> Dict[str, Any]:
        """生成饼图数据"""
        # 模拟数据生成
        labels = ["Healthy", "Warning", "Critical"]
        values = [70, 20, 10]

        return {"chart_type": "pie", "data": {"labels": labels, "values": values}}

    def get_translation(self, language: str, key: str) -> Optional[str]:
        """获取翻译"""
        if language in self.translations and key in self.translations[language]:
            return self.translations[language][key]

        # 回退到英文
        if "en" in self.translations and key in self.translations["en"]:
            return self.translations["en"][key]

        # 回退到键名
        return key

    async def set_ui_settings(self, user_id: str, settings: Dict[str, Any]) -> UISettings:
        """设置UI配置"""
        logger.info(f"Setting UI preferences for user {user_id}")

        if user_id not in self.ui_settings:
            self.ui_settings[user_id] = UISettings(user_id=user_id)

        user_settings = self.ui_settings[user_id]

        # 更新设置
        if "theme" in settings:
            user_settings.theme = ThemeMode(settings["theme"])

        if "language" in settings:
            user_settings.language = settings["language"]

        if "dashboard_layout" in settings:
            user_settings.dashboard_layout = settings["dashboard_layout"]

        if "preferences" in settings:
            user_settings.preferences.update(settings["preferences"])

        return user_settings

    async def get_ui_settings(self, user_id: str) -> Optional[UISettings]:
        """获取UI配置"""
        return self.ui_settings.get(user_id)

    async def get_mobile_optimized_data(
        self, endpoint: Any = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """获取移动端优化数据"""
        if params is None:
            params = {}
        if endpoint is None:
            endpoint = ""
        logger.info(f"Getting mobile optimized data for endpoint: {endpoint}")

        # 根据端点返回优化后的数据
        if endpoint == "dashboard":
            # 简化的仪表板数据
            return {
                "metrics": {"cpu": 45.2, "memory": 67.8, "alerts": 3},
                "recent_alerts": [
                    {"severity": "high", "message": "CPU high"},
                    {"severity": "medium", "message": "Memory warning"},
                ],
                "optimized": True,
            }
        elif endpoint == "alerts":
            # 分页的告警数据
            page = params.get("page", 1)
            limit = params.get("limit", 10)

            return {
                "alerts": [],  # 实际数据
                "page": page,
                "limit": limit,
                "total": 0,
                "optimized": True,
            }
        else:
            return {"optimized": False}

    def get_ui_statistics(self) -> Dict[str, Any]:
        """获取UI统计信息"""
        return {
            "websocket_connections": len(self.websocket_connections),
            "active_subscriptions": sum(
                len(subs) for subs in self.connection_subscriptions.values()
            ),
            "dashboard_widgets": len(self.dashboard_widgets),
            "topology_nodes": len(self.topology_nodes),
            "topology_edges": len(self.topology_edges),
            "report_configs": len(self.report_configs),
            "ui_settings": len(self.ui_settings),
            "supported_languages": list(self.translations.keys()),
            "supported_themes": [mode.value for mode in ThemeMode],
        }


__all__ = [
    "ThemeMode",
    "ChartType",
    "VisualizationType",
    "DashboardWidget",
    "TopologyNode",
    "TopologyEdge",
    "ReportConfig",
    "UISettings",
    "UIExperienceSupport",
    "ui_experience_support",
]

# 全局实例
ui_experience_support = UIExperienceSupport()
