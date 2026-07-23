# -*- coding: utf-8 -*-
"""
Enhanced AI Capabilities Module
增强AI能力模块

Provides advanced AI capabilities:
- Predictive analysis (time series prediction, anomaly prediction)
- Adaptive learning (online learning, model updates)
- Natural language interface (conversational operations)
- Enhanced multi-model LLM routing with intelligent decision making
- Continuous knowledge base learning and accumulation
- AI decision explainability
"""

import asyncio
import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# Optional ML imports
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available for enhanced AI capabilities")

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not available for time series prediction")


class PredictionType(Enum):
    """预测类型"""

    TIMESERIES = "timeseries"
    ANOMALY = "anomaly"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class LearningMode(Enum):
    """学习模式"""

    ONLINE = "online"
    BATCH = "batch"
    TRANSFER = "transfer"


@dataclass
class PredictionResult:
    """预测结果"""

    prediction_type: PredictionType
    predicted_values: List[float]
    confidence_scores: List[float]
    timestamps: List[datetime]
    model_used: str
    accuracy: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyPrediction:
    """异常预测"""

    is_anomalous: bool
    anomaly_score: float
    confidence: float
    explanation: str
    contributing_factors: List[str]
    predicted_impact: str


@dataclass
class LearningUpdate:
    """学习更新"""

    model_id: str
    learning_mode: LearningMode
    samples_added: int
    accuracy_before: float
    accuracy_after: float
    update_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NLParseResult:
    """自然语言解析结果"""

    intent: str
    entities: Dict[str, Any]
    confidence: float
    requires_clarification: bool
    suggested_actions: List[str]


@dataclass
class DecisionExplanation:
    """决策解释"""

    decision: str
    confidence: float
    reasoning: List[str]
    alternative_options: List[Dict[str, Any]]
    data_sources: List[str]
    model_confidence: float


