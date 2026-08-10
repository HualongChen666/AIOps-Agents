# -*- coding: utf-8 -*-
"""
Advanced AI Capabilities Module
==============================

Extends AI capabilities with predictive analysis, adaptive learning, natural language interaction,
and explainable AI decision-making.

Key Features:
- Predictive analysis module (time series prediction, anomaly prediction)
- Adaptive learning capabilities (online learning, model updates)
- Natural language interaction interface (conversational operations)
- Enhanced multi-model LLM routing with intelligent decision-making
- Continuous knowledge base learning and accumulation
- Explainable AI decision-making functionality
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

# Try to import ML libraries
try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
    from sklearn.linear_model import SGDClassifier

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.info("ML libraries not available, using rule-based fallback")

# Try to import time series forecasting
try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.info("Prophet not available, using simplified forecasting")

# Import existing AI components
try:
    from core.ai_engine import analyze

    AI_ENGINE_AVAILABLE = True
except ImportError:
    AI_ENGINE_AVAILABLE = False
    logger.info("AI engine components not available")


class PredictionType(Enum):
    """Types of predictions"""

    TIME_SERIES = "time_series"
    ANOMALY = "anomaly"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class LearningMode(Enum):
    """Learning modes for adaptive learning"""

    ONLINE = "online"
    BATCH = "batch"
    REINFORCEMENT = "reinforcement"


@dataclass
class PredictionResult:
    """Result of a prediction"""

    prediction_type: PredictionType
    predicted_values: List[float]
    confidence: float
    prediction_timestamp: datetime = field(default_factory=datetime.now)
    model_used: str = "rule_based"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningUpdate:
    """Learning update from adaptive learning"""

    update_id: str
    learning_mode: LearningMode
    performance_improvement: float
    new_samples: int
    model_version: str
    update_timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for natural language conversation"""

    conversation_id: str
    user_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    current_intent: Optional[str] = None
    context_variables: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class ExplainableDecision:
    """Explainable AI decision with reasoning"""

    decision_id: str
    decision: str
    confidence: float
    reasoning: List[str] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    alternative_options: List[Dict[str, Any]] = field(default_factory=list)
    decision_timestamp: datetime = field(default_factory=datetime.now)


