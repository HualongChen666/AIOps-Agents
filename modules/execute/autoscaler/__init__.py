# -*- coding: utf-8 -*-
"""
Autoscaler Module
弹性伸缩控制器模块

功能:
- Kubernetes HPA自定义指标
- 容量预测驱动的伸缩
- 伸缩策略推荐
"""

from .custom_hpa_controller import CustomHPAController, ScalingPolicy

__all__ = [
    "CustomHPAController",
    "ScalingPolicy",
]
