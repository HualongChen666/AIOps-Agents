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
        """从配置文件发现节点"""
        # 实现配置文件解析逻辑
        nodes: List[TopologyNode] = []
        # 示例：解析应用配置、部署配置等
        return nodes

    async def _discover_from_service_registry(self) -> List[TopologyNode]:
        """从服务注册中心发现节点"""
        # 实现服务注册中心查询逻辑
        nodes: List[TopologyNode] = []
        # 示例：查询Consul、Eureka、Kubernetes等
        return nodes

    async def _discover_from_database_metadata(self) -> List[TopologyNode]:
        """从数据库元数据发现节点"""
        # 实现数据库元数据查询逻辑
        nodes: List[TopologyNode] = []
        # 示例：查询数据库、表、存储过程等
        return nodes

    async def _discover_from_monitoring(self) -> List[TopologyNode]:
        """从监控数据发现节点"""
        # 实现监控数据分析逻辑
        nodes: List[TopologyNode] = []
        # 示例：分析Prometheus指标、日志等
        return nodes

    async def _discover_edges_from_config(self) -> List[TopologyEdge]:
        """从配置发现边"""
        # 实现配置边发现逻辑
        edges: List[TopologyEdge] = []
        return edges

    async def _discover_edges_from_traces(self) -> List[TopologyEdge]:
        """从追踪数据发现边"""
        # 实现追踪数据分析逻辑
        edges: List[TopologyEdge] = []
        # 示例：分析Jaeger、Zipkin等追踪数据
        return edges

    async def _discover_edges_from_database_queries(self) -> List[TopologyEdge]:
        """从数据库查询发现边"""
        # 实现数据库查询分析逻辑
        edges: List[TopologyEdge] = []
        return edges

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
        """检测拓扑变更"""
        changes = []

        # 检测节点变更
        new_node_ids = {node.id for node in new_nodes}
        existing_node_ids = set(self.nodes.keys())

        added_nodes = new_node_ids - existing_node_ids
        removed_nodes = existing_node_ids - new_node_ids

        for node_id in added_nodes:
            changes.append(
                TopologyChange(
                    change_type=TopologyChangeType.ADD_NODE,
                    timestamp=datetime.now(),
                    details={"node_id": node_id},
                )
            )

        for node_id in removed_nodes:
            changes.append(
                TopologyChange(
                    change_type=TopologyChangeType.REMOVE_NODE,
                    timestamp=datetime.now(),
                    details={"node_id": node_id},
                )
            )

        # 检测边变更
        # 类似逻辑...

        return changes

    async def _apply_topology_change(self, change: TopologyChange):
        """应用拓扑变更"""
        if change.change_type == TopologyChangeType.ADD_NODE:
            # 添加节点逻辑
            pass
        elif change.change_type == TopologyChangeType.REMOVE_NODE:
            # 移除节点逻辑
            pass
        # 其他变更类型...

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
        """添加跨层级因果关系"""
        # 实现跨层级因果关系逻辑
        # 例如：基础设施层 -> 应用层 -> 业务层

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

        # 提取特征
        # features = self._extract_ml_features(anomaly_nodes, context)

        # 使用训练好的模型预测
        # (这里需要模型训练逻辑)

        return []

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
        return hashlib.md5(feature_str.encode(), usedforsecurity=False).hexdigest()

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
        """识别关键节点"""
        # 实现关键节点识别逻辑
        # 可以使用度中心性、介数中心性等图算法
        return []

    async def _is_single_point_of_failure(self, node: str) -> bool:
        """检查是否是单点故障"""
        # 实现单点故障检查逻辑
        return False

    async def _analyze_dependency_chains(self, anomaly_nodes: Set[str]) -> List[List[str]]:
        """分析依赖链"""
        chains: List[List[str]] = []
        # 实现依赖链分析逻辑
        return chains

    def _extract_ml_features(self, anomaly_nodes: Set[str], context: Optional[Dict]) -> List[float]:
        """提取ML特征"""
        # 实现特征提取逻辑
        return []

    def _generate_analysis_key(self, anomaly_nodes: Set[str], context: Optional[Dict]) -> str:
        """生成分析键"""
        nodes_str = "|".join(sorted(anomaly_nodes))
        context_str = json.dumps(context, sort_keys=True) if context else ""
        return hashlib.md5(f"{nodes_str}_{context_str}".encode(), usedforsecurity=False).hexdigest()

    def _get_node_types(self, nodes: Set[str]) -> List[str]:
        """获取节点类型"""
        types = []
        for node in nodes:
            if node in self.nodes:
                types.append(self.nodes[node].type)
        return types

    async def _analyze_state_trends(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析状态趋势"""
        # 实现趋势分析逻辑
        return []

    async def _predict_potential_failures(
        self, trends: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """预测潜在故障"""
        # 实现故障预测逻辑
        return []

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
