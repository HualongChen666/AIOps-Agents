# -*- coding: utf-8 -*-
"""
Prophet-based Time Series Anomaly Detection
基于Facebook Prophet的时序异常检测模型

功能:
- 时序数据分解（趋势、季节性、节假日）
- 异常点检测（基于预测置信区间）
- 支持多变量输入
- 自动参数调优
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

import pandas as pd

try:
    from prophet import Prophet
    from prophet.diagnostics import cross_validation, performance_metrics

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = None

logger = logging.getLogger(__name__)


class ProphetAnomalyDetector:
    """
    Prophet异常检测器

    使用Prophet进行时序预测，基于预测置信区间检测异常点。

    参数:
        interval_width: 预测置信区间宽度 (0-1)，默认0.95
        changepoint_prior_scale: 趋势变化敏感度，默认0.05
        seasonality_prior_scale: 季节性敏感度，默认10
        holidays_prior_scale: 节假日敏感度，默认10
        yearly_seasonality: 是否包含年季节性，默认True
        weekly_seasonality: 是否包含周季节性，默认True
        daily_seasonality: 是否包含日季节性，默认False
    """

    def __init__(
        self,
        interval_width: float = 0.95,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
    ):
        if not PROPHET_AVAILABLE:
            raise ImportError("Prophet is not installed. Install with: pip install prophet")

        self.interval_width = interval_width
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality

        self.model: Optional[Prophet] = None
        self.is_fitted = False

    def _prepare_data(
        self, data: List[Dict[str, Any]], timestamp_col: str = "timestamp", value_col: str = "value"
    ) -> pd.DataFrame:
        """
        准备Prophet所需的数据格式

        参数:
            data: 时序数据列表，每个元素包含timestamp和value
            timestamp_col: 时间戳字段名
            value_col: 数值字段名

        返回:
            DataFrame with columns ['ds', 'y']
        """
        df = pd.DataFrame(data)

        # 转换时间戳
        if timestamp_col in df.columns:
            df["ds"] = pd.to_datetime(df[timestamp_col])
        else:
            raise ValueError(f"Timestamp column '{timestamp_col}' not found in data")

        # 提取数值
        if value_col in df.columns:
            df["y"] = pd.to_numeric(df[value_col], errors="coerce")
        else:
            raise ValueError(f"Value column '{value_col}' not found in data")

        # 删除无效数据
        df = df.dropna(subset=["ds", "y"])
        df = df.sort_values("ds")

        return df[["ds", "y"]]

    def fit(
        self,
        data: List[Dict[str, Any]],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        holidays: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        训练Prophet模型

        参数:
            data: 训练数据
            timestamp_col: 时间戳字段名
            value_col: 数值字段名
            holidays: 节假日数据，DataFrame with columns ['ds', 'holiday', 'lower_window', 'upper_window']
        """
        logger.info("Fitting Prophet model with %d data points", len(data))

        # 准备数据
        df = self._prepare_data(data, timestamp_col, value_col)

        if len(df) < 10:
            raise ValueError("Insufficient data for Prophet (minimum 10 points required)")

        # 创建Prophet模型
        self.model = Prophet(
            interval_width=self.interval_width,
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            holidays_prior_scale=self.holidays_prior_scale,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
        )

        # 添加节假日
        if holidays is not None:
            self.model.add_holidays(holidays)

        # 训练
        self.model.fit(df)
        self.is_fitted = True

        logger.info("Prophet model fitted successfully")

    def predict(
        self,
        data: List[Dict[str, Any]],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        periods: int = 30,
        freq: str = "H",
    ) -> Dict[str, Any]:
        """
        预测并检测异常

        参数:
            data: 待检测数据
            timestamp_col: 时间戳字段名
            value_col: 数值字段名
            periods: 预测未来periods个时间点
            freq: 预测频率（H=小时, D=天, W=周）

        返回:
            {
                "predictions": List[Dict],  # 预测结果
                "anomalies": List[Dict],    # 异常点
                "metrics": Dict             # 检测指标
            }
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        logger.info("Predicting with Prophet model")

        # 准备数据
        df = self._prepare_data(data, timestamp_col, value_col)

        # 生成未来时间点
        if self.model is None:
            raise RuntimeError("Model is not initialized")
        future = self.model.make_future_dataframe(periods=periods, freq=freq)

        # 预测
        forecast = self.model.predict(future)

        # 检测异常（实际值超出置信区间）
        anomalies = []
        predictions = []

        for idx, row in forecast.iterrows():
            pred = {
                "timestamp": row["ds"].isoformat(),
                "value": row["yhat"],
                "value_lower": row["yhat_lower"],
                "value_upper": row["yhat_upper"],
                "trend": row["trend"],
                "seasonal": row.get("seasonal", 0),
            }
            predictions.append(pred)

            # 检查是否为异常（仅对历史数据）
            if idx < len(df):
                actual_value = df.iloc[idx]["y"]
                is_anomaly = actual_value < row["yhat_lower"] or actual_value > row["yhat_upper"]

                if is_anomaly:
                    anomaly = {
                        "timestamp": row["ds"].isoformat(),
                        "actual_value": actual_value,
                        "predicted_value": row["yhat"],
                        "lower_bound": row["yhat_lower"],
                        "upper_bound": row["yhat_upper"],
                        "anomaly_type": "high" if actual_value > row["yhat_upper"] else "low",
                        "severity": (
                            abs(actual_value - row["yhat"])
                            / (row["yhat_upper"] - row["yhat_lower"])
                        ),
                    }
                    anomalies.append(anomaly)

        # 计算指标
        anomaly_count = len(anomalies)
        anomaly_rate = anomaly_count / len(df) if len(df) > 0 else 0

        metrics = {
            "total_points": len(df),
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "interval_width": self.interval_width,
        }

        logger.info(
            "Prediction completed: %d anomalies detected (%.2f%% rate)",
            anomaly_count,
            anomaly_rate * 100,
        )

        return {
            "predictions": predictions,
            "anomalies": anomalies,
            "metrics": metrics,
        }

    def detect_anomalies(
        self, data: List[Dict[str, Any]], timestamp_col: str = "timestamp", value_col: str = "value"
    ) -> List[Dict[str, Any]]:
        """
        仅检测异常点（简化接口）

        参数:
            data: 待检测数据
            timestamp_col: 时间戳字段名
            value_col: 数值字段名

        返回:
            异常点列表
        """
        result = self.predict(data, timestamp_col, value_col, periods=0)
        return cast(List[Dict[str, Any]], result["anomalies"])

    def get_forecast(self, periods: int = 30, freq: str = "H") -> List[Dict[str, Any]]:
        """
        获取未来预测（不检测异常）

        参数:
            periods: 预测未来periods个时间点
            freq: 预测频率

        返回:
            预测结果列表
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        if self.model is None:
            raise RuntimeError("Model is not initialized")
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        forecast = self.model.predict(future)

        predictions = []
        for _, row in forecast.iterrows():
            pred = {
                "timestamp": row["ds"].isoformat(),
                "value": row["yhat"],
                "value_lower": row["yhat_lower"],
                "value_upper": row["yhat_upper"],
                "trend": row["trend"],
                "seasonal": row.get("seasonal", 0),
            }
            predictions.append(pred)

        return predictions

    def cross_validate(
        self, initial: str = "730 days", period: str = "180 days", horizon: str = "365 days"
    ) -> Dict[str, Any]:
        """
        交叉验证模型性能

        参数:
            initial: 初始训练期
            period: 验证周期
            horizon: 预测范围

        返回:
            性能指标
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before cross-validation")

        logger.info("Running cross-validation")

        df_cv = cross_validation(self.model, initial=initial, period=period, horizon=horizon)

        df_p = performance_metrics(df_cv)

        metrics = {
            "mse": df_p["mse"].mean(),
            "rmse": df_p["rmse"].mean(),
            "mae": df_p["mae"].mean(),
            "mape": df_p["mape"].mean(),
            "coverage": df_p["coverage"].mean(),
        }

        logger.info(
            "Cross-validation completed: RMSE=%.2f, MAPE=%.2f%%", metrics["rmse"], metrics["mape"]
        )

        return metrics

    def save_model(self, path: str) -> None:
        """保存模型到文件"""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        import joblib

        joblib.dump(self.model, path)
        logger.info("Model saved to %s", path)

    def load_model(self, path: str) -> None:
        """从文件加载模型"""
        import joblib

        self.model = joblib.load(path)
        self.is_fitted = True
        logger.info("Model loaded from %s", path)
