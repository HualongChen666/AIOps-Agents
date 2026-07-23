# -*- coding: utf-8 -*-
"""
transformer_service.py
----------------------
Transformer 异常检测服务 - 生产环境集成。

提供与现有系统兼容的接口，支持：
- 模型加载和卸载
- 实时异常检测
- 批量检测
- 模型热更新
- 性能监控
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union  # noqa: F401

import numpy as np
import pandas as pd
import torch
from fastapi import HTTPException

from .data_preprocessing import TimeSeriesPreprocessingPipeline
from .transformer_model import (
    TransformerAnomalyDetector,
    TransformerAnomalyDetectorWrapper,
    create_transformer_model,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 模型管理器
# ----------------------------------------------------------------------
class TransformerModelManager:
    """Transformer 模型管理器"""

    def __init__(
        self,
        model_dir: str = "models/anomaly",
        model_name: str = "transformer_anomaly_detector.pth",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """
        Parameters
        ----------
        model_dir : str
            模型目录
        model_name : str
            模型文件名
        device : str
            设备
        """
        self.model_dir = Path(model_dir)
        self.model_name = model_name
        self.device = device
        self.model: Optional[TransformerAnomalyDetector] = None
        self.wrapper: Optional[TransformerAnomalyDetectorWrapper] = None
        self.preprocessor: Optional[TimeSeriesPreprocessingPipeline] = None
        self.is_loaded = False

    def load_model(
        self,
        model_path: Optional[Union[str, Path]] = None,
        input_dim: int = 1,
        d_model: int = 128,
        n_heads: int = 8,
        n_layers: int = 4,
        d_ff: int = 512,
        threshold: float = 0.5,
    ) -> bool:
        """
        加载模型

        Parameters
        ----------
        model_path : str, optional
            模型路径，如果为 None 则使用默认路径
        input_dim : int
            输入维度
        d_model : int
            模型维度
        n_heads : int
            注意力头数
        n_layers : int
            层数
        d_ff : int
            前馈维度
        threshold : float
            异常阈值

        Returns
        -------
        bool
            是否加载成功
        """
        try:
            # 参数验证
            if not 0 <= threshold <= 1:
                raise ValueError(f"threshold must be in [0, 1], got {threshold}")

            if model_path is None:
                model_path = self.model_dir / self.model_name

            # 安全检查：防止路径遍历攻击
            model_path = Path(model_path).resolve()  # type: ignore[arg-type]
            if not str(model_path).startswith(str(self.model_dir.resolve())):
                logger.error(f"Invalid model path (outside model directory): {model_path}")
                return False

            if not model_path.exists():
                logger.warning(f"Model file not found: {model_path}")
                return False

            # 创建模型
            self.model = create_transformer_model(
                input_dim=input_dim,
                d_model=d_model,
                n_heads=n_heads,
                n_layers=n_layers,
                d_ff=d_ff,
            )

            # 加载权重（使用 weights_only=True 防止代码注入）
            state_dict = torch.load(str(model_path), map_location=self.device, weights_only=True)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()

            # 创建推理包装器
            self.wrapper = TransformerAnomalyDetectorWrapper(
                model=self.model,
                device=self.device,
                threshold=threshold,
            )

            # 创建预处理器
            self.preprocessor = TimeSeriesPreprocessingPipeline(
                clean_missing=True,
                clean_outliers=False,
                add_features=True,
                scale=True,
                scale_method="standard",
                augment=False,
            )

            self.is_loaded = True
            logger.info(f"Model loaded successfully from {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def unload_model(self):
        """卸载模型"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.wrapper is not None:
            del self.wrapper
            self.wrapper = None
        if self.preprocessor is not None:
            del self.preprocessor
            self.preprocessor = None

        self.is_loaded = False
        logger.info("Model unloaded")

    def reload_model(self, **kwargs) -> bool:
        """
        重新加载模型

        Returns
        -------
        bool
            是否加载成功
        """
        self.unload_model()
        return self.load_model(**kwargs)


