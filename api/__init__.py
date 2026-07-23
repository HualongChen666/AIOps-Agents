# -*- coding: utf-8 -*-
"""
API Module
==========

Provides RESTful API endpoints for the AIOps Agent system.
Includes routers for alerts, metrics, workflows, topology, and APM.

Key Features:
- RESTful API design
- OpenAPI specification
- Request validation
- Error handling
- Authentication and authorization
"""

# api/__init__.py
# AIOps Agent API 路由包
#
# 该包提供 AIOps Agent 项目的所有 REST API 路由模块:
#   - ai_router              : AI 根因分析(M-1 富上下文增强)
#   - ai_feedback_router     : AI 反馈闭环接口(M-2)
#   - alert_router           : 告警查询/清空
#   - autoheal_router        : HITL 自动修复审批工作流
#   - guard_router           : 高危指令审查 + 审计
#   - linux_router           : Linux 远程监控 + 修复
#   - log_router             : Windows + Linux 日志采集
#   - metrics_router         : 系统指标采集(30s TTL 缓存)
#   - notify_router          : 通知渠道配置 + 热重载
#   - repair_router          : Windows PowerShell 修复执行
#   - stats_router           : 真实统计数据(内部接口需密钥)
#   - topology_router        : 拓扑管理(M-3 五阶段)
#   - workflow_router        : 工作流仿真 SSE(20 并发限流)

"""
AIOps Agent API 路由包

提供 100+ REST 接口,覆盖系统监控、AI 分析、自动修复、HITL 审批等核心能力。

典型路由前缀:
    /api/metrics/*    系统指标
    /api/alerts/*     告警管理
    /api/ai/*         AI 分析与反馈
    /api/autoheal/*   HITL 审批闭环
    /api/repair/*     Windows 修复
    /api/linux/*      Linux 监控与修复
    /api/topology/*   拓扑管理
    /api/workflow/*   工作流仿真(SSE)
    /api/guard/*      指令护栏
    /api/notify/*     通知配置
    /api/stats/*      真实统计
    /api/logs/*       日志采集

详见各子模块的 docstring 与 OpenAPI 文档(/docs)。
"""

# ============================================================
# 包元数据
# ============================================================
__version__: str = "2.2.0"  # 与 README v2.2 同步
__author__: str = "AIOps Agent Team"
__license__: str = "Proprietary"
__status__: str = "Production"

# ============================================================
# 显式导出列表
# ============================================================
__all__: list[str] = [
    "__version__",
    "__author__",
    "__license__",
    "__status__",
]
