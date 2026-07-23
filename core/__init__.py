# -*- coding: utf-8 -*-
"""
AIOps Agent Core Module
=======================

This module provides the core functionality for the AIOps Agent system,
including AI engines, alert processing, authentication, and data collection.

Key Components:
- AI Engine: Intelligent analysis and decision making
- Alert Engine: Alert processing and correlation
- Authentication: JWT-based authentication and authorization
- Database: Async database operations with connection pooling
- Monitoring: System health and performance monitoring
"""

# core/__init__.py
# AIOps Agent 核心模块包
#
# 该包提供 AIOps Agent 项目的所有核心引擎模块:
#   - ai_engine          : MiniMax LLM 智能分析引擎(含规则降级)
#   - alert_engine       : 告警规则引擎(含 N-2 去重 + M-4 SSH 暴破检测 + M-5 动态阈值)
#   - approval_store     : 审批存储统一封装(BUG-FIX-24 解耦)
#   - auto_heal          : 告警自动修复联动引擎
#   - collector          : Windows 系统指标采集探针
#   - command_guard      : 高危指令护栏系统(双平台 50+ 规则)
#   - db_engine          : SQLite 持久化引擎(N-1 改造)
#   - linux_collector    : Linux 远程 SSH 采集引擎(10 维度)
#   - linux_repair       : Linux Bash 修复脚本库
#   - log_collector      : 日志采集引擎(Windows 事件日志 + Linux 远程日志)
#   - metrics_history    : 线程安全的环形指标历史缓冲区
#   - notify_engine      : 告警通知推送引擎(企微/钉钉/飞书)
#   - repair_engine      : Windows PowerShell 修复脚本库
#   - runbook_generator  : LLM 动态生成修复 Runbook(HITL 闭环核心)
#   - i18n               : 后端国际化引擎(中英文双语支持)
#   - stats_engine       : 真实统计引擎(MTTR/MTTD/降噪/RCA 准确率)
#   - topology_engine    : 拓扑管理引擎(M-3 阶段3-5)
#   - workflow_engine    : 工作流仿真引擎(SSE 流式输出)

"""
AIOps Agent 核心模块包

跨平台(Windows + Linux)智能运维 Agent 系统的核心引擎层。
提供从数据采集 → AI 根因分析 → 人工审批 → 自动修复 → 用户反馈的
端到端 HITL(Human-in-the-Loop)闭环自治能力。

典型使用方式:
    from core.collector import collect_all
    from core.ai_engine import analyze
    from core.alert_engine import alert_monitor_loop

详见各子模块的 docstring 与项目根目录的 README v2.1。
"""

# ============================================================
# 包元数据
# ============================================================
__version__: str = "2.2.0"  # 同步 main.py + api/__init__.py
__author__: str = "AIOps Agent Team"
__license__: str = "Proprietary"
__status__: str = "Production"  # Development / Beta / Production

# ============================================================
# 显式导出列表(控制 from core import * 行为)
# ============================================================
# 仅暴露包元数据,避免误用 from core import *
# 所有引擎模块都应显式 from core.<module> import <symbol> 导入
__all__: list[str] = [
    "__version__",
    "__author__",
    "__license__",
    "__status__",
]
