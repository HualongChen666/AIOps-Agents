# -*- coding: utf-8 -*-
"""
causal_service.py
-----------------
因果分析服务 - 生产环境集成。

提供与现有系统兼容的接口，支持：
- 因果图学习
- 根因识别
- 反事实推理
- 因果效应估计
- 模型热更新
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import HTTPException

from .causal_graph_builder import (
    CausalGraphBuilder,
    CausalGraphPersistence,
    create_causal_graph_builder,
)
from .causal_inference import (  # noqa: F401
    CausalGraph,
    CausalRootCauseAnalyzer,
    create_causal_analyzer,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 因果分析服务
# ----------------------------------------------------------------------
class CausalAnalysisService:
    """因果分析服务"""

    def __init__(
        self,
        model_dir: str = "models/causal",
        discovery_method: str = "pc",
    ):
        """
        Parameters
        ----------
        model_dir : str
            模型目录
        discovery_method : str
            因果发现方法
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.discovery_method = discovery_method

        self.builder: Optional[CausalGraphBuilder] = None
        self.analyzer: Optional[CausalRootCauseAnalyzer] = None
        self.causal_graph: Optional[CausalGraph] = None
        self.is_initialized = False

    def initialize(
        self,
        metrics_data: pd.DataFrame,
        discovery_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        初始化服务

        Parameters
        ----------
        metrics_data : pd.DataFrame
            指标数据
        discovery_params : Dict[str, Any], optional
            因果发现参数

        Returns
        -------
        bool
            是否初始化成功
        """
        try:
            # 创建因果图构建器
            self.builder = create_causal_graph_builder(
                discovery_method=self.discovery_method,
                discovery_params=discovery_params,
            )

            # 学习因果图
            self.causal_graph = self.builder.build_from_metrics(metrics_data)

            # 创建分析器
            self.analyzer = self.builder.get_analyzer()

            self.is_initialized = True
            logger.info("Causal analysis service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            return False

    def identify_root_cause(
        self,
        alert_var: str,
        current_data: pd.DataFrame,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        识别根因

        Parameters
        ----------
        alert_var : str
            告警变量
        current_data : pd.DataFrame
            当前数据
        top_k : int
            返回前 k 个根因

        Returns
        -------
        List[Dict[str, Any]]
            根因候选列表
        """
        if not self.is_initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")

        assert self.analyzer is not None
        return self.analyzer.identify_root_cause(alert_var, current_data, top_k)

    def explain_root_cause(
        self,
        root_cause: Dict[str, Any],
        alert_var: str,
        current_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        解释根因

        Parameters
        ----------
        root_cause : Dict[str, Any]
            根因信息
        alert_var : str
            告警变量
        current_data : pd.DataFrame
            当前数据

        Returns
        -------
        Dict[str, Any]
            解释信息
        """
        if not self.is_initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")

        assert self.analyzer is not None
        return self.analyzer.explain_root_cause(root_cause, alert_var, current_data)

    def estimate_causal_effect(
        self,
        treatment: str,
        outcome: str,
        data: pd.DataFrame,
        treatment_values: List[float] = [0.0, 1.0],
    ) -> Dict[str, float]:
        """
        估计因果效应

        Parameters
        ----------
        treatment : str
            处理变量
        outcome : str
            结果变量
        data : pd.DataFrame
            数据
        treatment_values : List[float]
            处理值列表

        Returns
        -------
        Dict[str, float]
            因果效应估计
        """
        if not self.is_initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")

        assert self.analyzer is not None
        assert self.analyzer.do_calculus is not None
        return self.analyzer.do_calculus.estimate_causal_effect(
            treatment, outcome, data, treatment_values
        )

    def counterfactual_query(
        self,
        factual: Dict[str, float],
        intervention: Dict[str, float],
        outcome_var: str,
        data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        反事实查询

        Parameters
        ----------
        factual : Dict[str, float]
            事实状态
        intervention : Dict[str, float]
            反事实干预
        outcome_var : str
            结果变量
        data : pd.DataFrame
            数据

        Returns
        -------
        Dict[str, Any]
            反事实结果
        """
        if not self.is_initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")

        assert self.analyzer is not None
        assert self.analyzer.counterfactual is not None
        return self.analyzer.counterfactual.what_if(factual, intervention, outcome_var, data)

    def save_model(self, name: str = "causal_graph") -> str:
        """
        保存模型

        Parameters
        ----------
        name : str
            模型名称

        Returns
        -------
        str
            保存路径
        """
        if not self.is_initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")

        assert self.causal_graph is not None
        path = self.model_dir / f"{name}.json"
        CausalGraphPersistence.save(self.causal_graph, str(path))
        return str(path)

    def load_model(self, name: str = "causal_graph") -> bool:
        """
        加载模型

        Parameters
        ----------
        name : str
            模型名称

        Returns
        -------
        bool
            是否加载成功
        """
        path = self.model_dir / f"{name}.json"

        if not path.exists():
            logger.warning(f"Model file not found: {path}")
            return False

        try:
            self.causal_graph = CausalGraphPersistence.load(str(path))

            # 重新创建分析器
            self.builder = create_causal_graph_builder(
                discovery_method=self.discovery_method,
            )
            self.builder.causal_graph = self.causal_graph
            self.analyzer = self.builder.get_analyzer()

            self.is_initialized = True
            logger.info(f"Model loaded from {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


# ----------------------------------------------------------------------
# 2️⃣ 全局服务实例
# -*-
_global_service: Optional[CausalAnalysisService] = None


def get_service() -> CausalAnalysisService:
    """获取全局服务实例"""
    global _global_service

    if _global_service is None:
        _global_service = CausalAnalysisService()

    return _global_service


def initialize_service(
    metrics_data: pd.DataFrame,
    discovery_method: str = "pc",
    discovery_params: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    初始化服务

    Returns
    -------
    bool
        是否初始化成功
    """
    service = get_service()
    service.discovery_method = discovery_method
    return service.initialize(metrics_data, discovery_params)


def shutdown_service():
    """关闭服务"""
    global _global_service
    _global_service = None


# ----------------------------------------------------------------------
# 3️⃣ FastAPI 路由集成
# ----------------------------------------------------------------------
def create_router():
    """创建 FastAPI 路由"""
    from fastapi import APIRouter

    router = APIRouter(prefix="/root-cause/causal", tags=["root-cause-causal"])

    @router.post("/initialize")
    async def initialize(
        metrics_data: Dict[str, List[float]],
        discovery_method: str = "pc",
    ):
        """初始化服务"""
        df = pd.DataFrame(metrics_data)
        success = initialize_service(df, discovery_method)
        return {"success": success, "initialized": success}

    @router.post("/root-cause")
    async def identify_root_cause(
        alert_var: str,
        current_data: Dict[str, List[float]],
        top_k: int = 5,
    ):
        """识别根因"""
        service = get_service()
        df = pd.DataFrame(current_data)
        results = service.identify_root_cause(alert_var, df, top_k)
        return results

    @router.post("/explain")
    async def explain_root_cause(
        root_cause: Dict[str, Any],
        alert_var: str,
        current_data: Dict[str, List[float]],
    ):
        """解释根因"""
        service = get_service()
        df = pd.DataFrame(current_data)
        explanation = service.explain_root_cause(root_cause, alert_var, df)
        return explanation

    @router.post("/causal-effect")
    async def estimate_causal_effect(
        treatment: str,
        outcome: str,
        data: Dict[str, List[float]],
        treatment_values: List[float] = [0.0, 1.0],
    ):
        """估计因果效应"""
        service = get_service()
        df = pd.DataFrame(data)
        effect = service.estimate_causal_effect(treatment, outcome, df, treatment_values)
        return effect

    @router.post("/counterfactual")
    async def counterfactual_query(
        factual: Dict[str, float],
        intervention: Dict[str, float],
        outcome_var: str,
        data: Dict[str, List[float]],
    ):
        """反事实查询"""
        service = get_service()
        df = pd.DataFrame(data)
        result = service.counterfactual_query(factual, intervention, outcome_var, df)
        return result

    @router.post("/model/save")
    async def save_model(name: str = "causal_graph"):
        """保存模型"""
        service = get_service()
        path = service.save_model(name)
        return {"success": True, "path": path}

    @router.post("/model/load")
    async def load_model(name: str = "causal_graph"):
        """加载模型"""
        service = get_service()
        success = service.load_model(name)
        return {"success": success, "loaded": success}

    @router.get("/status")
    async def status():
        """获取服务状态"""
        service = get_service()
        return {
            "initialized": service.is_initialized,
            "discovery_method": service.discovery_method,
        }

    return router


# ----------------------------------------------------------------------
# 4️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 生成测试数据
    logger.info("Creating test data")
    np.random.seed(42)
    n_samples = 1000

    X = np.random.randn(n_samples)
    Y = 0.5 * X + np.random.randn(n_samples) * 0.5
    Z = 0.3 * Y + np.random.randn(n_samples) * 0.7

    metrics_data = pd.DataFrame(
        {
            "service_A": X,
            "service_B": Y,
            "service_C": Z,
        }
    )

    # 测试服务
    logger.info("Testing causal analysis service")
    success = initialize_service(metrics_data)

    if success:
        # 测试根因识别
        root_causes = get_service().identify_root_cause("service_C", metrics_data)
        logger.info(f"Root causes: {root_causes}")

        # 测试因果效应
        effect = get_service().estimate_causal_effect("service_A", "service_C", metrics_data)
        logger.info(f"Causal effect: {effect}")

        # 测试保存/加载
        path = get_service().save_model()
        logger.info(f"Model saved to {path}")

        shutdown_service()
        get_service().load_model()
        logger.info("Model loaded successfully")

    logger.info("Test passed!")