# ----------------------------------------------------------------------
# 2️⃣ 异常检测服务
# ----------------------------------------------------------------------
class TransformerAnomalyService:
    """Transformer 异常检测服务"""

    def __init__(
        self,
        model_manager: TransformerModelManager,
    ):
        """
        Parameters
        ----------
        model_manager : TransformerModelManager
            模型管理器
        """
        self.model_manager = model_manager

    def detect_single(
        self,
        data: List[float],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
    ) -> Dict[str, Any]:
        """
        检测单个时序数据的异常

        Parameters
        ----------
        data : List[float]
            时序数据
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名

        Returns
        -------
        Dict[str, Any]
            检测结果
        """
        if not self.model_manager.is_loaded:
            raise HTTPException(status_code=503, detail="Model not loaded")

        assert self.model_manager.preprocessor is not None
        assert self.model_manager.wrapper is not None

        # 转换为 DataFrame
        timestamps = pd.date_range("2024-01-01", periods=len(data), freq="1min")
        df = pd.DataFrame(
            {
                timestamp_col: timestamps,
                value_col: data,
            }
        )

        # 预处理
        processed_data = self.model_manager.preprocessor.process(
            df,
            timestamp_col,
            value_col,
        )

        # 检测
        is_anomaly, anomaly_scores = self.model_manager.wrapper.detect(processed_data)

        return {
            "is_anomaly": bool(is_anomaly.any()),
            "anomaly_count": int(is_anomaly.sum()),
            "anomaly_scores": anomaly_scores.tolist(),
            "max_anomaly_score": float(anomaly_scores.max()),
            "mean_anomaly_score": float(anomaly_scores.mean()),
        }

    def detect_batch(
        self,
        data: List[List[float]],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
    ) -> List[Dict[str, Any]]:
        """
        批量检测异常

        Parameters
        ----------
        data : List[List[float]]
            多个时序数据
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名

        Returns
        -------
        List[Dict[str, Any]]
            检测结果列表
        """
        results = []

        for i, series in enumerate(data):
            try:
                result = self.detect_single(series, timestamp_col, value_col)
                result["series_id"] = i
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to detect series {i}: {e}")
                results.append(
                    {
                        "series_id": i,
                        "error": str(e),
                    }
                )

        return results

    def detect_from_dataframe(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        value_col: str = "value",
    ) -> pd.DataFrame:
        """
        从 DataFrame 检测异常

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名

        Returns
        -------
        pd.DataFrame
            带异常标记的 DataFrame
        """
        if not self.model_manager.is_loaded:
            raise HTTPException(status_code=503, detail="Model not loaded")

        assert self.model_manager.preprocessor is not None
        assert self.model_manager.wrapper is not None

        # 预处理
        processed_data = self.model_manager.preprocessor.process(
            df,
            timestamp_col,
            value_col,
        )

        # 检测
        is_anomaly, anomaly_scores = self.model_manager.wrapper.detect(processed_data)

        # 添加结果到原始 DataFrame
        result_df = df.copy()
        result_df["is_anomaly"] = is_anomaly
        result_df["anomaly_score"] = anomaly_scores

        return result_df


# ----------------------------------------------------------------------
# 3️⃣ 全局服务实例
# ----------------------------------------------------------------------
# 创建全局模型管理器
_global_model_manager = TransformerModelManager()

# 创建全局服务实例
_global_service: Optional[TransformerAnomalyService] = None


def get_model_manager() -> TransformerModelManager:
    """获取全局模型管理器"""
    return _global_model_manager


def get_service() -> TransformerAnomalyService:
    """获取全局服务实例"""
    global _global_service

    if _global_service is None:
        _global_service = TransformerAnomalyService(_global_model_manager)

    return _global_service


