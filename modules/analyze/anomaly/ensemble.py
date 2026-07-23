# -*- coding: utf-8 -*-
"""
Ensemble Anomaly Detection
集成异常检测模型，结合Prophet和IsolationForest的优势

功能:
- 集成多种检测方法
- 投票机制
- 加权融合
- 提高检测准确率
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .isolation_forest import IsolationForestDetector
from .prophet_model import ProphetAnomalyDetector

logger = logging.getLogger(__name__)


class EnsembleAnomalyDetector:
    """
    集成异常检测器

    结合Prophet（时序检测）和IsolationForest（多维检测）的优势，
    通过投票或加权融合提高检测准确率。

    参数:
        prophet_params: Prophet模型参数
        isolation_params: Isolation Forest模型参数
        voting: 投票方式 ('hard', 'soft', 'weighted')
        prophet_weight: Prophet权重（仅soft/weighted模式）
        isolation_weight: Isolation Forest权重（仅soft/weighted模式）
        threshold: 异常判定阈值（仅soft/weighted模式）
    """

    def __init__(
        self,
        prophet_params: Optional[Dict[str, Any]] = None,
        isolation_params: Optional[Dict[str, Any]] = None,
        voting: str = "hard",
        prophet_weight: float = 0.5,
        isolation_weight: float = 0.5,
        threshold: float = 0.5,
    ):
        self.prophet_params = prophet_params or {}
        self.isolation_params = isolation_params or {}
        self.voting = voting
        self.prophet_weight = prophet_weight
        self.isolation_weight = isolation_weight
        self.threshold = threshold

        # 初始化子模型
        self.prophet_detector = ProphetAnomalyDetector(**self.prophet_params)
        self.isolation_detector = IsolationForestDetector(**self.isolation_params)

        self.is_fitted = False

    def fit(
        self,
        data: List[Dict[str, Any]],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        feature_cols: Optional[List[str]] = None,
    ) -> None:
        """
        训练集成模型

        参数:
            data: 训练数据
            timestamp_col: 时间戳字段名（Prophet用）
            value_col: 数值字段名（Prophet用）
            feature_cols: 特征列名列表（Isolation Forest用）
        """
        logger.info("Fitting ensemble model with %d samples", len(data))

        # 训练Prophet
        try:
            self.prophet_detector.fit(data, timestamp_col, value_col)
            logger.info("Prophet model fitted")
        except Exception as e:
            logger.warning("Prophet fitting failed: %s", e)

        # 训练Isolation Forest
        try:
            self.isolation_detector.fit(data, feature_cols)
            logger.info("Isolation Forest fitted")
        except Exception as e:
            logger.warning("Isolation Forest fitting failed: %s", e)

        self.is_fitted = True
        logger.info("Ensemble model fitted successfully")

    def predict(
        self,
        data: List[Dict[str, Any]],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        feature_cols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        预测并检测异常

        参数:
            data: 待检测数据
            timestamp_col: 时间戳字段名
            value_col: 数值字段名
            feature_cols: 特征列名列表

        返回:
            {
                "anomalies": List[Dict],    # 集成异常点
                "prophet_anomalies": List,  # Prophet检测的异常
                "isolation_anomalies": List, # Isolation Forest检测的异常
                "metrics": Dict             # 检测指标
            }
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        logger.info("Predicting with ensemble model")

        # Prophet预测
        prophet_result = None
        try:
            prophet_result = self.prophet_detector.predict(
                data, timestamp_col, value_col, periods=0
            )
            prophet_anomalies = prophet_result["anomalies"]
        except Exception as e:
            logger.warning("Prophet prediction failed: %s", e)
            prophet_anomalies = []

        # Isolation Forest预测
        isolation_result = None
        try:
            isolation_result = self.isolation_detector.predict(
                data, feature_cols, return_scores=True
            )
            isolation_anomalies = isolation_result["anomalies"]
        except Exception as e:
            logger.warning("Isolation Forest prediction failed: %s", e)
            isolation_anomalies = []

        # 集成异常检测
        ensemble_anomalies = self._ensemble_anomalies(prophet_anomalies, isolation_anomalies, data)

        # 计算指标
        metrics = {
            "total_samples": len(data),
            "prophet_anomaly_count": len(prophet_anomalies),
            "isolation_anomaly_count": len(isolation_anomalies),
            "ensemble_anomaly_count": len(ensemble_anomalies),
            "voting_method": self.voting,
        }

        logger.info("Ensemble prediction completed: %d anomalies detected", len(ensemble_anomalies))

        return {
            "anomalies": ensemble_anomalies,
            "prophet_anomalies": prophet_anomalies,
            "isolation_anomalies": isolation_anomalies,
            "metrics": metrics,
        }

    def _ensemble_anomalies(
        self,
        prophet_anomalies: List[Dict[str, Any]],
        isolation_anomalies: List[Dict[str, Any]],
        data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        集成异常检测结果

        参数:
            prophet_anomalies: Prophet检测的异常
            isolation_anomalies: Isolation Forest检测的异常
            data: 原始数据

        返回:
            集成异常列表
        """
        if self.voting == "hard":
            return self._hard_voting(prophet_anomalies, isolation_anomalies, data)
        elif self.voting == "soft":
            return self._soft_voting(prophet_anomalies, isolation_anomalies, data)
        elif self.voting == "weighted":
            return self._weighted_voting(prophet_anomalies, isolation_anomalies, data)
        else:
            raise ValueError(f"Unknown voting method: {self.voting}")

    def _hard_voting(
        self,
        prophet_anomalies: List[Dict[str, Any]],
        isolation_anomalies: List[Dict[str, Any]],
        data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        硬投票：至少一个模型检测为异常即判定为异常
        """
        # 构建异常时间戳集合
        prophet_timestamps = {a["timestamp"] for a in prophet_anomalies}

        ensemble_anomalies = []

        # Prophet检测的异常
        for anomaly in prophet_anomalies:
            ensemble_anomalies.append(
                {
                    **anomaly,
                    "detection_method": "prophet",
                    "ensemble_confidence": 1.0,
                }
            )

        # Isolation Forest检测的异常（去重）
        for anomaly in isolation_anomalies:
            idx = anomaly["index"]
            timestamp = data[idx].get("timestamp", "")

            if timestamp not in prophet_timestamps:
                ensemble_anomalies.append(
                    {
                        **anomaly,
                        "detection_method": "isolation_forest",
                        "ensemble_confidence": 1.0,
                    }
                )

        return ensemble_anomalies

    def _soft_voting(
        self,
        prophet_anomalies: List[Dict[str, Any]],
        isolation_anomalies: List[Dict[str, Any]],
        data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        软投票：基于异常评分加权融合
        """
        # 构建评分映射
        prophet_scores = {a["timestamp"]: a.get("severity", 0.5) for a in prophet_anomalies}

        isolation_scores = {a["index"]: a["anomaly_score"] for a in isolation_anomalies}

        ensemble_anomalies = []

        # 遍历所有数据点
        for idx, item in enumerate(data):
            timestamp = item.get("timestamp", "")

            # 获取两个模型的评分
            prophet_score = prophet_scores.get(timestamp, 0.0)
            isolation_score = isolation_scores.get(idx, 0.0)

            # 加权融合
            ensemble_score = (
                self.prophet_weight * prophet_score + self.isolation_weight * isolation_score
            )

            # 判定是否为异常
            if ensemble_score >= self.threshold:
                ensemble_anomalies.append(
                    {
                        "index": idx,
                        "timestamp": timestamp,
                        "ensemble_score": ensemble_score,
                        "prophet_score": prophet_score,
                        "isolation_score": isolation_score,
                        "detection_method": "ensemble_soft",
                        "ensemble_confidence": ensemble_score,
                    }
                )

        return ensemble_anomalies

    def _weighted_voting(
        self,
        prophet_anomalies: List[Dict[str, Any]],
        isolation_anomalies: List[Dict[str, Any]],
        data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        加权投票：基于模型权重和检测置信度
        """
        # 构建异常映射
        prophet_map = {a["timestamp"]: a for a in prophet_anomalies}
        isolation_map = {a["index"]: a for a in isolation_anomalies}

        ensemble_anomalies = []

        # 遍历所有数据点
        for idx, item in enumerate(data):
            timestamp = item.get("timestamp", "")

            prophet_anomaly = prophet_map.get(timestamp)
            isolation_anomaly = isolation_map.get(idx)

            # 计算置信度
            prophet_conf = 0.0
            if prophet_anomaly:
                prophet_conf = prophet_anomaly.get("severity", 0.5)

            isolation_conf = 0.0
            if isolation_anomaly:
                isolation_conf = isolation_anomaly.get("anomaly_score", 0.5)

            # 加权融合
            ensemble_conf = (
                self.prophet_weight * prophet_conf + self.isolation_weight * isolation_conf
            )

            # 判定是否为异常
            if ensemble_conf >= self.threshold:
                ensemble_anomalies.append(
                    {
                        "index": idx,
                        "timestamp": timestamp,
                        "ensemble_confidence": ensemble_conf,
                        "prophet_confidence": prophet_conf,
                        "isolation_confidence": isolation_conf,
                        "detection_method": "ensemble_weighted",
                    }
                )

        return ensemble_anomalies

    def save_model(self, path: str) -> None:
        """保存集成模型"""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        import joblib

        model_data = {
            "prophet_detector": self.prophet_detector,
            "isolation_detector": self.isolation_detector,
            "params": {
                "prophet_params": self.prophet_params,
                "isolation_params": self.isolation_params,
                "voting": self.voting,
                "prophet_weight": self.prophet_weight,
                "isolation_weight": self.isolation_weight,
                "threshold": self.threshold,
            },
        }
        joblib.dump(model_data, path)
        logger.info("Ensemble model saved to %s", path)

    def load_model(self, path: str) -> None:
        """加载集成模型"""
        import joblib

        model_data = joblib.load(path)

        self.prophet_detector = model_data["prophet_detector"]
        self.isolation_detector = model_data["isolation_detector"]

        params = model_data["params"]
        self.prophet_params = params["prophet_params"]
        self.isolation_params = params["isolation_params"]
        self.voting = params["voting"]
        self.prophet_weight = params["prophet_weight"]
        self.isolation_weight = params["isolation_weight"]
        self.threshold = params["threshold"]

        self.is_fitted = True
        logger.info("Ensemble model loaded from %s", path)