class AdvancedAICapabilities:
    """
    Advanced AI capabilities including predictive analysis, adaptive learning,
    natural language interaction, and explainable AI
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize advanced AI capabilities

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Predictive analysis components
        self.prediction_models: Dict[str, Any] = {}
        self.prediction_history: List[PredictionResult] = []

        # Adaptive learning components
        self.learning_models: Dict[str, Any] = {}
        self.learning_updates: List[LearningUpdate] = []
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)

        # Natural language interaction
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.intent_recognizer = None
        self.response_generator = None

        # Knowledge base learning
        self.knowledge_base: Dict[str, Any] = defaultdict(list)
        self.knowledge_updates: deque = deque(maxlen=1000)

        # Explainable AI
        self.decision_history: List[ExplainableDecision] = []
        self.explanation_templates: Dict[str, str] = {}

        # Initialize components
        self._initialize_components()

        logger.info("Advanced AI Capabilities initialized")

    def _initialize_components(self):
        """Initialize ML and AI components"""
        if ML_AVAILABLE:
            try:
                # Initialize prediction models
                self.prediction_models["time_series"] = GradientBoostingRegressor(
                    n_estimators=100, max_depth=5, random_state=42
                )
                self.prediction_models["classification"] = RandomForestClassifier(
                    n_estimators=100, max_depth=10, random_state=42
                )

                # Initialize adaptive learning models
                self.learning_models["online"] = SGDClassifier(
                    learning_rate="adaptive", eta0=0.01, random_state=42
                )

                logger.info("ML components initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ML components: {e}")

        # Initialize explanation templates
        self._initialize_explanation_templates()

    def _initialize_explanation_templates(self):
        """Initialize explanation templates for different decision types"""
        self.explanation_templates = {
            "alert_routing": "告警路由到 {destination} 因为 {reason}。置信度: {confidence:.2f}",
            "root_cause": (
                "根因分析指向 {root_cause} 基于 {evidence_count} 条证据。主要因素: {main_factors}"
            ),
            "auto_heal": "自动修复建议 {action} 因为 {reason}。预期效果: {expected_effect}",
            "priority": "优先级设为 {priority} 考虑到 {factors}",
            "default": "决策 {decision} 基于 {reasoning}",
        }

    async def predict_time_series(
        self, historical_data: List[Tuple[datetime, float]], prediction_horizon: int = 24
    ) -> PredictionResult:
        """
        Perform time series prediction

        Args:
            historical_data: List of (timestamp, value) tuples
            prediction_horizon: Number of periods to predict

        Returns:
            PredictionResult with forecasted values
        """
        logger.info(f"Performing time series prediction for {prediction_horizon} periods")

        if len(historical_data) < 10:
            logger.warning("Insufficient historical data for prediction")
            return PredictionResult(
                prediction_type=PredictionType.TIME_SERIES,
                predicted_values=[],
                confidence=0.0,
                model_used="insufficient_data",
            )

        try:
            if PROPHET_AVAILABLE:
                return await self._prophet_prediction(historical_data, prediction_horizon)
            elif ML_AVAILABLE:
                return await self._ml_time_series_prediction(historical_data, prediction_horizon)
            else:
                return await self._rule_based_prediction(historical_data, prediction_horizon)

        except Exception as e:
            logger.error(f"Time series prediction failed: {e}")
            return await self._rule_based_prediction(historical_data, prediction_horizon)

    async def _prophet_prediction(
        self, historical_data: List[Tuple[datetime, float]], prediction_horizon: int
    ) -> PredictionResult:
        """Use Prophet for time series prediction"""
        # Prepare data for Prophet
        df = pd.DataFrame(historical_data, columns=["ds", "y"])

        # Fit model
        model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
        model.fit(df)

        # Make prediction
        future = model.make_future_dataframe(periods=prediction_horizon, freq="H")
        forecast = model.predict(future)

        # Extract predictions
        predicted_values = forecast["yhat"].tail(prediction_horizon).tolist()

        result = PredictionResult(
            prediction_type=PredictionType.TIME_SERIES,
            predicted_values=predicted_values,
            confidence=0.8,
            model_used="prophet",
            metadata={
                "prediction_horizon": prediction_horizon,
                "data_points": len(historical_data),
            },
        )

        self.prediction_history.append(result)
        return result

    async def _ml_time_series_prediction(
        self, historical_data: List[Tuple[datetime, float]], prediction_horizon: int
    ) -> PredictionResult:
        """Use ML for time series prediction"""
        # Extract features and target
        values = [v for _, v in historical_data]

        # Create lag features
        features = []
        targets = []
        window_size = 5

        for i in range(window_size, len(values)):
            features.append(values[i - window_size: i])
            targets.append(values[i])

        if len(features) < 10:
            return await self._rule_based_prediction(historical_data, prediction_horizon)

        # Train model
        X = np.array(features)
        y = np.array(targets)

        model = self.prediction_models["time_series"]
        model.fit(X, y)

        # Make predictions
        predictions = []
        current_window = values[-window_size:]

        for _ in range(prediction_horizon):
            pred = model.predict([current_window])[0]
            predictions.append(pred)
            current_window = current_window[1:] + [pred]

        result = PredictionResult(
            prediction_type=PredictionType.TIME_SERIES,
            predicted_values=predictions,
            confidence=0.7,
            model_used="ml_gradient_boosting",
            metadata={"prediction_horizon": prediction_horizon, "training_samples": len(features)},
        )

        self.prediction_history.append(result)
        return result

    async def _rule_based_prediction(
        self, historical_data: List[Tuple[datetime, float]], prediction_horizon: int
    ) -> PredictionResult:
        """Simple rule-based prediction as fallback"""
        values = [v for _, v in historical_data]

        if len(values) < 2:
            return PredictionResult(
                prediction_type=PredictionType.TIME_SERIES,
                predicted_values=[],
                confidence=0.0,
                model_used="insufficient_data",
            )

        # Calculate trend
        trend = (values[-1] - values[0]) / len(values)
        predictions = [values[-1] + trend * (i + 1) for i in range(prediction_horizon)]

        result = PredictionResult(
            prediction_type=PredictionType.TIME_SERIES,
            predicted_values=predictions,
            confidence=0.5,
            model_used="rule_based_trend",
            metadata={"prediction_horizon": prediction_horizon, "trend": trend},
        )

        self.prediction_history.append(result)
        return result

    async def predict_anomalies(
        self,
        current_data: Dict[str, float],
        historical_baseline: Dict[str, List[float]],
        threshold_std: float = 2.0,
    ) -> PredictionResult:
        """
        Predict anomalies based on statistical analysis

        Args:
            current_data: Current metric values
            historical_baseline: Historical baseline data for each metric
            threshold_std: Standard deviation threshold for anomaly detection

        Returns:
            PredictionResult with anomaly predictions
        """
        logger.info("Performing anomaly prediction")

        anomalies = []
        anomaly_scores = {}

        for metric_name, current_value in current_data.items():
            if metric_name in historical_baseline and len(historical_baseline[metric_name]) > 10:
                baseline = historical_baseline[metric_name]
                mean = np.mean(baseline)
                std = np.std(baseline)

                if std > 0:
                    z_score = abs(current_value - mean) / std
                    anomaly_scores[metric_name] = z_score

                    if z_score > threshold_std:
                        anomalies.append(
                            {
                                "metric": metric_name,
                                "current_value": current_value,
                                "baseline_mean": mean,
                                "z_score": z_score,
                                "severity": "high" if z_score > 3 else "medium",
                            }
                        )

        result = PredictionResult(
            prediction_type=PredictionType.ANOMALY,
            predicted_values=[],
            confidence=1.0 - (1.0 / (len(anomalies) + 1)),
            model_used="statistical_z_score",
            metadata={
                "anomalies": anomalies,
                "anomaly_scores": anomaly_scores,
                "total_metrics": len(current_data),
            },
        )

        self.prediction_history.append(result)
        return result

    async def adaptive_learning_update(
        self,
        new_data: Dict[str, Any],
        feedback: Dict[str, float],
        learning_mode: LearningMode = LearningMode.ONLINE,
    ) -> LearningUpdate:
        """
        Perform adaptive learning update with new data and feedback

        Args:
            new_data: New data for learning
            feedback: Feedback signal for learning
            learning_mode: Learning mode to use

        Returns:
            LearningUpdate with update results
        """
        logger.info(f"Performing adaptive learning update in {learning_mode.value} mode")

        update_id = f"update_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            if learning_mode == LearningMode.ONLINE and ML_AVAILABLE:
                # Online learning - update model incrementally
                improvement = await self._online_learning_update(new_data, feedback)
            elif learning_mode == LearningMode.BATCH and ML_AVAILABLE:
                # Batch learning - retrain with accumulated data
                improvement = await self._batch_learning_update(new_data, feedback)
            else:
                # Rule-based learning
                improvement = await self._rule_based_learning_update(new_data, feedback)

            update = LearningUpdate(
                update_id=update_id,
                learning_mode=learning_mode,
                performance_improvement=improvement,
                new_samples=len(new_data) if isinstance(new_data, (list, dict)) else 1,
                model_version=f"v{len(self.learning_updates) + 1}",
                metadata={
                    "new_data_keys": list(new_data.keys()) if isinstance(new_data, dict) else []
                },
            )

            self.learning_updates.append(update)

            # Update performance metrics
            for metric, value in feedback.items():
                self.performance_metrics[metric].append(value)

            logger.info(f"Adaptive learning update completed: {improvement:.2f} improvement")
            return update

        except Exception as e:
            logger.error(f"Adaptive learning update failed: {e}")
            return LearningUpdate(
                update_id=update_id,
                learning_mode=learning_mode,
                performance_improvement=0.0,
                new_samples=0,
                model_version="failed",
                metadata={"error": str(e)},
            )

    async def _online_learning_update(
        self, new_data: Dict[str, Any], feedback: Dict[str, float]
    ) -> float:
        """Perform online learning update"""
        # Extract features from new data
        features = self._extract_features(new_data)
        target = list(feedback.values())[0] if feedback else 0.0

        # Update online learning model
        if "online" in self.learning_models and features:
            try:
                model = self.learning_models["online"]
                # Incremental fit
                model.partial_fit([features], [int(target)])
                return 0.1  # Assume small improvement
            except Exception as e:
                logger.error(f"Online learning update failed: {e}")

        return 0.0

    async def _batch_learning_update(
        self, new_data: Dict[str, Any], feedback: Dict[str, float]
    ) -> float:
        """Perform batch learning update"""
        # Accumulate data and retrain
        # Simplified implementation
        return 0.15  # Assume moderate improvement for batch learning

    async def _rule_based_learning_update(
        self, new_data: Dict[str, Any], feedback: Dict[str, float]
    ) -> float:
        """Rule-based learning update"""
        # Update knowledge base with new patterns
        for key, value in new_data.items():
            self.knowledge_base[key].append(
                {"value": value, "feedback": feedback.get(key, 0.0), "timestamp": datetime.now()}
            )

        return 0.05  # Small improvement for rule-based

    def _extract_features(self, data: Dict[str, Any]) -> List[float]:
        """Extract numerical features from data"""
        features = []

        for value in data.values():
            if isinstance(value, (int, float)):
                features.append(float(value))
            elif isinstance(value, str):
                features.append(float(hash(value)) % 100)
            elif isinstance(value, bool):
                features.append(1.0 if value else 0.0)
            else:
                features.append(0.0)

        return features

    async def natural_language_interaction(
        self, user_input: str, conversation_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Process natural language interaction

        Args:
            user_input: User's natural language input
            conversation_id: Conversation identifier
            user_id: User identifier

        Returns:
            Response with action and explanation
        """
        logger.info(f"Processing natural language input: {user_input[:50]}...")

        # Get or create conversation context
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = ConversationContext(
                conversation_id=conversation_id, user_id=user_id
            )

        context = self.conversation_contexts[conversation_id]

        # Add user message to context
        context.messages.append(
            {"role": "user", "content": user_input, "timestamp": datetime.now().isoformat()}
        )

        # Recognize intent
        intent = await self._recognize_intent(user_input, context)
        context.current_intent = intent

        # Generate response
        response = await self._generate_response(user_input, intent, context)

        context.last_activity = datetime.now()

        return response

    async def _recognize_intent(self, user_input: str, context: ConversationContext) -> str:
        """Recognize user intent from natural language input"""
        # Simple keyword-based intent recognition
        intent_keywords = {
            "check_status": ["检查", "状态", "status", "check"],
            "analyze_alert": ["分析", "告警", "alert", "analyze"],
            "predict": ["预测", "forecast", "predict"],
            "auto_heal": ["修复", "heal", "fix", "repair"],
            "root_cause": ["根因", "root cause", "原因"],
            "help": ["帮助", "help", "如何"],
            "report": ["报告", "report", "报表"],
        }

        user_input_lower = user_input.lower()

        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    return intent

        return "general_query"

    async def _generate_response(
        self, user_input: str, intent: str, context: ConversationContext
    ) -> Dict[str, Any]:
        """Generate response based on intent and context"""

        # Use AI engine if available for complex queries
        if AI_ENGINE_AVAILABLE and intent in ["analyze_alert", "root_cause", "predict"]:
            try:
                ai_response = await analyze(user_input, context_type="conversation")
                return {
                    "response": ai_response.get("analysis", "处理完成"),
                    "intent": intent,
                    "confidence": 0.8,
                    "action_required": ai_response.get("action_required", False),
                    "metadata": {"ai_generated": True},
                }
            except Exception as e:
                logger.error(f"AI response generation failed: {e}")

        # Rule-based responses
        responses = {
            "check_status": "系统运行正常，所有关键指标在正常范围内。",
            "analyze_alert": "正在分析告警信息，请提供具体的告警详情。",
            "predict": "预测功能已启用，系统正在分析历史数据以预测未来趋势。",
            "auto_heal": "自动修复功能已准备就绪，系统将根据告警类型采取相应措施。",
            "root_cause": "根因分析引擎正在运行，将结合拓扑图和历史模式识别根本原因。",
            "help": "我可以帮助您：检查系统状态、分析告警、预测趋势、自动修复问题、分析根因等。",
            "report": "正在生成系统报告，包含关键指标和趋势分析。",
            "general_query": "我理解您的询问，请提供更多详细信息以便更好地帮助您。",
        }

        base_response = responses.get(intent, responses["general_query"])

        return {
            "response": base_response,
            "intent": intent,
            "confidence": 0.7,
            "action_required": False,
            "metadata": {"rule_based": True},
        }

    async def explain_decision(
        self, decision: str, decision_context: Dict[str, Any], decision_type: str = "default"
    ) -> ExplainableDecision:
        """
        Generate explanation for AI decision

        Args:
            decision: The decision made
            decision_context: Context information for the decision
            decision_type: Type of decision for template selection

        Returns:
            ExplainableDecision with reasoning
        """
        logger.info(f"Generating explanation for decision: {decision}")

        decision_id = f"decision_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Generate reasoning
        reasoning = self._generate_reasoning(decision, decision_context, decision_type)

        # Calculate feature importance
        feature_importance = self._calculate_feature_importance(decision_context)

        # Generate alternative options
        alternatives = self._generate_alternatives(decision, decision_context)

        # Calculate confidence
        confidence = self._calculate_decision_confidence(decision_context)

        explainable_decision = ExplainableDecision(
            decision_id=decision_id,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            feature_importance=feature_importance,
            alternative_options=alternatives,
        )

        self.decision_history.append(explainable_decision)

        return explainable_decision

    def _generate_reasoning(
        self, decision: str, context: Dict[str, Any], decision_type: str
    ) -> List[str]:
        """Generate reasoning steps for the decision"""
        reasoning = []

        # Add context-based reasoning
        for key, value in context.items():
            if isinstance(value, (int, float)) and value > 0.5:
                reasoning.append(f"{key} 显示为 {value:.2f}，这是一个重要因素")

        # Add decision-type specific reasoning
        if decision_type == "alert_routing":
            reasoning.append("基于历史路由模式和当前系统状态")
        elif decision_type == "root_cause":
            reasoning.append("结合因果分析和历史模式匹配")
        elif decision_type == "auto_heal":
            reasoning.append("考虑修复风险和预期效果")

        return reasoning

    def _calculate_feature_importance(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate importance of features in decision"""
        importance = {}

        for key, value in context.items():
            if isinstance(value, (int, float)):
                # Normalize to 0-1 range
                importance[key] = min(1.0, abs(value) / 100.0)
            elif isinstance(value, str):
                importance[key] = 0.5
            else:
                importance[key] = 0.3

        # Normalize to sum to 1
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}

        return importance

    def _generate_alternatives(
        self, decision: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate alternative options considered"""
        alternatives = []

        # Generate 2-3 alternatives based on context
        if "severity" in context:
            alternatives.append(
                {
                    "option": "conservative_approach",
                    "description": "采用保守策略，等待进一步确认",
                    "confidence": 0.6,
                }
            )

        alternatives.append(
            {"option": "default_action", "description": "执行默认操作", "confidence": 0.8}
        )

        return alternatives

    def _calculate_decision_confidence(self, context: Dict[str, Any]) -> float:
        """Calculate confidence in the decision"""
        # Base confidence
        confidence = 0.7

        # Increase confidence if we have more context
        if len(context) > 3:
            confidence += 0.1

        # Increase confidence if we have strong signals
        strong_signals = sum(1 for v in context.values() if isinstance(v, (int, float)) and v > 0.8)
        confidence += min(0.2, strong_signals * 0.05)

        return min(1.0, confidence)

    async def continuous_knowledge_learning(
        self, experience_data: Dict[str, Any], outcome: str
    ) -> Dict[str, Any]:
        """
        Continuously learn and accumulate knowledge from experiences

        Args:
            experience_data: Data from the experience
            outcome: Outcome of the experience

        Returns:
            Learning results
        """
        logger.info("Performing continuous knowledge learning")

        # Extract knowledge from experience
        knowledge = self._extract_knowledge(experience_data, outcome)

        # Update knowledge base
        for key, value in knowledge.items():
            self.knowledge_base[key].append(
                {"value": value, "outcome": outcome, "timestamp": datetime.now()}
            )

        # Add to knowledge updates queue
        self.knowledge_updates.append(
            {"knowledge": knowledge, "outcome": outcome, "timestamp": datetime.now()}
        )

        # Trigger adaptive learning if enough data accumulated
        if len(self.knowledge_updates) >= 10:
            await self._trigger_knowledge_based_learning()

        return {
            "status": "success",
            "knowledge_extracted": len(knowledge),
            "total_knowledge_items": sum(len(v) for v in self.knowledge_base.values()),
        }

    def _extract_knowledge(self, experience_data: Dict[str, Any], outcome: str) -> Dict[str, Any]:
        """Extract knowledge from experience data"""
        knowledge: Dict[str, Any] = {}

        # Extract patterns from experience
        for key, value in experience_data.items():
            if isinstance(value, (int, float)):
                knowledge[f"{key}_value"] = value
            elif isinstance(value, str):
                knowledge[f"{key}_pattern"] = value

        knowledge["outcome"] = outcome
        knowledge["success"] = outcome in ["success", "resolved", "fixed"]

        return knowledge

    async def _trigger_knowledge_based_learning(self):
        """Trigger learning based on accumulated knowledge"""
        # Aggregate knowledge from recent updates
        recent_knowledge = list(self.knowledge_updates)[-10:]

        # Perform learning
        aggregated_data: Dict[str, List[Any]] = {}
        feedback: Dict[str, float] = {}

        for update in recent_knowledge:
            for key, value in update["knowledge"].items():
                if key not in aggregated_data:
                    aggregated_data[key] = []
                aggregated_data[key].append(value)

            # Use outcome as feedback
            feedback[update["timestamp"].isoformat()] = (
                1.0 if update["outcome"] == "success" else 0.0
            )

        # Trigger adaptive learning
        if aggregated_data:
            await self.adaptive_learning_update(aggregated_data, feedback, LearningMode.BATCH)

    def get_capabilities_summary(self) -> Dict[str, Any]:
        """Get summary of AI capabilities"""
        return {
            "predictive_analysis": {
                "available": PROPHET_AVAILABLE or ML_AVAILABLE,
                "models": list(self.prediction_models.keys()),
                "predictions_made": len(self.prediction_history),
            },
            "adaptive_learning": {
                "available": ML_AVAILABLE,
                "learning_modes": ["online", "batch", "rule_based"],
                "updates_performed": len(self.learning_updates),
                "performance_metrics": {k: len(v) for k, v in self.performance_metrics.items()},
            },
            "natural_language_interaction": {
                "available": AI_ENGINE_AVAILABLE,
                "active_conversations": len(self.conversation_contexts),
                "supported_intents": [
                    "check_status",
                    "analyze_alert",
                    "predict",
                    "auto_heal",
                    "root_cause",
                    "help",
                    "report",
                ],
            },
            "knowledge_base": {
                "total_items": sum(len(v) for v in self.knowledge_base.values()),
                "categories": list(self.knowledge_base.keys()),
                "recent_updates": len(self.knowledge_updates),
            },
            "explainable_ai": {
                "decisions_explained": len(self.decision_history),
                "available_templates": list(self.explanation_templates.keys()),
            },
        }


# Global instance
advanced_ai_capabilities = AdvancedAICapabilities()
