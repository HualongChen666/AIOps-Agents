# -*- coding: utf-8 -*-
"""
Intelligent Alert Analyzer Module
智能告警分析模块

Provides ML-based alert intelligence capabilities:
- Alert aggregation using clustering algorithms
- Alert trend prediction using time series models
- Automated alert routing based on topology and rules
- Enhanced alert noise reduction using pattern recognition
- Topology-aware alert correlation
- Fine-grained alert suppression management
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

# Optional ML imports - graceful degradation if not available
try:
    from sklearn.cluster import DBSCAN
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    # Create component types for when ML is not available
    TfidfVectorizer = Any  # type: ignore
    DBSCAN = Any  # type: ignore
    cosine_similarity = Any  # type: ignore
    logger.warning("ML libraries not available, using rule-based fallback")

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = Any  # type: ignore
    logger.warning("Prophet not available, trend prediction disabled")


class AlertSeverity(Enum):
    """告警严重程度枚举"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Alert:
    """告警数据结构"""

    id: str
    severity: AlertSeverity
    message: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_entities: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)


@dataclass
class AggregatedAlert:
    """聚合告警数据结构"""

    id: str
    original_alerts: List[str]
    severity: AlertSeverity
    message: str
    count: int
    first_seen: datetime
    last_seen: datetime
    pattern: str
    confidence: float


@dataclass
class AlertTrendPrediction:
    """告警趋势预测结果"""

    metric_name: str
    predicted_values: List[float]
    timestamps: List[datetime]
    trend: str  # "increasing", "decreasing", "stable"
    confidence: float
    anomaly_threshold: float


