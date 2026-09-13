# -*- coding: utf-8 -*-
"""
Enhanced Root Cause Analyzer Module
增强根因分析模块

Provides advanced root cause analysis capabilities:
- Real-time topology discovery and dynamic updates
- Historical pattern matching for faster RCA
- Enhanced causal analysis with improved accuracy
- Root cause prediction using ML models
- Cross-layer tracing and correlation
- Automated root cause verification
"""

import asyncio
import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

# Optional ML imports
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available for enhanced RCA")


class RCASeverity(Enum):
    """根因分析严重程度"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TopologyChangeType(Enum):
    """拓扑变更类型"""

    ADD_NODE = "add_node"
    REMOVE_NODE = "remove_node"
    ADD_EDGE = "add_edge"
    REMOVE_EDGE = "remove_edge"
    UPDATE_NODE = "update_node"


@dataclass
class TopologyNode:
    """拓扑节点"""

    id: str
    type: str  # service, database, cache, queue, etc.
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "healthy"
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TopologyEdge:
    """拓扑边"""

    source: str
    target: str
    type: str  # calls, reads, writes, publishes, subscribes, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0


@dataclass
class TopologyChange:
    """拓扑变更事件"""

    change_type: TopologyChangeType
    timestamp: datetime
    details: Dict[str, Any]


@dataclass
class HistoricalIncident:
    """历史事故记录"""

    id: str
    timestamp: datetime
    symptoms: List[str]
    root_causes: List[str]
    resolution: str
    similarity_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RootCauseHypothesis:
    """根因假设"""

    node_id: str
    confidence: float
    explanation: str
    evidence: List[str]
    impact_score: float
    severity: RCASeverity
    predicted_impact: Optional[Dict[str, Any]] = None
    verification_status: str = "unverified"  # unverified, verified, rejected


class EnhancedRootCauseAnalyzer:
    """增强根因分析器"""

    def __init__(self):
        """初始化增强根因分析器"""
        # 拓扑图
        self.nodes: Dict[str, TopologyNode] = {}
        self.edges: Dict[str, List[TopologyEdge]] = defaultdict(list)
        self.topology_changes: List[TopologyChange] = []

        # 历史模式
        self.historical_incidents: List[HistoricalIncident] = []
        self.pattern_index: Dict[str, List[HistoricalIncident]] = defaultdict(list)

        # 因果分析模型
        self.causal_graph: Dict[str, Set[str]] = defaultdict(set)
        self.causal_strength: Dict[Tuple[str, str], float] = {}

        # ML模型
        self.rca_classifier = None
        self.pattern_vectorizer = None

        # 配置
        self.topology_refresh_interval = timedelta(minutes=5)
        self.pattern_similarity_threshold = 0.7
        self.max_historical_incidents = 10000

        # 性能优化
        self.recent_analyses: deque = deque(maxlen=1000)
        self.analysis_cache: Dict[str, RootCauseHypothesis] = {}
        # 状态快照（用于趋势分析/故障预测）
        self._state_snapshots: deque = deque(maxlen=100)

    async def initialize(self):
        """初始化分析器"""
        logger.info("Initializing Enhanced Root Cause Analyzer")

        # 初始化ML模型
        if ML_AVAILABLE:
            self.rca_classifier = RandomForestClassifier(n_estimators=100)
            self.pattern_vectorizer = TfidfVectorizer(max_features=500)
            logger.info("ML models initialized for RCA")

        # 加载历史事故数据
        await self._load_historical_incidents()

        # 构建初始拓扑
        await self.discover_topology()

        # 启动拓扑发现任务
        asyncio.create_task(self._topology_discovery_loop())

        logger.info("Enhanced Root Cause Analyzer initialized successfully")

    async def discover_topology(self) -> Dict[str, Any]:
        """实时拓扑发现

        通过服务发现、配置分析、依赖注入等方式发现系统拓扑
        """
        logger.info("Discovering system topology")

        try:
            # 从各种来源发现拓扑
            discovered_nodes = await self._discover_nodes()
            discovered_edges = await self._discover_edges()

            # 更新拓扑
            await self._update_topology(discovered_nodes, discovered_edges)

            # 构建因果图
            await self._build_causal_graph()

            topology_info = {
                "nodes_count": len(self.nodes),
                "edges_count": sum(len(edges) for edges in self.edges.values()),
                "discovery_time": datetime.now().isoformat(),
            }

            logger.info(f"Topology discovery completed: {topology_info}")
            return topology_info

        except Exception as e:
            logger.error(f"Topology discovery failed: {e}")
            return {"error": str(e)}

    async def _discover_nodes(self) -> List[TopologyNode]:
        """发现拓扑节点"""
        nodes = []

        try:
            # 从配置文件发现
            config_nodes = await self._discover_from_config()
            nodes.extend(config_nodes)

            # 从服务注册中心发现
            service_nodes = await self._discover_from_service_registry()
            nodes.extend(service_nodes)

            # 从数据库元数据发现
            db_nodes = await self._discover_from_database_metadata()
            nodes.extend(db_nodes)

            # 从监控数据发现
            monitored_nodes = await self._discover_from_monitoring()
            nodes.extend(monitored_nodes)

        except Exception as e:
            logger.error(f"Node discovery error: {e}")

        return nodes

    async def _discover_edges(self) -> List[TopologyEdge]:
        """发现拓扑边"""
        edges = []

        try:
            # 从应用配置发现调用关系
            config_edges = await self._discover_edges_from_config()
            edges.extend(config_edges)

            # 从追踪数据发现调用关系
            trace_edges = await self._discover_edges_from_traces()
            edges.extend(trace_edges)

            # 从数据库查询分析发现数据流
            db_edges = await self._discover_edges_from_database_queries()
            edges.extend(db_edges)

        except Exception as e:
            logger.error(f"Edge discovery error: {e}")

        return edges

    async def _discover_from_config(self) -> List[TopologyNode]:
        """从真实项目配置发现基础设施节点。

        历史问题（已修复）：原实现为 ``return []`` 桩。现依据 ``config`` 中真实配置
        的基础设施组件（PostgreSQL / Redis / Qdrant / Elasticsearch / Prometheus /
        Grafana 等）构造节点；未配置的组件不产出（不伪造）。
        """
        import os

        nodes: List[TopologyNode] = []

        def _add(node_id: str, ntype: str, name: str, props: Dict[str, Any]) -> None:
            nodes.append(
                TopologyNode(
                    id=node_id,
                    type=ntype,
                    name=name,
                    properties=props,
                    last_updated=datetime.now(),
                )
            )

        try:
            import config as cfg

            if getattr(cfg, "POSTGRES_HOST", ""):
                _add(
                    "postgres",
                    "database",
                    "PostgreSQL",
                    {
                        "host": cfg.POSTGRES_HOST,
                        "port": getattr(cfg, "POSTGRES_PORT", 5432),
                        "db": getattr(cfg, "POSTGRES_DB", ""),
                    },
                )
            if getattr(cfg, "REDIS_HOST", ""):
                _add(
                    "redis",
                    "cache",
                    "Redis",
                    {"host": cfg.REDIS_HOST, "port": getattr(cfg, "REDIS_PORT", 6379)},
                )
            if getattr(cfg, "QDRANT_URL", ""):
                _add("qdrant", "vector_db", "Qdrant", {"url": cfg.QDRANT_URL})
            if getattr(cfg, "ELASTICSEARCH_URL", ""):
                _add(
                    "elasticsearch", "search", "Elasticsearch", {"url": cfg.ELASTICSEARCH_URL}
                )

            prometheus_url = os.getenv("PROMETHEUS_URL") or getattr(cfg, "PROMETHEUS_URL", "")
            if prometheus_url:
                _add("prometheus", "monitoring", "Prometheus", {"url": prometheus_url})
            grafana_url = os.getenv("GRAFANA_URL") or getattr(cfg, "GRAFANA_URL", "")
            if grafana_url:
                _add("grafana", "monitoring", "Grafana", {"url": grafana_url})
        except Exception as e:  # noqa: BLE001 - config 读取失败须如实暴露
            logger.warning(f"Config-based topology discovery failed: {e}")

        return nodes

    async def _discover_from_service_registry(self) -> List[TopologyNode]:
        """从真实服务注册中心（Consul / 通用 registry）发现节点。

        历史问题（已修复）：原实现为 ``return []`` 桩。现当 ``SERVICE_REGISTRY_URL`` /
        ``CONSUL_HTTP_ADDR`` 已配置时，查询真实的 ``/v1/catalog/services``；未配置注册
        中心时如实返回空（不伪造）。
        """
        import os

        registry = os.getenv("SERVICE_REGISTRY_URL") or os.getenv("CONSUL_HTTP_ADDR")
        if not registry:
            return []

        base = registry if registry.startswith("http") else f"http://{registry}"
        nodes: List[TopologyNode] = []
        try:
            import requests

            resp = requests.get(base.rstrip("/") + "/v1/catalog/services", timeout=5)
            resp.raise_for_status()
            for name in (resp.json() or {}).keys():
                nodes.append(
                    TopologyNode(
                        id=f"svc:{name}",
                        type="service",
                        name=str(name),
                        properties={"registry": base},
                        last_updated=datetime.now(),
                    )
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Service registry topology discovery failed: {e}")
        return nodes

    async def _discover_from_database_metadata(self) -> List[TopologyNode]:
        """从真实数据库元数据（information_schema）发现表节点。

        历史问题（已修复）：原实现为 ``return []`` 桩。现通过 SQLAlchemy inspector 读取
        项目数据库的真实表清单；数据库不可用时如实返回空。
        """

        def _query_tables() -> List[str]:
            from sqlalchemy import inspect

            from core.database import engine

            return list(inspect(engine).get_table_names())

        try:
            tables = await asyncio.to_thread(_query_tables)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Database metadata topology discovery failed: {e}")
            return []

        return [
            TopologyNode(
                id=f"table:{name}",
                type="database_table",
                name=name,
                properties={"schema": "public"},
                last_updated=datetime.now(),
            )
            for name in tables
        ]

    async def _discover_from_monitoring(self) -> List[TopologyNode]:
        """从真实监控（Prometheus targets）发现被监控节点。

        历史问题（已修复）：原实现为 ``return []`` 桩。现当 ``PROMETHEUS_URL`` 已配置时，
        查询真实的 ``/api/v1/targets``；未配置时如实返回空。
        """
        import os

        prometheus_url = os.getenv("PROMETHEUS_URL")
        if not prometheus_url:
            return []

        nodes: List[TopologyNode] = []
        try:
            import requests

            resp = requests.get(prometheus_url.rstrip("/") + "/api/v1/targets", timeout=5)
            resp.raise_for_status()
            for target in resp.json().get("data", {}).get("activeTargets", []):
                labels = target.get("labels", {}) or {}
                job = labels.get("job", "unknown")
                instance = labels.get("instance", "")
                nodes.append(
                    TopologyNode(
                        id=f"target:{job}:{instance}",
                        type="monitored_target",
                        name=f"{job}/{instance}",
                        properties={
                            "health": target.get("health"),
                            "scrape_url": target.get("scrapeUrl"),
                            "labels": labels,
                        },
                        health_status=target.get("health", "unknown"),
                        last_updated=datetime.now(),
                    )
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Monitoring topology discovery failed: {e}")
        return nodes

    async def _discover_edges_from_config(self) -> List[TopologyEdge]:
        """从真实配置声明发现应用→后端依赖边。

        历史问题（已修复）：原实现为 ``return []`` 桩。现基于配置中真实存在的后端
        组件，建立应用与该后端之间的依赖边（应用为根节点）。
        """
        edges: List[TopologyEdge] = []
        backend_nodes = await self._discover_from_config()
        for node in backend_nodes:
            edges.append(
                TopologyEdge(
                    source="application",
                    target=node.id,
                    type="depends_on",
                    properties={"declared_in": "config"},
                )
            )
        return edges

    async def _discover_edges_from_traces(self) -> List[TopologyEdge]:
        """从真实追踪后端（Tempo / Jaeger）发现服务调用边。

        历史问题（已修复）：原实现为 ``return []`` 桩。现当 ``TEMPO_URL`` / ``JAEGER_URL``
        已配置时查询真实的追踪 API；未配置时如实返回空。
        """
        import os

        tempo_url = os.getenv("TEMPO_URL")
        jaeger_url = os.getenv("JAEGER_URL")
        if not tempo_url and not jaeger_url:
            return []

        edges: List[TopologyEdge] = []
        try:
            import requests

            if jaeger_url:
                resp = requests.get(
                    jaeger_url.rstrip("/") + "/api/services", timeout=5
                )
                resp.raise_for_status()
                services = resp.json().get("data", []) or []
                for svc in services:
                    edges.append(
                        TopologyEdge(
                            source="application",
                            target=f"svc:{svc}",
                            type="calls",
                            properties={"source": "jaeger"},
                        )
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Trace-based edge discovery failed: {e}")
        return edges

    async def _discover_edges_from_database_queries(self) -> List[TopologyEdge]:
        """从真实数据库外键元数据发现表→表数据流边。

        历史问题（已修复）：原实现为 ``return []`` 桩。现读取真实外键约束构造边。
        """

        def _query_fks() -> List[Tuple[str, str, str]]:
            from sqlalchemy import inspect

            from core.database import engine

            inspector = inspect(engine)
            relations: List[Tuple[str, str, str]] = []
            for table in inspector.get_table_names():
                for fk in inspector.get_foreign_keys(table):
                    referred = fk.get("referred_table")
                    if referred:
                        relations.append((table, referred, ",".join(fk.get("constrained_columns", []))))
            return relations

        try:
            relations = await asyncio.to_thread(_query_fks)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Database-query edge discovery failed: {e}")
            return []

        return [
            TopologyEdge(
                source=f"table:{src}",
                target=f"table:{dst}",
                type="references",
                properties={"columns": cols},
            )
            for src, dst, cols in relations
        ]

    async def _update_topology(self, nodes: List[TopologyNode], edges: List[TopologyEdge]):
        """更新拓扑"""
        # 检测变更
        changes = self._detect_topology_changes(nodes, edges)

        # 应用变更
        for change in changes:
            self.topology_changes.append(change)
            await self._apply_topology_change(change)

        # 清理旧变更
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.topology_changes = [c for c in self.topology_changes if c.timestamp > cutoff_time]

    def _detect_topology_changes(
        self, new_nodes: List[TopologyNode], new_edges: List[TopologyEdge]
    ) -> List[TopologyChange]:
        """检测拓扑变更（携带真实节点/边对象，供 _apply_topology_change 落地）。"""
        changes: List[TopologyChange] = []

        # 检测节点变更
        new_nodes_by_id = {node.id: node for node in new_nodes}
        existing_node_ids = set(self.nodes.keys())

        for node_id, node in new_nodes_by_id.items():
            if node_id not in existing_node_ids:
                changes.append(
                    TopologyChange(
                        change_type=TopologyChangeType.ADD_NODE,
                        timestamp=datetime.now(),
                        details={"node_id": node_id, "node": node},
                    )
                )

        for node_id in existing_node_ids - set(new_nodes_by_id.keys()):
            changes.append(
                TopologyChange(
                    change_type=TopologyChangeType.REMOVE_NODE,
                    timestamp=datetime.now(),
                    details={"node_id": node_id},
                )
            )

        # 检测边变更
        existing_edge_keys = {
            (edge.source, edge.target, edge.type)
            for edges in self.edges.values()
            for edge in edges
        }
        new_edge_keys = {(edge.source, edge.target, edge.type) for edge in new_edges}

        for edge in new_edges:
            key = (edge.source, edge.target, edge.type)
            if key not in existing_edge_keys:
                changes.append(
                    TopologyChange(
                        change_type=TopologyChangeType.ADD_EDGE,
                        timestamp=datetime.now(),
                        details={"edge": edge},
                    )
                )

        for key in existing_edge_keys - new_edge_keys:
            changes.append(
                TopologyChange(
                    change_type=TopologyChangeType.REMOVE_EDGE,
                    timestamp=datetime.now(),
                    details={"edge_key": key},
                )
            )

        return changes

    async def _apply_topology_change(self, change: TopologyChange):
        """应用拓扑变更（真实更新 ``self.nodes`` / ``self.edges``）。"""
        if change.change_type == TopologyChangeType.ADD_NODE:
            node = change.details.get("node")
            if node is not None:
                self.nodes[node.id] = node
        elif change.change_type == TopologyChangeType.REMOVE_NODE:
            node_id = change.details.get("node_id")
            self.nodes.pop(node_id, None)
            # 级联移除关联边
            self.edges.pop(node_id, None)
            for source in list(self.edges.keys()):
                self.edges[source] = [
                    edge for edge in self.edges[source] if edge.target != node_id
                ]
        elif change.change_type == TopologyChangeType.ADD_EDGE:
            edge = change.details.get("edge")
            if edge is not None:
                bucket = self.edges.setdefault(edge.source, [])
                if not any(
                    e.source == edge.source and e.target == edge.target and e.type == edge.type
                    for e in bucket
                ):
                    bucket.append(edge)
        elif change.change_type == TopologyChangeType.REMOVE_EDGE:
            source, target, edge_type = change.details.get("edge_key", (None, None, None))
            if source is not None:
                self.edges[source] = [
                    edge
                    for edge in self.edges.get(source, [])
                    if not (edge.target == target and edge.type == edge_type)
                ]
        elif change.change_type == TopologyChangeType.UPDATE_NODE:
            node = change.details.get("node")
            if node is not None:
                self.nodes[node.id] = node

    async def _build_causal_graph(self):
        """构建因果图"""
        logger.info("Building causal graph from topology")

        # 基于拓扑构建因果图
        for source, edges in self.edges.items():
            for edge in edges:
                self.causal_graph[source].add(edge.target)
                # 设置因果强度
                self.causal_strength[(source, edge.target)] = edge.strength

        # 添加跨层级因果关系
        await self._add_cross_layer_causality()

        logger.info(
            f"Causal graph built: {len(self.causal_graph)} nodes, {len(self.causal_strength)} edges"
        )

    async def _add_cross_layer_causality(self):
        """添加跨层级因果关系。

        基于节点类型推断层级：基础设施/数据库/缓存/队列 -> 应用服务 -> 业务组件，
        为跨层边补充因果强度。
        """
        infra_types = {"database", "cache", "queue", "server", "host", "network", "storage"}
        app_types = {"service", "application", "api", "microservice", "web"}
        business_types = {"business", "product", "order", "payment", "user", "transaction"}

        layer_map: Dict[str, int] = {}
        for node_id, node in self.nodes.items():
            node_type = (node.type or "").lower()
            if node_type in infra_types or any(t in node_type for t in infra_types):
                layer_map[node_id] = 0
            elif node_type in app_types or any(t in node_type for t in app_types):
                layer_map[node_id] = 1
            elif node_type in business_types or any(t in node_type for t in business_types):
                layer_map[node_id] = 2
            else:
                layer_map[node_id] = 1  # 默认归为应用层

        # 推断跨层因果关系：低层节点影响高层节点
        for source, edges in self.edges.items():
            source_layer = layer_map.get(source, 1)
            for edge in edges:
                target_layer = layer_map.get(edge.target, 1)
                if target_layer > source_layer:
                    # 低层 -> 高层，添加或增强因果边
                    self.causal_graph[source].add(edge.target)
                    key = (source, edge.target)
                    current_strength = self.causal_strength.get(key, edge.strength)
                    self.causal_strength[key] = min(current_strength * 1.2, 1.0)

        logger.info(
            f"Cross-layer causality added: {len(self.causal_graph)} nodes, "
            f"{len(self.causal_strength)} causal edges"
        )

    async def _topology_discovery_loop(self):
        """拓扑发现循环"""
        while True:
            try:
                await asyncio.sleep(self.topology_refresh_interval.total_seconds())
                await self.discover_topology()
            except Exception as e:
                logger.error(f"Topology discovery loop error: {e}")

    async def analyze_root_causes(
        self, anomaly_nodes: Set[str], context: Optional[Dict] = None
    ) -> List[RootCauseHypothesis]:
        """分析根因

        结合实时拓扑、历史模式和因果分析进行根因推断
        """
        logger.info(f"Analyzing root causes for {len(anomaly_nodes)} anomaly nodes")

        # 1. 历史模式匹配
        pattern_matches = await self._match_historical_patterns(anomaly_nodes, context)

        # 2. 因果分析
        causal_hypotheses = await self._perform_causal_analysis(anomaly_nodes, context)

        # 3. 拓扑感知分析
        topology_hypotheses = await self._perform_topology_analysis(anomaly_nodes, context)

        # 4. ML预测（如果可用）
        ml_hypotheses = []
        if ML_AVAILABLE:
            ml_hypotheses = await self._perform_ml_analysis(anomaly_nodes, context)

        # 5. 综合所有假设
        combined_hypotheses = await self._combine_hypotheses(
            pattern_matches, causal_hypotheses, topology_hypotheses, ml_hypotheses
        )

        # 6. 排序和过滤
        ranked_hypotheses = await self._rank_hypotheses(combined_hypotheses)

        # 7. 缓存结果
        analysis_key = self._generate_analysis_key(anomaly_nodes, context)
        self.recent_analyses.append(analysis_key)

        logger.info(f"Root cause analysis completed: {len(ranked_hypotheses)} hypotheses")
        return ranked_hypotheses

    async def _match_historical_patterns(
        self, anomaly_nodes: Set[str], context: Optional[Dict]
    ) -> List[RootCauseHypothesis]:
        """历史模式匹配"""
        logger.info("Matching historical patterns")

        # 生成当前症状的特征
        current_features = self._extract_features(anomaly_nodes, context)
        similarity_hash = self._generate_similarity_hash(current_features)

        # 查找相似的历史事故
        similar_incidents = []
        for incident in self.historical_incidents:
            similarity = self._calculate_pattern_similarity(
                similarity_hash, incident.similarity_hash
            )
            if similarity >= self.pattern_similarity_threshold:
                similar_incidents.append((incident, similarity))

        # 基于相似事故生成根因假设
        hypotheses = []
        for incident, similarity in similar_incidents:
            for root_cause in incident.root_causes:
                hypothesis = RootCauseHypothesis(
                    node_id=root_cause,
                    confidence=similarity * 0.8,  # 基于相似度调整置信度
                    explanation=f"Similar to historical incident {incident.id}",
                    evidence=[f"Historical pattern match (similarity: {similarity:.2f})"],
                    impact_score=0.7,
                    severity=RCASeverity.MEDIUM,
                )
                hypotheses.append(hypothesis)

        logger.info(f"Found {len(hypotheses)} pattern-based hypotheses")
        return hypotheses

    async def _perform_causal_analysis(
        self, anomaly_nodes: Set[str], context: Optional[Dict]
    ) -> List[RootCauseHypothesis]:
        """因果分析"""
        logger.info("Performing causal analysis")

        hypotheses = []

        # 在因果图中向上游追溯
        for anomaly_node in anomaly_nodes:
            upstream_nodes = self._find_upstream_causes(anomaly_node)

            for upstream_node in upstream_nodes:
                # 计算因果强度
                strength = self.causal_strength.get((upstream_node, anomaly_node), 0.5)

                # 检查上游节点是否也有异常
                is_anomalous = upstream_node in anomaly_nodes

                confidence = strength * (1.2 if is_anomalous else 0.8)

                hypothesis = RootCauseHypothesis(
                    node_id=upstream_node,
                    confidence=min(confidence, 1.0),
                    explanation=f"Upstream cause of {anomaly_node} with strength {strength:.2f}",
                    evidence=[f"Causal link: {upstream_node} -> {anomaly_node}"],
                    impact_score=strength,
                    severity=RCASeverity.HIGH if strength > 0.7 else RCASeverity.MEDIUM,
                )
                hypotheses.append(hypothesis)

        logger.info(f"Generated {len(hypotheses)} causal hypotheses")
        return hypotheses

    async def _perform_topology_analysis(
        self, anomaly_nodes: Set[str], context: Optional[Dict]
    ) -> List[RootCauseHypothesis]:
        """拓扑感知分析"""
        logger.info("Performing topology analysis")

        hypotheses = []

        # 分析拓扑中的关键节点
        critical_nodes = await self._identify_critical_nodes()

        for node in critical_nodes:
            if node in anomaly_nodes:
                # 检查是否是单点故障
                if await self._is_single_point_of_failure(node):
                    hypothesis = RootCauseHypothesis(
                        node_id=node,
                        confidence=0.9,
                        explanation="Critical single point of failure",
                        evidence=["Single point of failure detected"],
                        impact_score=1.0,
                        severity=RCASeverity.CRITICAL,
                    )
                    hypotheses.append(hypothesis)

        # 分析依赖链
        dependency_chains = await self._analyze_dependency_chains(anomaly_nodes)

        for chain in dependency_chains:
            # 链的起点可能是根因
            if chain:
                hypothesis = RootCauseHypothesis(
                    node_id=chain[0],
                    confidence=0.75,
                    explanation=f"Start of dependency chain affecting {len(chain)} nodes",
                    evidence=[f"Dependency chain: {' -> '.join(chain)}"],
                    impact_score=len(chain) / 10.0,
                    severity=RCASeverity.HIGH,
                )
                hypotheses.append(hypothesis)

        logger.info(f"Generated {len(hypotheses)} topology hypotheses")
        return hypotheses

    async def _perform_ml_analysis(
        self, anomaly_nodes: Set[str], context: Optional[Dict]
    ) -> List[RootCauseHypothesis]:
        """ML分析"""
        logger.info("Performing ML analysis")

        if not ML_AVAILABLE or not self.rca_classifier:
            return []

        if not hasattr(self.rca_classifier, "classes_"):
            # The classifier has not been trained on historical incidents yet.
            logger.debug("RCA classifier not trained; skipping ML analysis")
            return []

        features = self._extract_ml_features(anomaly_nodes, context)
        try:
            proba = self.rca_classifier.predict_proba([features])[0]
            classes = list(self.rca_classifier.classes_)
            best_index = max(range(len(proba)), key=lambda i: proba[i])
            node_id = str(classes[best_index])
            confidence = float(proba[best_index])
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"ML analysis failed: {exc}")
            return []

        return [
            RootCauseHypothesis(
                node_id=node_id,
                confidence=confidence,
                explanation=f"ML model predicted {node_id} as root cause",
                evidence=[f"features={features}"],
                impact_score=confidence,
                severity=RCASeverity.HIGH if confidence >= 0.75 else RCASeverity.MEDIUM,
            )
        ]

    async def _combine_hypotheses(self, *hypothesis_lists) -> List[RootCauseHypothesis]:
        """综合多个来源的假设"""
        all_hypotheses = []
        for hypotheses in hypothesis_lists:
            all_hypotheses.extend(hypotheses)

        # 按节点ID分组并合并
        grouped_hypotheses = defaultdict(list)
        for hypothesis in all_hypotheses:
            grouped_hypotheses[hypothesis.node_id].append(hypothesis)

        # 合并相同节点的假设
        combined = []
        for node_id, hypotheses in grouped_hypotheses.items():
            if len(hypotheses) == 1:
                combined.append(hypotheses[0])
            else:
                # 合并多个假设
                combined_confidence = max(h.confidence for h in hypotheses)
                combined_evidence = []
                for h in hypotheses:
                    combined_evidence.extend(h.evidence)

                combined_hypothesis = RootCauseHypothesis(
                    node_id=node_id,
                    confidence=min(combined_confidence * 1.1, 1.0),  # 多个来源支持，增加置信度
                    explanation="Multiple analysis methods support this root cause",
                    evidence=combined_evidence,
                    impact_score=max(h.impact_score for h in hypotheses),
                    severity=max(
                        (h.severity for h in hypotheses),
                        key=lambda s: RCASeverity.__members__.keys(),
                    ),
                )
                combined.append(combined_hypothesis)

        return combined

    async def _rank_hypotheses(
        self, hypotheses: List[RootCauseHypothesis]
    ) -> List[RootCauseHypothesis]:
        """排序假设"""

        # 综合考虑置信度、影响程度、严重程度
        def score(hypothesis):
            return (
                hypothesis.confidence * 0.5
                + hypothesis.impact_score * 0.3
                + self._severity_score(hypothesis.severity) * 0.2
            )

        ranked = sorted(hypotheses, key=score, reverse=True)
        return ranked

    def _severity_score(self, severity: RCASeverity) -> float:
        """严重程度分数"""
        scores = {
            RCASeverity.CRITICAL: 1.0,
            RCASeverity.HIGH: 0.8,
            RCASeverity.MEDIUM: 0.6,
            RCASeverity.LOW: 0.4,
        }
        return scores.get(severity, 0.5)

    async def predict_root_causes(self, current_state: Dict[str, Any]) -> List[RootCauseHypothesis]:
        """根因预测

        基于当前状态预测可能的未来根因
        """
        logger.info("Predicting potential root causes")

        # 分析当前状态趋势
        trends = await self._analyze_state_trends(current_state)

        # 基于趋势预测可能的故障点
        predicted_failures = await self._predict_potential_failures(trends)

        # 生成预测假设
        hypotheses = []
        for failure in predicted_failures:
            hypothesis = RootCauseHypothesis(
                node_id=failure["node"],
                confidence=failure["probability"],
                explanation="Predicted potential failure based on trend analysis",
                evidence=[f"Trend: {failure['trend']}"],
                impact_score=failure["impact"],
                severity=RCASeverity.HIGH,
                predicted_impact=failure.get("predicted_impact"),
            )
            hypotheses.append(hypothesis)

        logger.info(f"Generated {len(hypotheses)} predictive hypotheses")
        return hypotheses

    async def verify_root_cause(self, hypothesis: RootCauseHypothesis) -> bool:
        """验证根因假设"""
        logger.info(f"Verifying root cause hypothesis for {hypothesis.node_id}")

        # 收集验证证据
        evidence = await self._collect_verification_evidence(hypothesis)

        # 评估证据
        verification_score = await self._evaluate_verification_evidence(evidence)

        # 更新验证状态
        if verification_score > 0.7:
            hypothesis.verification_status = "verified"
            hypothesis.confidence = min(hypothesis.confidence * 1.1, 1.0)
            return True
        else:
            hypothesis.verification_status = "rejected"
            return False

    async def _collect_verification_evidence(self, hypothesis: RootCauseHypothesis) -> List[str]:
        """收集验证证据"""
        evidence = []

        # 检查节点状态
        if hypothesis.node_id in self.nodes:
            node = self.nodes[hypothesis.node_id]
            if node.health_status != "healthy":
                evidence.append(f"Node {hypothesis.node_id} is {node.health_status}")

        # 检查相关指标
        # (实现指标检查逻辑)

        # 检查日志
        # (实现日志检查逻辑)

        return evidence

    async def _evaluate_verification_evidence(self, evidence: List[str]) -> float:
        """评估验证证据"""
        if not evidence:
            return 0.0

        # 简单评估：证据数量越多，验证分数越高
        return min(len(evidence) / 5.0, 1.0)

    async def _load_historical_incidents(self):
        """加载历史事故数据"""
        logger.info("Loading historical incidents")
        # 实现历史数据加载逻辑

    async def record_incident(self, incident: HistoricalIncident):
        """记录新事故"""
        self.historical_incidents.append(incident)

        # 更新模式索引
        pattern_key = incident.similarity_hash
        self.pattern_index[pattern_key].append(incident)

        # 限制历史数据数量
        if len(self.historical_incidents) > self.max_historical_incidents:
            oldest = self.historical_incidents.pop(0)
            self.pattern_index[oldest.similarity_hash].remove(oldest)

    def _extract_features(self, anomaly_nodes: Set[str], context: Optional[Dict]) -> Dict[str, Any]:
        """提取特征"""
        features = {
            "node_count": len(anomaly_nodes),
            "node_types": self._get_node_types(anomaly_nodes),
            "timestamp": datetime.now().isoformat(),
        }
        if context:
            features.update(context)
        return features

    def _generate_similarity_hash(self, features: Dict[str, Any]) -> str:
        """生成相似度哈希"""
        feature_str = json.dumps(features, sort_keys=True)
        return hashlib.sha256(feature_str.encode()).hexdigest()

    def _calculate_pattern_similarity(self, hash1: str, hash2: str) -> float:
        """计算模式相似度"""
        # 简单实现：哈希相同则为1.0，否则为0
        # 实际可以使用更复杂的相似度计算
        return 1.0 if hash1 == hash2 else 0.0

    def _find_upstream_causes(self, node: str) -> List[str]:
        """查找上游原因"""
        upstream = []
        visited = set()

        def dfs(current_node):
            if current_node in visited:
                return
            visited.add(current_node)

            for neighbor in self.causal_graph.get(current_node, set()):
                if neighbor not in visited:
                    upstream.append(neighbor)
                    dfs(neighbor)

        dfs(node)
        return upstream

    async def _identify_critical_nodes(self) -> List[str]:
        """识别关键节点（基于因果图的度中心性）。"""
        if not self.causal_graph:
            return []

        degree: Dict[str, int] = defaultdict(int)
        for source, targets in self.causal_graph.items():
            degree[source] += len(targets)
            for target in targets:
                degree[target] += 1

        if not degree:
            return []

        values = list(degree.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        threshold = mean + std if std > 0 else mean

        critical = [node for node, deg in degree.items() if deg >= threshold and deg > 0]
        critical.sort(key=lambda n: degree[n], reverse=True)
        return critical

    async def _is_single_point_of_failure(self, node: str) -> bool:
        """检查 node 是否为单点故障（存在仅能经其到达的下游节点）。"""
        if node not in self.causal_graph and not any(
            node in targets for targets in self.causal_graph.values()
        ):
            return False

        # Predecessor map (incoming causal edges).
        predecessors: Dict[str, Set[str]] = defaultdict(set)
        for source, targets in self.causal_graph.items():
            for target in targets:
                predecessors[target].add(source)

        successors = self.causal_graph.get(node, set())
        for successor in successors:
            # A successor is dependent solely on ``node`` when node is its only
            # (causal) predecessor other than itself.
            others = {p for p in predecessors.get(successor, set()) if p != node}
            if not others:
                return True
        return False

    async def _analyze_dependency_chains(self, anomaly_nodes: Set[str]) -> List[List[str]]:
        """分析从异常节点出发的依赖链（因果图 DFS）。"""
        chains: List[List[str]] = []
        max_depth = 20

        def dfs(current: str, path: List[str]) -> None:
            successors = self.causal_graph.get(current, set())
            extended = False
            for successor in sorted(successors):
                if successor in path or len(path) >= max_depth:
                    continue
                extended = True
                dfs(successor, path + [successor])
            if not extended and len(path) > 1:
                chains.append(path)

        for node in anomaly_nodes:
            dfs(node, [node])

        return chains

    def _extract_ml_features(
        self, anomaly_nodes: Set[str], context: Optional[Dict]
    ) -> List[float]:
        """提取ML特征（规模、类型分布、上下文数值）。"""
        total_edges = sum(len(t) for t in self.causal_graph.values())
        anomalous_types = self._get_node_types(anomaly_nodes)
        type_diversity = len(set(anomalous_types))
        critical_count = sum(
            1 for n in anomaly_nodes if self.causal_graph.get(n)
        )
        context_numeric = [
            float(v)
            for v in (context or {}).values()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        avg_context = sum(context_numeric) / len(context_numeric) if context_numeric else 0.0
        return [
            float(len(anomaly_nodes)),
            float(len(self.nodes)),
            float(total_edges),
            float(type_diversity),
            float(critical_count),
            avg_context,
        ]

    def _generate_analysis_key(self, anomaly_nodes: Set[str], context: Optional[Dict]) -> str:
        """生成分析键"""
        nodes_str = "|".join(sorted(anomaly_nodes))
        context_str = json.dumps(context, sort_keys=True) if context else ""
        return hashlib.sha256(f"{nodes_str}_{context_str}".encode()).hexdigest()

    def _get_node_types(self, nodes: Set[str]) -> List[str]:
        """获取节点类型"""
        types = []
        for node in nodes:
            if node in self.nodes:
                types.append(self.nodes[node].type)
        return types

    async def _analyze_state_trends(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析状态趋势（基于真实采集的状态快照序列）。"""
        self._state_snapshots.append(
            {"ts": datetime.now().isoformat(), "state": dict(current_state)}
        )
        if len(self._state_snapshots) < 2:
            return []

        first = self._state_snapshots[0]["state"]
        last = self._state_snapshots[-1]["state"]
        trends: List[Dict[str, Any]] = []
        for key, last_value in last.items():
            if not isinstance(last_value, (int, float)) or isinstance(last_value, bool):
                continue
            first_value = first.get(key)
            if not isinstance(first_value, (int, float)) or isinstance(first_value, bool):
                continue
            delta = last_value - first_value
            direction = "stable"
            if delta > 0:
                direction = "increasing"
            elif delta < 0:
                direction = "decreasing"
            trends.append(
                {
                    "metric": key,
                    "first": first_value,
                    "last": last_value,
                    "delta": delta,
                    "direction": direction,
                    "samples": len(self._state_snapshots),
                }
            )
        return trends

    async def _predict_potential_failures(
        self, trends: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基于趋势预测潜在故障（数值持续上升且增幅显著时预警）。"""
        predictions: List[Dict[str, Any]] = []
        for trend in trends:
            if trend.get("direction") != "increasing":
                continue
            first = trend.get("first")
            delta = trend.get("delta", 0)
            if not first:
                continue
            change_ratio = delta / abs(first)
            if change_ratio >= 0.5:
                predictions.append(
                    {
                        "metric": trend["metric"],
                        "current": trend["last"],
                        "predicted_direction": "increasing",
                        "change_ratio": change_ratio,
                        "severity": "high" if change_ratio >= 1.0 else "medium",
                    }
                )
        return predictions

    async def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(edges) for edges in self.edges.values()),
            "historical_incidents": len(self.historical_incidents),
            "recent_analyses": len(self.recent_analyses),
            "topology_changes": len(self.topology_changes),
        }


# 全局实例
enhanced_root_cause_analyzer = EnhancedRootCauseAnalyzer()
