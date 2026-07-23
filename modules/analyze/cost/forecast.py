# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Cost Forecasting
成本预测模块，基于Prophet和GradientBoosting进行成本预测

功能:
- 云资源成本预测
- Prophet时序预测
- GradientBoosting特征预测
- 成本优化建议
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = None

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    GradientBoostingRegressor = None
    StandardScaler = None

logger = logging.getLogger(__name__)


class CostForecaster:
    """
    成本预测器

    使用Prophet和GradientBoosting进行云资源成本预测。

    参数:
        use_prophet: 是否使用Prophet模型
        use_gbm: 是否使用GradientBoosting模型
        prophet_params: Prophet模型参数
        gbm_params: GradientBoosting模型参数
        currency: 货币单位
    """

    def __init__(
        self,
        use_prophet: bool = True,
        use_gbm: bool = True,
        prophet_params: Optional[Dict[str, Any]] = None,
        gbm_params: Optional[Dict[str, Any]] = None,
        currency: str = "USD",
    ):
        self.use_prophet = use_prophet
        self.use_gbm = use_gbm
        self.prophet_params = prophet_params or {}
        self.gbm_params = gbm_params or {}
        self.currency = currency

        self.prophet_model: Optional[Prophet] = None
        self.gbm_model: Optional[GradientBoostingRegressor] = None
        self.scaler: Optional[StandardScaler] = None

        self.is_fitted = False
        self.feature_names: List[str] = []

    def _prepare_prophet_data(
        self, data: List[Dict[str, Any]], timestamp_col: str = "timestamp", cost_col: str = "cost"
    ) -> pd.DataFrame:
        """
        准备Prophet数据

        参数:
            data: 成本数据
            timestamp_col: 时间戳字段名
            cost_col: 成本字段名

        返回:
            DataFrame with columns ['ds', 'y']
        """
        df = pd.DataFrame(data)

        if timestamp_col not in df.columns:
            raise ValueError(f"Timestamp column '{timestamp_col}' not found")
        if cost_col not in df.columns:
            raise ValueError(f"Cost column '{cost_col}' not found")

        df["ds"] = pd.to_datetime(df[timestamp_col])
        df["y"] = pd.to_numeric(df[cost_col], errors="coerce")

        df = df.dropna(subset=["ds", "y"])
        df = df.sort_values("ds")

        return df[["ds", "y"]]

    def _prepare_gbm_features(
        self,
        data: List[Dict[str, Any]],
        target_col: str = "cost",
        feature_cols: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备GradientBoosting特征

        参数:
            data: 数据列表
            target_col: 目标列名
            feature_cols: 特征列名列表

        返回:
            (特征矩阵, 目标向量)
        """
        df = pd.DataFrame(data)

        if feature_cols is None:
            # 自动选择数值特征
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if target_col in feature_cols:
                feature_cols.remove(target_col)

        if not feature_cols:
            raise ValueError("No feature columns found")

        self.feature_names = feature_cols

        X = df[feature_cols].values
        y = df[target_col].values

        # 处理缺失值
        X = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        y = np.nan_to_num(y, nan=0.0)

        return X, y

    def fit(
        self,
        data: List[Dict[str, Any]],
        timestamp_col: str = "timestamp",
        cost_col: str = "cost",
        feature_cols: Optional[List[str]] = None,
    ) -> None:
        """
        训练预测模型

        参数:
            data: 训练数据
            timestamp_col: 时间戳字段名
            cost_col: 成本字段名
            feature_cols: 特征列名列表（GBM用）
        """
        logger.info("Fitting cost forecaster with %d samples", len(data))

        # 训练Prophet
        if self.use_prophet and PROPHET_AVAILABLE:
            try:
                df = self._prepare_prophet_data(data, timestamp_col, cost_col)

                if len(df) >= 10:
                    self.prophet_model = Prophet(**self.prophet_params)
                    self.prophet_model.fit(df)
                    logger.info("Prophet model fitted")
                else:
                    logger.warning("Insufficient data for Prophet (need >= 10 points)")
            except Exception as e:
                logger.warning("Prophet fitting failed: %s", e)

        # 训练GradientBoosting
        if self.use_gbm and SKLEARN_AVAILABLE:
            try:
                X, y = self._prepare_gbm_features(data, cost_col, feature_cols)

                if len(X) >= 10:
                    self.scaler = StandardScaler()
                    X_scaled = self.scaler.fit_transform(X)

                    default_gbm_params = {
                        "n_estimators": 100,
                        "learning_rate": 0.1,
                        "max_depth": 5,
                        "random_state": 42,
                    }
                    gbm_params = {**default_gbm_params, **self.gbm_params}

                    self.gbm_model = GradientBoostingRegressor(**gbm_params)
                    self.gbm_model.fit(X_scaled, y)
                    logger.info("GradientBoosting model fitted")
                else:
                    logger.warning("Insufficient data for GBM (need >= 10 samples)")
            except Exception as e:
                logger.warning("GradientBoosting fitting failed: %s", e)

        self.is_fitted = True
        logger.info("Cost forecaster fitted successfully")

    def forecast(
        self, periods: int = 30, freq: str = "D", return_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        预测未来成本

        参数:
            periods: 预测未来periods个时间点
            freq: 预测频率（D=天, W=周, M=月）
            return_confidence: 是否返回置信区间

        返回:
            预测结果
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before forecasting")

        logger.info("Forecasting cost for %d periods", periods)

        predictions = []

        # Prophet预测
        if self.prophet_model is not None:
            future = self.prophet_model.make_future_dataframe(periods=periods, freq=freq)
            prophet_forecast = self.prophet_model.predict(future)

            # 只返回未来的预测
            future_forecast = prophet_forecast.tail(periods)

            for _, row in future_forecast.iterrows():
                pred = {
                    "timestamp": row["ds"].isoformat(),
                    "cost": row["yhat"],
                    "cost_lower": row["yhat_lower"] if return_confidence else None,
                    "cost_upper": row["yhat_upper"] if return_confidence else None,
                    "trend": row["trend"],
                    "currency": self.currency,
                    "model": "prophet",
                }
                predictions.append(pred)

        # 如果没有预测结果，返回空列表
        if not predictions:
            logger.warning("No predictions generated")
            return {
                "predictions": [],
                "metrics": {},
            }

        # 计算指标
        costs = [p["cost"] for p in predictions]
        metrics = {
            "forecast_periods": periods,
            "forecast_frequency": freq,
            "currency": self.currency,
            "total_forecasted_cost": sum(costs),
            "mean_daily_cost": np.mean(costs),
            "std_cost": np.std(costs),
            "min_cost": np.min(costs),
            "max_cost": np.max(costs),
            "growth_rate": (costs[-1] - costs[0]) / costs[0] if costs[0] != 0 else 0,
        }

        logger.info(
            "Cost forecasting completed: total=%.2f %s, growth=%.2f%%",
            metrics["total_forecasted_cost"],
            self.currency,
            metrics["growth_rate"] * 100,
        )

        return {
            "predictions": predictions,
            "metrics": metrics,
        }

    def predict_monthly_cost(self, forecast_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        预测月度成本

        参数:
            forecast_data: 预测数据

        返回:
            月度成本汇总
        """
        df = pd.DataFrame(forecast_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["month"] = df["timestamp"].dt.to_period("M")

        monthly_costs = df.groupby("month")["cost"].sum()

        monthly_summary = []
        for month, cost in monthly_costs.items():
            monthly_summary.append(
                {
                    "month": str(month),
                    "cost": float(cost),
                    "currency": self.currency,
                }
            )

        return {
            "monthly_costs": monthly_summary,
            "total_months": len(monthly_summary),
        }

    def recommend_cost_optimization(
        self,
        forecast_data: List[Dict[str, Any]],
        budget: Optional[float] = None,
        threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """
        推荐成本优化方案

        参数:
            forecast_data: 预测数据
            budget: 预算上限
            threshold: 成本增长告警阈值

        返回:
            优化建议
        """
        costs = [p["cost"] for p in forecast_data]
        total_cost = sum(costs)
        avg_cost = np.mean(costs)
        max_cost = max(costs)

        recommendations = []

        # 检查是否超出预算
        if budget is not None and total_cost > budget:
            recommendations.append(
                {
                    "type": "budget_exceeded",
                    "severity": "high",
                    "message": (
                        f"Forecasted cost {total_cost:.2f} {self.currency} "
                        f"exceeds budget {budget:.2f} {self.currency}"
                    ),
                    "suggested_action": (  # noqa: E501
                        "Review resource utilization and consider scaling down non-critical"
                        " services"
                    ),
                }
            )

        # 检查成本增长趋势
        if len(costs) >= 2:
            growth_rate = (costs[-1] - costs[0]) / costs[0] if costs[0] != 0 else 0
            if abs(growth_rate) > threshold:
                recommendations.append(
                    {
                        "type": "cost_growth",
                        "severity": "medium" if growth_rate > 0 else "low",
                        "message": (  # noqa: E501
                            f"Cost growth rate {growth_rate * 100:.2f}% exceeds threshold"
                            f" {threshold * 100:.2f}%"
                        ),
                        "suggested_action": (  # noqa: E501
                            "Analyze cost drivers and implement cost optimization measures"
                        ),
                    }
                )

        # 检查峰值成本
        if max_cost > avg_cost * 1.5:
            recommendations.append(
                {
                    "type": "peak_cost",
                    "severity": "medium",
                    "message": (
                        f"Peak cost {max_cost:.2f} {self.currency} is significantly "
                        f"higher than average {avg_cost:.2f} {self.currency}"
                    ),
                    "suggested_action": (  # noqa: E501
                        "Consider using spot instances or reserved instances for predictable"
                        " workloads"
                    ),
                }
            )

        # 通用优化建议
        general_recommendations = [
            "Review idle resources and terminate unused instances",
            "Use auto-scaling to match capacity with demand",
            "Leverage reserved instances for steady-state workloads",
            "Implement cost allocation tags for better visibility",
            "Schedule non-critical workloads during off-peak hours",
        ]

        return {
            "recommendations": recommendations,
            "general_recommendations": general_recommendations,
            "total_forecasted_cost": total_cost,
            "budget": budget,
            "budget_status": "exceeded" if budget and total_cost > budget else "within_budget",
        }

    def compare_with_actual(
        self, forecast_data: List[Dict[str, Any]], actual_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        比较预测与实际成本

        参数:
            forecast_data: 预测数据
            actual_data: 实际数据

        返回:
            比较结果
        """
        forecast_df = pd.DataFrame(forecast_data)
        actual_df = pd.DataFrame(actual_data)

        forecast_df["timestamp"] = pd.to_datetime(forecast_df["timestamp"])
        actual_df["timestamp"] = pd.to_datetime(actual_df["timestamp"])

        # 合并数据
        merged = pd.merge(
            forecast_df[["timestamp", "cost"]],
            actual_df[["timestamp", "cost"]],
            on="timestamp",
            suffixes=("_forecast", "_actual"),
        )

        if merged.empty:
            return {
                "error": "No matching timestamps between forecast and actual data",
            }

        # 计算误差指标
        merged["error"] = merged["cost_actual"] - merged["cost_forecast"]
        merged["abs_error"] = abs(merged["error"])
        merged["pct_error"] = (merged["error"] / merged["cost_actual"] * 100).replace(
            [np.inf, -np.inf], 0
        )

        metrics = {
            "mae": merged["abs_error"].mean(),  # Mean Absolute Error
            "mape": merged["pct_error"].mean(),  # Mean Absolute Percentage Error
            "rmse": np.sqrt((merged["error"] ** 2).mean()),  # Root Mean Square Error
            "total_forecast": merged["cost_forecast"].sum(),
            "total_actual": merged["cost_actual"].sum(),
            "total_error": merged["error"].sum(),
            "accuracy": (
                1 - (merged["abs_error"].sum() / merged["cost_actual"].sum())
                if merged["cost_actual"].sum() > 0
                else 0
            ),
        }

        return {
            "metrics": metrics,
            "comparison": merged.to_dict("records"),
        }

    def save_model(self, path: str) -> None:
        """保存模型"""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        import joblib

        model_data = {
            "prophet_model": self.prophet_model,
            "gbm_model": self.gbm_model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "currency": self.currency,
            "params": {
                "use_prophet": self.use_prophet,
                "use_gbm": self.use_gbm,
                "prophet_params": self.prophet_params,
                "gbm_params": self.gbm_params,
            },
        }
        joblib.dump(model_data, path)
        logger.info("Cost forecaster saved to %s", path)

    def load_model(self, path: str) -> None:
        """加载模型"""
        import joblib

        model_data = joblib.load(path)

        self.prophet_model = model_data["prophet_model"]
        self.gbm_model = model_data["gbm_model"]
        self.scaler = model_data["scaler"]
        self.feature_names = model_data["feature_names"]
        self.currency = model_data["currency"]

        params = model_data["params"]
        self.use_prophet = params["use_prophet"]
        self.use_gbm = params["use_gbm"]
        self.prophet_params = params["prophet_params"]
        self.gbm_params = params["gbm_params"]

        self.is_fitted = True
        logger.info("Cost forecaster loaded from %s", path)
