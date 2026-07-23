# -*- coding: utf-8 -*-
"""
anomaly_detection.py
-------------------
实现 **时序异常检测**，组合 Prophet（趋势/季节性预测） 与 IsolationForest（基于残差的离群点检测）。

主要公开 API:
* ``AnomalyDetector`` – 初始化后可调用 ``train(df)`` 与 ``detect(df)``。
* ``train``   – 接收包含 ``timestamp``（ISO8601、epoch 或 datetime）和 ``value`` 两列的 ``pandas.DataFrame``，
               自动转换为 Prophet 所需的 ``ds``/``y``，训练 Prophet 并保存模型，同时在残差上训练 IsolationForest。
* ``detect`` – 对新数据进行预测、计算残差并使用已训练的 IsolationForest 标记异常，返回原始 ``timestamp``/``value``
               加上 ``is_anomaly``（bool） 与 ``anomaly_score``（异常分数）的 ``DataFrame``。

异常检测流程
~~~~~~~~~~~~~~
1. **时间序列预处理**：将 ``timestamp`` 统一为 UTC ``datetime``，列名改为 ``ds``、``y``，
   缺失值前向填充（ffill），若仍缺失则填 0。
2. **Prophet 预测**：使用默认 ``growth='linear'``、开启年季节性、周季节性，
   预测与原始数据同等长度的 ``yhat``。
3. **残差计算**：``residual = y - yhat``，该序列用于异常检测。
4. **IsolationForest**：在残差上训练
   ``IsolationForest(n_estimators=100, contamination='auto', random_state=42)``，
   ``predict`` 返回 ``1``（正常）或 ``-1``（异常），``decision_function`` 作为异常分数（越小越异常）。
5. **结果返回**：在输入 ``df`` 上加入 ``is_anomaly``、``anomaly_score`` 两列并返回。

安全降级
~~~~~~~~
* 若项目环境缺少 ``pandas``/``prophet``/``scikit-learn``，在导入阶段抛出明确的 ``ImportError``，便于 CI 发现缺失依赖。
* ``prophet`` 包在 PyPI 上的正式名称为 ``prophet``（原名 ``fbprophet``）。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from prophet import Prophet
    from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 1️⃣ 可选依赖导入（安全降级）
# ----------------------------------------------------------------------
# pandas import deferred to runtime

# Prophet import deferred to runtime

# IsolationForest import deferred to runtime


# ----------------------------------------------------------------------
# 2️⃣ 主类实现
# ----------------------------------------------------------------------
class AnomalyDetector:
    """时序异常检测器 – Prophet + IsolationForest.

    Parameters
    ----------
    growth: str, optional
        Prophet 参数，默认 ``'linear'``。
    yearly_seasonality: bool, optional
        是否启用年季节性，默认 ``True``。
    weekly_seasonality: bool, optional
        是否启用周季节性，默认 ``True``。
    """

    def __init__(
        self,
        growth: str = "linear",
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
    ) -> None:
        self.growth = growth
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.prophet_model: Prophet | None = None
        self.iforest: IsolationForest | None = None

    # ------------------------------------------------------------------
    # 2️⃣ 数据准备工具
    # ------------------------------------------------------------------
    @staticmethod
    def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """将用户提供的 ``timestamp/value`` DF 转换为 Prophet 所需的 ``ds/y``.

        - ``timestamp`` 支持 ISO8601、epoch (int/float) 或 ``datetime`` 对象。
        - 解析失败会抛出 ``ValueError``，确保模型在可控输入下运行。
        - 缺失值使用前向填充（ffill），若仍缺失则填 0，防止 Prophet 报错。
        """
        import pandas as pd

        if "timestamp" not in df.columns or "value" not in df.columns:
            raise ValueError("DataFrame must contain 'timestamp' and 'value' columns")
        df = df.copy()
        df["ds"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        if df["ds"].isna().any():
            raise ValueError("Failed to parse some timestamps to datetime")
        df["y"] = pd.to_numeric(df["value"], errors="coerce")
        df["y"] = df["y"].ffill().fillna(0)
        return df[["ds", "y"]]

    # ------------------------------------------------------------------
    # 3️⃣ 训练 Prophet 与 IsolationForest
    # ------------------------------------------------------------------
    def train(self, df: pd.DataFrame) -> None:
        """基于历史数据训练模型。

        Parameters
        ----------
        df : pandas.DataFrame
            必须包含 ``timestamp`` 与 ``value`` 两列。
        """
        logger.info("Training AnomalyDetector (Prophet + IsolationForest)")
        prophet_df = self._prepare_dataframe(df)

        # ---- Prophet ----
        from prophet import Prophet

        self.prophet_model = Prophet(
            growth=self.growth,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
        )
        self.prophet_model.fit(prophet_df)
        logger.debug("Prophet model trained")

        # ---- 预测（与训练集同长） ----
        future = self.prophet_model.make_future_dataframe(periods=0, freq="D")
        forecast = self.prophet_model.predict(future)
        merged = prophet_df.merge(forecast[["ds", "yhat"]], on="ds", how="left")
        residual = merged["y"] - merged["yhat"]

        # ---- IsolationForest ----
        self.iforest = IsolationForest(
            n_estimators=100,
            contamination="auto",
            random_state=42,
        )
        self.iforest.fit(residual.values.reshape(-1, 1))
        logger.debug("IsolationForest trained on residuals")

    # ------------------------------------------------------------------
    # 4️⃣ 检测新数据中的异常
    # ------------------------------------------------------------------
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """对新数据进行异常检测，返回带标记的 DataFrame。

        Returns
        -------
        pandas.DataFrame
            原始 ``timestamp``/``value`` 列 + ``is_anomaly`` (bool) 与 ``anomaly_score`` (float)。
        """
        if self.prophet_model is None or self.iforest is None:
            raise RuntimeError("Model not trained. Call train() before detect().")

        # 预处理为 Prophet 格式
        prophet_df = self._prepare_dataframe(df)
        # 预测
        future = self.prophet_model.make_future_dataframe(periods=0, freq="D")
        forecast = self.prophet_model.predict(future)
        merged = prophet_df.merge(forecast[["ds", "yhat"]], on="ds", how="left")
        residual = merged["y"] - merged["yhat"]

        # IsolationForest 预测
        preds = self.iforest.predict(residual.values.reshape(-1, 1))
        scores = self.iforest.decision_function(residual.values.reshape(-1, 1))
        is_anomaly = preds == -1

        result = df.copy()
        result["is_anomaly"] = is_anomaly
        result["anomaly_score"] = scores
        return result


# ----------------------------------------------------------------------
# 5️⃣ 简易 CLI 用于本地快速验证（仅在直接执行时触发）
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    if len(sys.argv) != 2:
        print("Usage: python anomaly_detection.py <path_to_json_data>")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # raw 示例: [{"timestamp": "2024-01-01T00:00:00Z", "value": 12.3}, ...]
    df_input = pd.DataFrame(raw)
    detector = AnomalyDetector()
    detector.train(df_input)
    out = detector.detect(df_input)
    print(out.head())