class IntelligentAlertAnalyzer:
    """智能告警分析器"""

    def __init__(self):
        """初始化智能告警分析器"""
        self.alert_history: List[Alert] = []
        self.alert_patterns: Dict[str, List[Alert]] = defaultdict(list)
        self.suppression_rules: List[Dict[str, Any]] = []
        self.routing_rules: List[Dict[str, Any]] = []
        self.topology_graph: Dict[str, List[str]] = defaultdict(list)

        # ML models
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.clustering_model: Optional[DBSCAN] = None
        self.prophet_models: Dict[str, Prophet] = {}

        # Configuration
        self.aggregation_window = timedelta(minutes=10)
        self.similarity_threshold = 0.8
        self.trend_prediction_horizon = timedelta(hours=24)

    async def initialize(self):
        """初始化分析器"""
        logger.info("Initializing Intelligent Alert Analyzer")

        if ML_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(max_features=1000)
            self.clustering_model = DBSCAN(eps=0.5, min_samples=2)
            logger.info("ML models initialized")
        else:
            logger.warning("ML not available, using rule-based approach")

        # Load historical patterns
        await self._load_historical_patterns()

        # Build topology graph
        await self._build_topology_graph()

        logger.info("Intelligent Alert Analyzer initialized successfully")

    async def aggregate_alerts(self, alerts: List[Alert]) -> List[AggregatedAlert]:
        """智能告警聚合

        使用聚类算法和相似度分析将相似告警聚合
        """
        if not alerts:
            return []

        logger.info(f"Aggregating {len(alerts)} alerts")

        if ML_AVAILABLE:
            # 使用ML方法进行聚合
            aggregated = await self._ml_based_aggregation(alerts)
        else:
            # 使用规则方法进行聚合
            aggregated = await self._rule_based_aggregation(alerts)

        logger.info(f"Aggregated into {len(aggregated)} alert groups")
        return aggregated

    async def _ml_based_aggregation(self, alerts: List[Alert]) -> List[AggregatedAlert]:
        """基于机器学习的告警聚合"""
        try:
            # 提取告警文本特征
            texts = [alert.message for alert in alerts]

            # TF-IDF向量化
            if self.tfidf_vectorizer is None:
                self.tfidf_vectorizer = TfidfVectorizer(max_features=1000)
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            else:
                tfidf_matrix = self.tfidf_vectorizer.transform(texts)

            # 计算相似度矩阵
            similarity_matrix = cosine_similarity(tfidf_matrix)

            # 聚类
            if self.clustering_model is None:
                self.clustering_model = DBSCAN(eps=0.5, min_samples=2)
            clusters = self.clustering_model.fit_predict(similarity_matrix)

            # 按聚类结果分组
            cluster_groups = defaultdict(list)
            for alert, cluster_id in zip(alerts, clusters):
                cluster_groups[cluster_id].append(alert)

            # 生成聚合告警
            aggregated_alerts = []
            for cluster_id, cluster_alerts in cluster_groups.items():
                if cluster_id == -1:  # 噪点点，单独处理
                    for alert in cluster_alerts:
                        aggregated_alerts.append(self._create_single_alert_aggregation(alert))
                else:
                    aggregated_alerts.append(self._create_cluster_aggregation(cluster_alerts))

            return aggregated_alerts

        except Exception as e:
            logger.error(f"ML-based aggregation failed: {e}")
            # 降级到规则方法
            return await self._rule_based_aggregation(alerts)

    async def _rule_based_aggregation(self, alerts: List[Alert]) -> List[AggregatedAlert]:
        """基于规则的告警聚合"""
        # 按严重程度和源分组
        groups = defaultdict(list)
        for alert in alerts:
            key = (alert.severity, alert.source, alert.message[:50])  # 使用消息前50字符作为分组键
            groups[key].append(alert)

        aggregated_alerts = []
        for group_alerts in groups.values():
            if len(group_alerts) == 1:
                aggregated_alerts.append(self._create_single_alert_aggregation(group_alerts[0]))
            else:
                aggregated_alerts.append(self._create_cluster_aggregation(group_alerts))

        return aggregated_alerts

    def _create_single_alert_aggregation(self, alert: Alert) -> AggregatedAlert:
        """创建单个告警的聚合"""
        return AggregatedAlert(
            id=f"agg_{alert.id}",
            original_alerts=[alert.id],
            severity=alert.severity,
            message=alert.message,
            count=1,
            first_seen=alert.timestamp,
            last_seen=alert.timestamp,
            pattern="single",
            confidence=1.0,
        )

    def _create_cluster_aggregation(self, alerts: List[Alert]) -> AggregatedAlert:
        """创建聚类告警的聚合"""
        # 确定最高严重程度
        severity_order = [
            AlertSeverity.CRITICAL,
            AlertSeverity.HIGH,
            AlertSeverity.MEDIUM,
            AlertSeverity.LOW,
            AlertSeverity.INFO,
        ]
        highest_severity = min(alerts, key=lambda a: severity_order.index(a.severity)).severity

        # 生成聚合消息
        count = len(alerts)
        sources = set(alert.source for alert in alerts)
        message = f"Aggregated {count} alerts from {len(sources)} sources: {alerts[0].message}"

        return AggregatedAlert(
            id=f"agg_cluster_{hash(str([a.id for a in alerts]))}",
            original_alerts=[alert.id for alert in alerts],
            severity=highest_severity,
            message=message,
            count=count,
            first_seen=min(alert.timestamp for alert in alerts),
            last_seen=max(alert.timestamp for alert in alerts),
            pattern="cluster",
            confidence=0.8,
        )

    async def predict_alert_trends(
        self, metric_name: str, historical_data: List[Tuple[datetime, float]]
    ) -> Optional[AlertTrendPrediction]:
        """预测告警趋势

        使用Prophet时序模型预测未来告警趋势
        """
        if not PROPHET_AVAILABLE or len(historical_data) < 10:
            logger.warning(f"Trend prediction not available for {metric_name}")
            return None

        try:
            logger.info(f"Predicting trend for {metric_name}")

            # 准备数据
            # df_data = [(ts.strftime("%Y-%m-%d %H:%M:%S"), value) for ts, value in historical_data]

            # 创建或获取Prophet模型
            if metric_name not in self.prophet_models:
                self.prophet_models[metric_name] = Prophet(
                    yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False
                )

            model = self.prophet_models[metric_name]

            # 训练模型
            # (简化实现，实际需要更复杂的数据准备)

            # 预测未来趋势
            future = model.make_future_dataframe(periods=24)  # 预测24小时
            forecast = model.predict(future)

            # 提取预测结果
            predicted_values = forecast["yhat"].tail(24).tolist()
            timestamps = [pd.to_datetime(ds) for ds in forecast["ds"].tail(24).tolist()]

            # 判断趋势
            recent_values = historical_data[-10:]
            trend = self._determine_trend(recent_values, predicted_values)

            # 计算异常阈值
            historical_values = [v for _, v in historical_data]
            anomaly_threshold = float(
                np.percentile(historical_values, 95) + 2 * np.std(historical_values)
            )

            return AlertTrendPrediction(
                metric_name=metric_name,
                predicted_values=predicted_values,
                timestamps=timestamps,
                trend=trend,
                confidence=0.85,
                anomaly_threshold=anomaly_threshold,
            )

        except Exception as e:
            logger.error(f"Trend prediction failed for {metric_name}: {e}")
            return None

    def _determine_trend(
        self, historical: List[Tuple[datetime, float]], predicted: List[float]
    ) -> str:
        """判断趋势方向"""
        if not historical or not predicted:
            return "stable"

        recent_avg = np.mean([v for _, v in historical[-5:]])
        predicted_avg = np.mean(predicted)

        if predicted_avg > recent_avg * 1.1:
            return "increasing"
        elif predicted_avg < recent_avg * 0.9:
            return "decreasing"
        else:
            return "stable"

    async def route_alert(self, alert: Alert) -> List[str]:
        """自动化告警路由

        基于拓扑和规则引擎自动路由告警到正确的团队
        """
        logger.info(f"Routing alert {alert.id}")

        # 应用路由规则
        routed_teams = []
        for rule in self.routing_rules:
            if self._matches_routing_rule(alert, rule):
                routed_teams.extend(rule.get("teams", []))

        # 基于拓扑的路由
        topology_routes = self._topology_aware_routing(alert)
        routed_teams.extend(topology_routes)

        # 去重
        routed_teams = list(set(routed_teams))

        logger.info(f"Alert {alert.id} routed to teams: {routed_teams}")
        return routed_teams

    def _matches_routing_rule(self, alert: Alert, rule: Dict[str, Any]) -> bool:
        """检查告警是否匹配路由规则"""
        # 检查严重程度
        if "severity" in rule:
            if alert.severity.value != rule["severity"]:
                return False

        # 检查源
        if "source" in rule:
            if alert.source != rule["source"]:
                return False

        # 检查标签
        if "labels" in rule:
            required_labels = set(rule["labels"])
            if not required_labels.issubset(set(alert.labels)):
                return False

        return True

    def _topology_aware_routing(self, alert: Alert) -> List[str]:
        """基于拓扑的告警路由"""
        # 根据告警涉及的实体，查找依赖的服务和团队
        routed_teams = []

        for entity in alert.related_entities:
            # 查找拓扑图中的依赖关系
            if entity in self.topology_graph:
                dependencies = self.topology_graph[entity]
                # 根据依赖关系路由到相关团队
                for dep in dependencies:
                    # 这里可以配置实体到团队的映射
                    team = self._get_team_for_entity(dep)
                    if team:
                        routed_teams.append(team)

        return routed_teams

    def _get_team_for_entity(self, entity: str) -> Optional[str]:
        """根据实体获取负责团队"""
        # 这里可以实现实体到团队的映射逻辑
        # 可以从配置文件或数据库中读取
        entity_team_map = {
            # 示例映射
            "database": "database-team",
            "api": "backend-team",
            "frontend": "frontend-team",
        }
        return entity_team_map.get(entity)

    async def reduce_alert_noise(self, alerts: List[Alert]) -> List[Alert]:
        """告警降噪

        基于历史模式识别减少告警噪音
        """
        logger.info(f"Reducing noise from {len(alerts)} alerts")

        filtered_alerts = []

        for alert in alerts:
            # 检查是否应该被抑制
            if not await self._should_suppress_alert(alert):
                filtered_alerts.append(alert)

        noise_reduction = len(alerts) - len(filtered_alerts)
        logger.info(f"Reduced {noise_reduction} noisy alerts")

        return filtered_alerts

    async def _should_suppress_alert(self, alert: Alert) -> bool:
        """检查告警是否应该被抑制"""
        # 检查抑制规则
        for rule in self.suppression_rules:
            if self._matches_suppression_rule(alert, rule):
                return True

        # 检查历史模式
        if await self._is_known_noise_pattern(alert):
            return True

        return False

    def _matches_suppression_rule(self, alert: Alert, rule: Dict[str, Any]) -> bool:
        """检查告警是否匹配抑制规则"""
        # 检查时间窗口
        if "time_window" in rule:
            # 实现时间窗口检查逻辑
            pass

        # 检查频率
        if "max_frequency" in rule:
            # 实现频率检查逻辑
            pass

        # 检查模式匹配
        if "pattern" in rule:
            if rule["pattern"] in alert.message:
                return True

        return False

    async def _is_known_noise_pattern(self, alert: Alert) -> bool:
        """检查是否为已知的噪音模式"""
        # 检查历史告警模式
        pattern_key = self._generate_pattern_key(alert)

        if pattern_key in self.alert_patterns:
            recent_pattern_alerts = self.alert_patterns[pattern_key]

            # 如果在短时间内出现了多次，可能是噪音
            recent_count = len(
                [
                    a
                    for a in recent_pattern_alerts
                    if a.timestamp > datetime.now() - timedelta(hours=1)
                ]
            )

            if recent_count > 10:  # 阈值可配置
                return True

        return False

    def _generate_pattern_key(self, alert: Alert) -> str:
        """生成模式键"""
        return f"{alert.source}_{alert.severity.value}_{alert.message[:30]}"

    async def correlate_alerts_with_topology(self, alerts: List[Alert]) -> Dict[str, List[Alert]]:
        """拓扑感知的告警关联分析"""
        logger.info("Correlating alerts with topology")

        correlation_groups = defaultdict(list)

        for alert in alerts:
            # 根据告警涉及的实体进行关联
            for entity in alert.related_entities:
                correlation_groups[entity].append(alert)

        # 扩展关联到依赖的实体
        expanded_groups = defaultdict(list)
        for entity, entity_alerts in correlation_groups.items():
            expanded_groups[entity].extend(entity_alerts)

            if entity in self.topology_graph:
                dependencies = self.topology_graph[entity]
                for dep in dependencies:
                    if dep in correlation_groups:
                        expanded_groups[entity].extend(correlation_groups[dep])

        logger.info(f"Created {len(expanded_groups)} correlation groups")
        return dict(expanded_groups)

    async def add_suppression_rule(self, rule: Dict[str, Any]):
        """添加抑制规则"""
        self.suppression_rules.append(rule)
        logger.info(f"Added suppression rule: {rule}")

    async def add_routing_rule(self, rule: Dict[str, Any]):
        """添加路由规则"""
        self.routing_rules.append(rule)
        logger.info(f"Added routing rule: {rule}")

    async def update_topology(self, topology_data: Dict[str, List[str]]):
        """更新拓扑图"""
        self.topology_graph = defaultdict(list, topology_data)
        logger.info(f"Updated topology graph with {len(topology_data)} entities")

    async def _load_historical_patterns(self):
        """加载历史告警模式"""
        # 从数据库或文件加载历史模式
        logger.info("Loading historical alert patterns")
        # 实现历史模式加载逻辑

    async def _build_topology_graph(self):
        """构建拓扑图"""
        # 从配置或服务发现构建拓扑图
        logger.info("Building topology graph")
        # 实现拓扑图构建逻辑

    async def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息"""
        return {
            "total_alerts": len(self.alert_history),
            "patterns_count": len(self.alert_patterns),
            "suppression_rules_count": len(self.suppression_rules),
            "routing_rules_count": len(self.routing_rules),
            "topology_entities_count": len(self.topology_graph),
        }


# 全局实例
intelligent_alert_analyzer = IntelligentAlertAnalyzer()