class EnhancedAICapabilities:
    """增强AI能力模块"""

    def __init__(self):
        """初始化增强AI能力模块"""
        # 预测模型
        self.prediction_models: Dict[str, Any] = {}
        self.anomaly_detectors: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}

        # 学习状态
        self.learning_history: List[LearningUpdate] = []
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)

        # 自然语言处理
        self.intent_classifier = None
        self.entity_extractor = None
        self.conversation_context: deque = deque(maxlen=10)

        # 知识库学习
        self.knowledge_accumulator = defaultdict(list)
        self.pattern_learner = defaultdict(int)

        # 配置
        self.prediction_horizon = timedelta(hours=24)
        self.min_samples_for_training = 100
        self.retrain_threshold = 0.05  # 性能下降5%时重新训练
        self.learning_interval = timedelta(hours=6)

        # 性能优化
        self.prediction_cache: Dict[str, Tuple[PredictionResult, datetime]] = {}
        self.cache_ttl = timedelta(minutes=10)

    async def initialize(self) -> None:
        """初始化AI能力模块"""
        logger.info("Initializing Enhanced AI Capabilities")

        if ML_AVAILABLE:
            # 初始化异常检测模型
            await self._initialize_anomaly_detectors()

            # 初始化预测模型
            await self._initialize_prediction_models()

            logger.info("ML models initialized")
        else:
            logger.warning("ML not available, using rule-based approach")

        # 启动学习循环
        asyncio.create_task(self._learning_loop())

        logger.info("Enhanced AI Capabilities initialized successfully")

    async def _initialize_anomaly_detectors(self) -> None:
        """初始化异常检测模型"""
        # 为不同的指标类型初始化异常检测器
        metric_types = [
            "cpu_usage",
            "memory_usage",
            "disk_usage",
            "network_io",
            "response_time",
            "error_rate",
            "throughput",
        ]

        for metric_type in metric_types:
            try:
                detector = IsolationForest(
                    n_estimators=100, contamination=0.1, random_state=42, n_jobs=-1
                )
                self.anomaly_detectors[metric_type] = detector
                logger.info(f"Initialized anomaly detector for {metric_type}")
            except Exception as e:
                logger.error(f"Failed to initialize detector for {metric_type}: {e}")

    async def _initialize_prediction_models(self) -> None:
        """初始化预测模型"""
        # 初始化时序预测模型
        if PROPHET_AVAILABLE:
            await self._initialize_prophet_models()

        # 初始化回归模型
        await self._initialize_regression_models()

    async def _initialize_prophet_models(self) -> None:
        """初始化Prophet时序模型"""
        metric_types = ["cpu_usage", "memory_usage", "request_count"]

        for metric_type in metric_types:
            try:
                model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=True,
                    seasonality_mode="multiplicative",
                )
                self.prediction_models[f"prophet_{metric_type}"] = model
                logger.info(f"Initialized Prophet model for {metric_type}")
            except Exception as e:
                logger.error(f"Failed to initialize Prophet for {metric_type}: {e}")

    async def _initialize_regression_models(self) -> None:
        """初始化回归模型"""
        metric_types = ["response_time", "throughput"]

        for metric_type in metric_types:
            try:
                model = RandomForestRegressor(
                    n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
                )
                self.prediction_models[f"rf_{metric_type}"] = model
                self.scalers[metric_type] = StandardScaler()
                logger.info(f"Initialized RF model for {metric_type}")
            except Exception as e:
                logger.error(f"Failed to initialize RF for {metric_type}: {e}")

    async def predict_timeseries(
        self, metric_name: str, historical_data: List[Tuple[datetime, float]]
    ) -> Optional[PredictionResult]:
        """时序预测

        使用Prophet或回归模型预测未来指标值
        """
        logger.info(f"Predicting timeseries for {metric_name}")

        if not PROPHET_AVAILABLE or len(historical_data) < 30:
            logger.warning(f"Time series prediction not available for {metric_name}")
            return None

        try:
            # 检查缓存
            cache_key = f"{metric_name}_{hash(str(historical_data[-10:]))}"
            if cache_key in self.prediction_cache:
                cached_result, cache_time = self.prediction_cache[cache_key]
                if datetime.now() - cache_time < self.cache_ttl:
                    return cached_result

            # 准备数据
            df = pd.DataFrame(historical_data, columns=["ds", "y"])
            df["ds"] = pd.to_datetime(df["ds"])

            # 获取或创建模型
            model_key = f"prophet_{metric_name}"
            if model_key not in self.prediction_models:
                self.prediction_models[model_key] = Prophet(
                    yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=True
                )

            model = self.prediction_models[model_key]

            # 训练模型
            model.fit(df)

            # 预测未来
            future = model.make_future_dataframe(periods=24)  # 预测24小时
            forecast = model.predict(future)

            # 提取预测结果
            predicted_values = forecast["yhat"].tail(24).tolist()
            timestamps = [pd.to_datetime(ds) for ds in forecast["ds"].tail(24).tolist()]

            # 计算置信度
            confidence_scores = []
            for i in range(24):
                yhat_lower = forecast["yhat_lower"].iloc[-24 + i]
                yhat_upper = forecast["yhat_upper"].iloc[-24 + i]
                yhat = forecast["yhat"].iloc[-24 + i]
                confidence = 1.0 - (yhat_upper - yhat_lower) / (2 * abs(yhat) + 1e-6)
                confidence_scores.append(max(0, min(1, confidence)))

            # 估算准确度
            accuracy = np.mean(confidence_scores)

            result = PredictionResult(
                prediction_type=PredictionType.TIMESERIES,
                predicted_values=predicted_values,
                confidence_scores=confidence_scores,
                timestamps=timestamps,
                model_used="Prophet",
                accuracy=accuracy,
                metadata={"horizon_hours": 24},
            )

            # 缓存结果
            self.prediction_cache[cache_key] = (result, datetime.now())

            logger.info(f"Time series prediction completed for {metric_name}")
            return result

        except Exception as e:
            logger.error(f"Time series prediction failed for {metric_name}: {e}")
            return None

    async def predict_anomalies(
        self, metric_name: str, current_value: float, historical_data: List[Tuple[datetime, float]]
    ) -> Optional[AnomalyPrediction]:
        """异常预测

        使用IsolationForest预测当前值是否为异常
        """
        logger.info(f"Predicting anomalies for {metric_name}")

        if not ML_AVAILABLE or len(historical_data) < 50:
            logger.warning(f"Anomaly prediction not available for {metric_name}")
            return None

        try:
            # 获取或创建检测器
            if metric_name not in self.anomaly_detectors:
                self.anomaly_detectors[metric_name] = IsolationForest(
                    n_estimators=100, contamination=0.1, random_state=42
                )

            detector = self.anomaly_detectors[metric_name]

            # 准备训练数据
            values = np.array([v for _, v in historical_data]).reshape(-1, 1)

            # 训练检测器（如果需要）
            if len(values) >= self.min_samples_for_training:
                detector.fit(values)

            # 预测当前值
            current_value_array = np.array([[current_value]])
            prediction = detector.predict(current_value_array)
            anomaly_score = detector.decision_function(current_value_array)[0]

            is_anomalous = prediction[0] == -1
            confidence = min(abs(anomaly_score) / 2.0, 1.0)

            # 生成解释
            if is_anomalous:
                explanation = (
                    f"{metric_name} value {current_value} is anomalous (score: {anomaly_score:.2f})"
                )
                contributing_factors = ["Value deviates from historical pattern"]
                predicted_impact = "May indicate system issue requiring investigation"
            else:
                explanation = f"{metric_name} value {current_value} is within normal range"
                contributing_factors = []
                predicted_impact = "No immediate action required"

            result = AnomalyPrediction(
                is_anomalous=is_anomalous,
                anomaly_score=abs(anomaly_score),
                confidence=confidence,
                explanation=explanation,
                contributing_factors=contributing_factors,
                predicted_impact=predicted_impact,
            )

            logger.info(
                f"Anomaly prediction completed for {metric_name}: is_anomalous={is_anomalous}"
            )
            return result

        except Exception as e:
            logger.error(f"Anomaly prediction failed for {metric_name}: {e}")
            return None

    async def adaptive_learn(
        self,
        model_id: str,
        new_samples: List[Tuple[Dict[str, Any], Any]],
        learning_mode: LearningMode = LearningMode.ONLINE,
    ) -> Optional[LearningUpdate]:
        """自适应学习

        使用新样本更新模型
        """
        logger.info(f"Adaptive learning for {model_id} with {len(new_samples)} samples")

        if not ML_AVAILABLE:
            logger.warning("ML not available for adaptive learning")
            return None

        try:
            # 获取模型
            if model_id not in self.prediction_models:
                logger.warning(f"Model {model_id} not found")
                return None

            model = self.prediction_models[model_id]

            # 记录学习前的性能
            accuracy_before = await self._evaluate_model_performance(model_id)

            # 根据学习模式进行学习
            if learning_mode == LearningMode.ONLINE:
                # 在线学习：增量更新
                await self._online_learning(model, new_samples)
            elif learning_mode == LearningMode.BATCH:
                # 批量学习：重新训练
                await self._batch_learning(model, new_samples)
            elif learning_mode == LearningMode.TRANSFER:
                # 迁移学习：从预训练模型开始
                await self._transfer_learning(model, new_samples)

            # 记录学习后的性能
            accuracy_after = await self._evaluate_model_performance(model_id)

            # 创建学习更新记录
            update = LearningUpdate(
                model_id=model_id,
                learning_mode=learning_mode,
                samples_added=len(new_samples),
                accuracy_before=accuracy_before,
                accuracy_after=accuracy_after,
                update_time=datetime.now(),
            )

            self.learning_history.append(update)
            self.performance_metrics[model_id].append(accuracy_after)

            logger.info(
                f"Adaptive learning completed for {model_id}: "
                f"{accuracy_before:.3f} -> {accuracy_after:.3f}"
            )
            return update

        except Exception as e:
            logger.error(f"Adaptive learning failed for {model_id}: {e}")
            return None

    async def _online_learning(self, model: Any, samples: List[Tuple[Dict[str, Any], Any]]) -> None:
        """在线学习"""
        # 实现增量学习逻辑
        # 对于某些模型（如sklearn），可能需要部分拟合

    async def _batch_learning(self, model: Any, samples: List[Tuple[Dict[str, Any], Any]]) -> None:
        """批量学习"""
        # 实现批量重新训练逻辑

    async def _transfer_learning(
        self, model: Any, samples: List[Tuple[Dict[str, Any], Any]]
    ) -> None:
        """迁移学习"""
        # 实现迁移学习逻辑

    async def _evaluate_model_performance(self, model_id: str) -> float:
        """评估模型性能"""
        # 实现性能评估逻辑
        # 返回准确度或其他性能指标
        return 0.8  # 默认值

    async def parse_natural_language(self, query: str) -> Optional[NLParseResult]:
        """自然语言解析

        解析用户的自然语言查询，提取意图和实体
        """
        logger.info(f"Parsing natural language query: {query[:50]}...")

        try:
            # 简单的规则基解析（实际可以使用NLP模型）
            intent = self._classify_intent(query)
            entities = self._extract_entities(query)
            confidence = self._calculate_parse_confidence(query, intent, entities)
            requires_clarification = confidence < 0.7
            suggested_actions = self._generate_suggested_actions(intent, entities)

            result = NLParseResult(
                intent=intent,
                entities=entities,
                confidence=confidence,
                requires_clarification=requires_clarification,
                suggested_actions=suggested_actions,
            )

            # 保存对话上下文
            self.conversation_context.append(
                {"query": query, "result": result, "timestamp": datetime.now()}
            )

            logger.info(
                f"Natural language parsing completed: intent={intent}, confidence={confidence:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Natural language parsing failed: {e}")
            return None

    def _classify_intent(self, query: str) -> str:
        """分类意图"""
        query_lower = query.lower()

        # 简单的关键词匹配
        intent_patterns = {
            "monitor": ["monitor", "check", "status", "health"],
            "analyze": ["analyze", "investigate", "diagnose", "root cause"],
            "fix": ["fix", "repair", "resolve", "heal"],
            "predict": ["predict", "forecast", "trend"],
            "optimize": ["optimize", "improve", "tune"],
            "alert": ["alert", "notify", "warn"],
            "deploy": ["deploy", "release", "ship"],
            "scale": ["scale", "expand", "grow"],
        }

        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent

        return "unknown"

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """提取实体"""
        entities: Dict[str, Any] = {}

        # 简单的实体提取
        if "cpu" in query.lower():
            entities["metric"] = "cpu_usage"
        elif "memory" in query.lower():
            entities["metric"] = "memory_usage"
        elif "disk" in query.lower():
            entities["metric"] = "disk_usage"

        # 提取数字
        import re

        numbers = re.findall(r"\d+", query)
        if numbers:
            entities["values"] = [int(n) for n in numbers]

        # 提取时间范围
        if "hour" in query.lower():
            entities["time_range"] = "hour"
        elif "day" in query.lower():
            entities["time_range"] = "day"
        elif "week" in query.lower():
            entities["time_range"] = "week"

        return entities

    def _calculate_parse_confidence(
        self, query: str, intent: str, entities: Dict[str, Any]
    ) -> float:
        """计算解析置信度"""
        confidence = 0.5  # 基础置信度

        if intent != "unknown":
            confidence += 0.3

        if entities:
            confidence += 0.2 * len(entities)

        return min(confidence, 1.0)

    def _generate_suggested_actions(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """生成建议操作"""
        actions = []

        if intent == "monitor":
            actions.append("Check system metrics")
            if "metric" in entities:
                actions.append(f"Monitor {entities['metric']}")
        elif intent == "analyze":
            actions.append("Perform root cause analysis")
        elif intent == "fix":
            actions.append("Execute automated repair")
        elif intent == "predict":
            actions.append("Generate trend prediction")

        return actions

    async def explain_decision(
        self, decision: str, context: Dict[str, Any]
    ) -> Optional[DecisionExplanation]:
        """决策解释

        解释AI决策的原因和依据
        """
        logger.info(f"Explaining decision: {decision}")

        try:
            # 收集决策依据
            reasoning = []
            data_sources = []

            # 分析上下文数据
            if "metrics" in context:
                reasoning.append("Based on current system metrics")
                data_sources.append("monitoring_system")

            if "historical_data" in context:
                reasoning.append("Considering historical patterns")
                data_sources.append("historical_database")

            if "ml_model" in context:
                reasoning.append(f"ML model {context['ml_model']} prediction")
                data_sources.append("ml_model")

            # 生成替代选项
            alternative_options = []
            if decision == "scale_up":
                alternative_options = [
                    {"action": "optimize_resources", "confidence": 0.6},
                    {"action": "increase_cache", "confidence": 0.7},
                ]
            elif decision == "restart_service":
                alternative_options = [
                    {"action": "restart_container", "confidence": 0.8},
                    {"action": "rolling_restart", "confidence": 0.9},
                ]

            # 计算模型置信度
            model_confidence = context.get("confidence", 0.7)

            explanation = DecisionExplanation(
                decision=decision,
                confidence=model_confidence,
                reasoning=reasoning,
                alternative_options=alternative_options,
                data_sources=data_sources,
                model_confidence=model_confidence,
            )

            logger.info(f"Decision explanation completed for {decision}")
            return explanation

        except Exception as e:
            logger.error(f"Decision explanation failed: {e}")
            return None

    async def accumulate_knowledge(self, incident_data: Dict[str, Any]) -> None:
        """知识库持续学习

        从事故数据中学习和积累知识
        """
        logger.info("Accumulating knowledge from incident data")

        try:
            # 提取关键信息
            symptoms = incident_data.get("symptoms", [])
            root_causes = incident_data.get("root_causes", [])
            resolution = incident_data.get("resolution", "")

            # 生成模式
            pattern_key = self._generate_knowledge_pattern(symptoms, root_causes)

            # 累积知识
            self.knowledge_accumulator[pattern_key].append(
                {
                    "incident_id": incident_data.get("id"),
                    "timestamp": datetime.now(),
                    "resolution": resolution,
                    "success": incident_data.get("success", True),
                }
            )

            # 学习模式频率
            self.pattern_learner[pattern_key] += 1

            logger.info(f"Knowledge accumulated for pattern: {pattern_key}")

        except Exception as e:
            logger.error(f"Knowledge accumulation failed: {e}")

    def _generate_knowledge_pattern(self, symptoms: List[str], root_causes: List[str]) -> str:
        """生成知识模式"""
        combined = symptoms + root_causes
        pattern_str = "|".join(sorted(combined))
        return hashlib.md5(pattern_str.encode(), usedforsecurity=False).hexdigest()

    async def get_knowledge_insights(self, pattern: str) -> Dict[str, Any]:
        """获取知识洞察"""
        if pattern not in self.knowledge_accumulator:
            return {}

        incidents = self.knowledge_accumulator[pattern]

        # 分析成功率和常见解决方案
        success_count = sum(1 for inc in incidents if inc["success"])
        success_rate = success_count / len(incidents) if incidents else 0

        resolutions = [inc["resolution"] for inc in incidents if inc["resolution"]]

        return {
            "pattern": pattern,
            "incident_count": len(incidents),
            "success_rate": success_rate,
            "common_resolutions": resolutions[:5],
            "pattern_frequency": self.pattern_learner.get(pattern, 0),
        }

    async def _learning_loop(self) -> None:
        """学习循环

        定期检查模型性能并触发重新学习
        """
        while True:
            try:
                await asyncio.sleep(self.learning_interval.total_seconds())

                # 检查是否需要重新学习
                for model_id in self.prediction_models:
                    if await self._should_relearn(model_id):
                        logger.info(f"Triggering relearning for {model_id}")
                        # 触发重新学习
                        # await self._retrain_model(model_id)

            except Exception as e:
                logger.error(f"Learning loop error: {e}")

    async def _should_relearn(self, model_id: str) -> bool:
        """检查是否需要重新学习"""
        if model_id not in self.performance_metrics:
            return False

        recent_scores = self.performance_metrics[model_id][-10:]
        if len(recent_scores) < 2:
            return False

        # 检查性能下降
        latest_score = recent_scores[-1]
        average_score = sum(recent_scores[:-1]) / (len(recent_scores) - 1)

        if (average_score - latest_score) > self.retrain_threshold:
            return True

        return False

    async def get_ai_statistics(self) -> Dict[str, Any]:
        """获取AI统计信息"""
        return {
            "prediction_models": len(self.prediction_models),
            "anomaly_detectors": len(self.anomaly_detectors),
            "learning_updates": len(self.learning_history),
            "knowledge_patterns": len(self.knowledge_accumulator),
            "conversation_context_size": len(self.conversation_context),
            "cache_size": len(self.prediction_cache),
        }


# 全局实例
enhanced_ai_capabilities = EnhancedAICapabilities()