def initialize_service(
    model_path: Optional[str] = None,
    input_dim: int = 1,
    d_model: int = 128,
    n_heads: int = 8,
    n_layers: int = 4,
    d_ff: int = 512,
    threshold: float = 0.5,
) -> bool:
    """
    初始化服务

    Returns
    -------
    bool
        是否初始化成功
    """
    manager = get_model_manager()
    return manager.load_model(
        model_path=model_path,
        input_dim=input_dim,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        threshold=threshold,
    )


def shutdown_service():
    """关闭服务"""
    manager = get_model_manager()
    manager.unload_model()


# ----------------------------------------------------------------------
# 4️⃣ FastAPI 路由集成
# ----------------------------------------------------------------------
def create_router():
    """创建 FastAPI 路由"""
    from fastapi import APIRouter

    router = APIRouter(prefix="/anomaly/transformer", tags=["anomaly-transformer"])

    @router.post("/detect")
    async def detect_anomaly(
        data: List[float],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
    ):
        """检测异常"""
        service = get_service()
        result = service.detect_single(data, timestamp_col, value_col)
        return result

    @router.post("/detect-batch")
    async def detect_anomaly_batch(
        data: List[List[float]],
        timestamp_col: str = "timestamp",
        value_col: str = "value",
    ):
        """批量检测异常"""
        service = get_service()
        results = service.detect_batch(data, timestamp_col, value_col)
        return results

    @router.post("/model/load")
    async def load_model(
        model_path: Optional[str] = None,
        input_dim: int = 1,
        d_model: int = 128,
        n_heads: int = 8,
        n_layers: int = 4,
        d_ff: int = 512,
        threshold: float = 0.5,
    ):
        """加载模型"""
        manager = get_model_manager()
        success = manager.load_model(
            model_path=model_path,
            input_dim=input_dim,
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            d_ff=d_ff,
            threshold=threshold,
        )
        return {"success": success, "loaded": manager.is_loaded}

    @router.post("/model/unload")
    async def unload_model():
        """卸载模型"""
        manager = get_model_manager()
        manager.unload_model()
        return {"success": True, "loaded": manager.is_loaded}

    @router.get("/model/status")
    async def model_status():
        """获取模型状态"""
        manager = get_model_manager()
        return {
            "loaded": manager.is_loaded,
            "device": manager.device,
            "model_path": str(manager.model_dir / manager.model_name),
        }

    return router


# ----------------------------------------------------------------------
# 5️⃣ 兼容性接口（与现有系统集成）
# ----------------------------------------------------------------------
class TransformerAnomalyDetectorCompat:
    """兼容现有系统的异常检测器接口"""

    def __init__(self, model_path: Optional[str] = None, threshold: float = 0.5, **model_kwargs):
        """
        Parameters
        ----------
        model_path : str, optional
            模型路径
        threshold : float
            异常阈值
        model_kwargs : dict
            模型参数
        """
        self.manager = TransformerModelManager()
        self.manager.load_model(model_path, threshold=threshold, **model_kwargs)
        self.service = TransformerAnomalyService(self.manager)

    def train(self, df: pd.DataFrame):
        """
        训练接口（兼容性，实际训练使用 train_transformer.py）

        Note
        ----
        Transformer 模型训练使用独立的训练脚本，此方法仅用于兼容
        """
        logger.warning("Transformer training should use train_transformer.py")

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测接口（兼容现有系统）

        Parameters
        ----------
        df : pd.DataFrame
            必须包含 timestamp 和 value 列

        Returns
        -------
        pd.DataFrame
            带异常标记的 DataFrame
        """
        return self.service.detect_from_dataframe(df)


# ----------------------------------------------------------------------
# 6️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO)

    # 测试服务
    logger.info("Testing Transformer Anomaly Service")

    # 初始化服务
    success = initialize_service()
    if not success:
        logger.error("Failed to initialize service")
        sys.exit(1)

    # 测试检测
    test_data = [100 + i * 0.1 + np.random.randn() * 0.5 for i in range(100)]
    result = get_service().detect_single(test_data)

    logger.info(f"Detection result: {result}")

    # 关闭服务
    shutdown_service()

    logger.info("Test passed!")
