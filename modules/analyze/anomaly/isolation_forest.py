# -*- coding: utf-8 -*-
"""
Isolation Forest-based Anomaly Detection
基于Isolation Forest的无监督异常检测模型

功能:
- 无监督异常检测（无需标签）
- 高效处理高维数据
- 支持流式检测
- 异常评分
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, cast  # noqa: F401

import numpy as np
import pandas as pd

try:
    from sklearn.decomposition import PCA
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    IsolationForest = None
    StandardScaler = None
    PCA = None

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """
    Isolation Forest异常检测器

    使用Isolation Forest进行无监督异常检测，适合高维数据。

    参数:
        contamination: 异常比例估计值，默认'auto'
        n_estimators: 基础估计器数量，默认100
        max_samples: 每个估计器的样本数，默认'auto'
        random_state: 随机种子
        use_pca: 是否使用PCA降维，默认False
        pca_components: PCA降维后的维度，默认0.95（保留95%方差）
    """

    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: str = "auto",
        random_state: Optional[int] = None,
        use_pca: bool = False,
        pca_components: float = 0.95,
    ):
        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "scikit-learn is not installed. Install with: pip install scikit-learn"
            )

        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        self.use_pca = use_pca
        self.pca_components = pca_components

        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.pca: Optional[PCA] = None
        self.feature_names: List[str] = []
        self.is_fitted = False

    def _prepare_features(
        self, data: List[Dict[str, Any]], feature_cols: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        准备特征矩阵

        参数:
            data: 数据列表
            feature_cols: 特征列名列表，如果为None则自动检测数值列

        返回:
            特征矩阵 (n_samples, n_features)
        """
        df = pd.DataFrame(data)

        # 自动检测数值特征
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not feature_cols:
            raise ValueError("No numeric features found in data")

        self.feature_names = feature_cols

        # 提取特征
        X = df[feature_cols].values

        # 处理缺失值
        X = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)

        return cast(np.ndarray, X)

    def fit(self, data: List[Dict[str, Any]], feature_cols: Optional[List[str]] = None) -> None:
        """
        训练Isolation Forest模型

        参数:
            data: 训练数据
            feature_cols: 特征列名列表
        """
        logger.info("Fitting Isolation Forest with %d samples", len(data))

        # 准备特征
        X = self._prepare_features(data, feature_cols)

        if len(X) < 10:
            raise ValueError("Insufficient data for Isolation Forest (minimum 10 samples required)")

        # 标准化
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # PCA降维（可选）
        if self.use_pca:
            self.pca = PCA(n_components=self.pca_components)
            X_scaled = self.pca.fit_transform(X_scaled)
            logger.info("PCA reduced to %d components", X_scaled.shape[1])

        # 训练模型
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            random_state=self.random_state,
            n_jobs=-1,  # 使用所有CPU核心
        )

        self.model.fit(X_scaled)
        self.is_fitted = True

        logger.info("Isolation Forest fitted successfully")

    def predict(
        self,
        data: List[Dict[str, Any]],
        feature_cols: Optional[List[str]] = None,
        return_scores: bool = True,
    ) -> Dict[str, Any]:
        """
        预测并检测异常

        参数:
            data: 待检测数据
            feature_cols: 特征列名列表
            return_scores: 是否返回异常评分

        返回:
            {
                "predictions": List[int],  # 预测结果 (1=正常, -1=异常)
                "anomalies": List[Dict],    # 异常点详情
                "scores": List[float],      # 异常评分（可选）
                "metrics": Dict             # 检测指标
            }
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        logger.info("Predicting with Isolation Forest")

        # 准备特征
        X = self._prepare_features(data, feature_cols)

        # 标准化
        if self.scaler is None:
            raise RuntimeError("Scaler is not initialized")
        X_scaled = self.scaler.transform(X)

        # PCA降维（如果训练时使用了）
        if self.pca is not None:
            X_scaled = self.pca.transform(X_scaled)

        # 预测
        if self.model is None:
            raise RuntimeError("Model is not initialized")
        predictions = self.model.predict(X_scaled)

        # 获取异常评分
        if return_scores:
            scores = self.model.score_samples(X_scaled)
            # 转换为0-1范围（0=正常，1=异常）
            scores_normalized = (scores - scores.min()) / (scores.max() - scores.min())
        else:
            scores = None
            scores_normalized = None

        # 提取异常点
        anomalies = []
        for idx, (pred, score) in enumerate(
            zip(predictions, scores_normalized if scores is not None else [0] * len(predictions))
        ):
            if pred == -1:  # 异常
                anomaly = {
                    "index": idx,
                    "timestamp": data[idx].get("timestamp", ""),
                    "anomaly_score": float(score) if score is not None else 0.0,
                    "features": {name: data[idx].get(name) for name in self.feature_names},
                }
                anomalies.append(anomaly)

        # 计算指标
        anomaly_count = len(anomalies)
        anomaly_rate = anomaly_count / len(data) if len(data) > 0 else 0

        metrics = {
            "total_samples": len(data),
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "contamination": self.contamination,
        }

        logger.info(
            "Prediction completed: %d anomalies detected (%.2f%% rate)",
            anomaly_count,
            anomaly_rate * 100,
        )

        result = {
            "predictions": predictions.tolist(),
            "anomalies": anomalies,
            "metrics": metrics,
        }

        if return_scores:
            result["scores"] = scores_normalized.tolist()

        return result

    def detect_anomalies(
        self,
        data: List[Dict[str, Any]],
        feature_cols: Optional[List[str]] = None,
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        仅检测异常点（简化接口）

        参数:
            data: 待检测数据
            feature_cols: 特征列名列表
            threshold: 异常评分阈值

        返回:
            异常点列表
        """
        result = self.predict(data, feature_cols, return_scores=True)

        # 根据阈值过滤
        anomalies = [a for a in result["anomalies"] if a["anomaly_score"] >= threshold]

        return anomalies

    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取特征重要性（基于异常评分的方差贡献）

        返回:
            特征重要性字典
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting feature importance")

        if self.pca is not None:
            # 如果使用了PCA，返回PCA的方差贡献
            importance = {
                f"PC{i + 1}": variance
                for i, variance in enumerate(self.pca.explained_variance_ratio_)
            }
        else:
            # 否则返回标准化后的特征标准差作为重要性
            if self.scaler is None:
                raise RuntimeError("Scaler is not initialized")
            importance = {name: std for name, std in zip(self.feature_names, self.scaler.scale_)}

        return importance

    def save_model(self, path: str) -> None:
        """保存模型到文件"""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        import joblib

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "pca": self.pca,
            "feature_names": self.feature_names,
            "params": {
                "contamination": self.contamination,
                "n_estimators": self.n_estimators,
                "max_samples": self.max_samples,
                "random_state": self.random_state,
                "use_pca": self.use_pca,
                "pca_components": self.pca_components,
            },
        }
        joblib.dump(model_data, path)
        logger.info("Model saved to %s", path)

    def load_model(self, path: str) -> None:
        """从文件加载模型"""
        import joblib

        model_data = joblib.load(path)

        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.pca = model_data["pca"]
        self.feature_names = model_data["feature_names"]

        params = model_data["params"]
        self.contamination = params["contamination"]
        self.n_estimators = params["n_estimators"]
        self.max_samples = params["max_samples"]
        self.random_state = params["random_state"]
        self.use_pca = params["use_pca"]
        self.pca_components = params["pca_components"]

        self.is_fitted = True
        logger.info("Model loaded from %s", path)
