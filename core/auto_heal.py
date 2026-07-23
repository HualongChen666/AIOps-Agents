# -*- coding: utf-8 -*-
"""
core/auto_heal.py

自动修复（Auto‑Heal）核心业务逻辑。

- 根据告警（Alert）触发对应的修复脚本（Repair）；
- 记录修复结果、验证过程以及审批状态；
- 通过 LangChain/LLM 生成修复建议（可选）；
- 所有关键步骤均写入结构化审计日志。

P2 Enhancement:
- 扩展修复脚本库
- 跨平台支持（Windows/Linux/macOS）
- 风险评估机制

依赖的底层数据库函数（insert_alert、insert_verify_record、upsert_pending_approval 等）
在 **core/db_engine.py** 中提供同步占位实现，亦有异步实现用于生产环境。

"""

from __future__ import annotations

import asyncio
import json
import logging
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from core.ai_engine import analyze

# 项目内部依赖
from core.db_engine import (
    insert_repair_record,
    insert_verify_record,
    update_approval_status,
    upsert_pending_approval,
)
from core.rag_engine import search_similar

# 日志
_logger = logging.getLogger(__name__)


# ============================================================
# P2 Enhancement: Platform Support
# ============================================================
class PlatformType(Enum):
    """Supported platforms for repair scripts"""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


# ============================================================
# P2 Enhancement: Risk Assessment
# ============================================================
class RiskLevel(Enum):
    """Risk levels for repair operations"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RepairScript:
    """Repair script configuration"""

    script_key: str
    name: str
    description: str
    platforms: List[PlatformType]
    risk_level: RiskLevel
    script_content: str
    requires_approval: bool = False
    estimated_duration_seconds: int = 60
    rollback_script: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """Risk assessment for repair operation"""

    risk_level: RiskLevel
    risk_factors: List[str]
    mitigation_strategies: List[str]
    approval_required: bool
    confidence_score: float
    potential_impact: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# P2 Enhancement: Extended Repair Script Library
# ============================================================
class RepairScriptLibrary:
    """
    P2 Enhanced repair script library with cross-platform support
    """

    def __init__(self):
        self.scripts: Dict[str, RepairScript] = {}
        self._initialize_default_scripts()

    def _initialize_default_scripts(self):
        """Initialize default repair scripts for common scenarios"""
        # CPU high repair script
        self.register_script(
            RepairScript(
                script_key="cpu_high_script",
                name="High CPU Usage Repair",
                description="Identify and terminate high CPU processes",
                platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                script_content=self._get_cpu_repair_script(),
                rollback_script=self._get_cpu_rollback_script(),
            )
        )

        # Memory high repair script
        self.register_script(
            RepairScript(
                script_key="memory_high_script",
                name="High Memory Usage Repair",
                description="Clear memory cache and optimize memory usage",
                platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                script_content=self._get_memory_repair_script(),
            )
        )

        # Disk high repair script
        self.register_script(
            RepairScript(
                script_key="disk_high_script",
                name="High Disk Usage Repair",
                description="Clean temporary files and logs",
                platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                script_content=self._get_disk_repair_script(),
            )
        )

        # Service restart repair script
        self.register_script(
            RepairScript(
                script_key="service_restart_script",
                name="Service Restart",
                description="Restart failed or hung services",
                platforms=[
                    PlatformType.LINUX,
                    PlatformType.WINDOWS,
                    PlatformType.DOCKER,
                    PlatformType.KUBERNETES,
                ],
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                script_content=self._get_service_restart_script(),
                rollback_script=self._get_service_rollback_script(),
            )
        )

    def register_script(self, script: RepairScript) -> None:
        """Register a repair script in the library"""
        self.scripts[script.script_key] = script
        _logger.info(f"Registered repair script: {script.script_key}")

    def get_script(self, script_key: str) -> Optional[RepairScript]:
        """Get a repair script by key"""
        return self.scripts.get(script_key)

    def get_scripts_for_platform(self, platform: PlatformType) -> List[RepairScript]:
        """Get all scripts compatible with a platform"""
        return [script for script in self.scripts.values() if platform in script.platforms]

    def _get_cpu_repair_script(self) -> str:
        """Get CPU repair script content (cross-platform)"""
        return """
# CPU High Usage Repair Script
import psutil
import os

def repair_cpu_high():
    # Identify top CPU consuming processes
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            if proc.info['cpu_percent'] > 50:
                processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Sort by CPU usage
    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)

    # Log top processes
    for proc in processes[:5]:
        print(f"High CPU process: {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu_percent']}%)")

    return processes
"""

    def _get_cpu_rollback_script(self) -> str:
        """Get CPU repair rollback script"""
        return """
# CPU Repair Rollback Script
# Restore any terminated processes (if recorded)
print("CPU repair rollback - no action needed for this repair type")
"""

    def _get_memory_repair_script(self) -> str:
        """Get memory repair script content"""
        return """
# Memory High Usage Repair Script
import gc
import psutil

def repair_memory_high():
    # Force garbage collection
    gc.collect()

    # Clear system caches (Linux)
    if os.name == 'posix':
        os.system('sync && echo 3 > /proc/sys/vm/drop_caches')

    # Log memory usage before and after
    mem = psutil.virtual_memory()
    print(f"Memory usage: {mem.percent}%")

    return mem.percent
"""

    def _get_disk_repair_script(self) -> str:
        """Get disk repair script content"""
        return """
# Disk High Usage Repair Script
import os
import tempfile
import shutil

def repair_disk_high():
    # Clean temporary files
    temp_dir = tempfile.gettempdir()
    cleaned_size = 0

    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        try:
            if os.path.isfile(filepath):
                file_size = os.path.getsize(filepath)
                os.remove(filepath)
                cleaned_size += file_size
        except Exception as e:
            print(f"Failed to remove {filename}: {e}")

    print(f"Cleaned {cleaned_size / (1024*1024):.2f} MB from temp directory")
    return cleaned_size
"""

    def _get_service_restart_script(self) -> str:
        """Get service restart script content"""
        return """
# Service Restart Repair Script
import subprocess
import platform

def restart_service(service_name):
    system = platform.system().lower()

    if system == 'linux':
        # Systemd-based systems
        subprocess.run(['systemctl', 'restart', service_name], check=True)
    elif system == 'windows':
        # Windows services
        subprocess.run(['net', 'stop', service_name], check=True)
        subprocess.run(['net', 'start', service_name], check=True)
    elif system == 'darwin':
        # macOS (launchctl)
        subprocess.run(['launchctl', 'restart', service_name], check=True)

    return True
"""

    def _get_service_rollback_script(self) -> str:
        """Get service restart rollback script"""
        return """
# Service Restart Rollback Script
import subprocess
import platform

def rollback_service_restart(service_name):
    system = platform.system().lower()

    # Stop the service (reverses the restart)
    if system == 'linux':
        subprocess.run(['systemctl', 'stop', service_name], check=True)
    elif system == 'windows':
        subprocess.run(['net', 'stop', service_name], check=True)

    return True
"""


# ============================================================
# P2 Enhancement: Risk Assessment Engine
# ============================================================
class RiskAssessmentEngine:
    """
    P2 Enhanced risk assessment for repair operations
    """

    def __init__(self):
        self.risk_factors: Dict[str, List[str]] = {
            "production": ["affects live users", "potential data loss"],
            "database": ["data corruption risk", "downtime impact"],
            "network": ["connectivity loss", "security implications"],
            "storage": ["data loss risk", "performance degradation"],
        }

    def assess_repair_risk(self, script: RepairScript, context: Dict[str, Any]) -> RiskAssessment:
        """
        Assess the risk of a repair operation

        Args:
            script: Repair script to assess
            context: Context information (environment, time, etc.)

        Returns:
            Risk assessment result
        """
        risk_factors = []
        mitigation_strategies = []
        approval_required = script.requires_approval
        confidence_score = 0.8

        # Base risk from script
        if script.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            risk_factors.append(f"High-risk operation: {script.risk_level.value}")
            approval_required = True

        # Environmental factors
        environment = context.get("environment", "development")
        if environment == "production":
            risk_factors.extend(self.risk_factors.get("production", []))
            approval_required = True
            confidence_score = 0.6

        # Time-based factors
        current_hour = datetime.now().hour
        if 0 <= current_hour < 6:  # Off-peak hours
            mitigation_strategies.append("Scheduled during off-peak hours")
            confidence_score += 0.1
        elif 18 <= current_hour <= 22:  # Peak hours
            risk_factors.append("Scheduled during peak hours")
            confidence_score -= 0.1

        # Mitigation strategies
        if script.rollback_script:
            mitigation_strategies.append("Rollback script available")
            confidence_score += 0.1

        mitigation_strategies.append("Monitoring enabled during repair")
        mitigation_strategies.append("Backup recommended before execution")

        # Determine final risk level
        if len(risk_factors) >= 3 or script.risk_level == RiskLevel.CRITICAL:
            final_risk = RiskLevel.CRITICAL
        elif len(risk_factors) >= 2 or script.risk_level == RiskLevel.HIGH:
            final_risk = RiskLevel.HIGH
        elif len(risk_factors) >= 1 or script.risk_level == RiskLevel.MEDIUM:
            final_risk = RiskLevel.MEDIUM
        else:
            final_risk = RiskLevel.LOW

        confidence_score = max(0.0, min(1.0, confidence_score))

        return RiskAssessment(
            risk_level=final_risk,
            risk_factors=risk_factors,
            mitigation_strategies=mitigation_strategies,
            approval_required=approval_required,
            confidence_score=confidence_score,
            potential_impact={
                "estimated_duration": script.estimated_duration_seconds,
                "affected_components": context.get("affected_components", []),
            },
        )


# ============================================================
# P2 Enhancement: Cross-Platform Script Executor
# ============================================================
class CrossPlatformScriptExecutor:
    """
    P2 Enhanced cross-platform script executor
    """

    def __init__(self):
        self.current_platform = self._detect_platform()
        self.script_library = RepairScriptLibrary()
        self.risk_engine = RiskAssessmentEngine()

    def _detect_platform(self) -> PlatformType:
        """Detect current platform"""
        system = platform.system().lower()
        if system == "windows":
            return PlatformType.WINDOWS
        elif system == "linux":
            return PlatformType.LINUX
        elif system == "darwin":
            return PlatformType.MACOS
        else:
            return PlatformType.LINUX  # Default to Linux

    def execute_script(
        self, script_key: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a repair script with cross-platform support

        Args:
            script_key: Script to execute
            context: Execution context

        Returns:
            Execution result
        """
        script = self.script_library.get_script(script_key)
        if not script:
            return {
                "success": False,
                "error": f"Script not found: {script_key}",
            }

        # Check platform compatibility
        if self.current_platform not in script.platforms:
            return {
                "success": False,
                "error": f"Script not compatible with platform {self.current_platform.value}",
            }

        # Assess risk
        risk_assessment = self.risk_engine.assess_repair_risk(script, context or {})

        # Check approval requirement
        if risk_assessment.approval_required:
            return {
                "success": False,
                "requires_approval": True,
                "risk_assessment": {
                    "risk_level": risk_assessment.risk_level.value,
                    "risk_factors": risk_assessment.risk_factors,
                    "mitigation_strategies": risk_assessment.mitigation_strategies,
                    "confidence_score": risk_assessment.confidence_score,
                },
            }

        # Execute script
        try:
            result = self._execute_script_content(script.script_content)
            return {
                "success": True,
                "output": result,
                "duration": script.estimated_duration_seconds,
                "risk_assessment": {
                    "risk_level": risk_assessment.risk_level.value,
                    "confidence_score": risk_assessment.confidence_score,
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "rollback_available": script.rollback_script is not None,
            }

    def _execute_script_content(self, script_content: str) -> str:
        """Execute script content safely"""
        # In production, this would execute in a sandboxed environment
        # For now, we'll just return a simulated result
        return f"Executed script successfully on {self.current_platform.value}"

    def get_available_scripts(self) -> List[Dict[str, Any]]:
        """Get list of available scripts for current platform"""
        scripts = self.script_library.get_scripts_for_platform(self.current_platform)
        return [
            {
                "script_key": script.script_key,
                "name": script.name,
                "description": script.description,
                "risk_level": script.risk_level.value,
                "requires_approval": script.requires_approval,
            }
            for script in scripts
        ]


# ============================================================
# P2 Enhancement: Global instances
# ============================================================
repair_script_library = RepairScriptLibrary()
risk_assessment_engine = RiskAssessmentEngine()
cross_platform_executor = CrossPlatformScriptExecutor()


# ----------------------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------------------
async def _create_alert_record(alert: Dict[str, Any]) -> str:
    """
    将告警写入数据库，返回生成的 alert_id。
    """
    try:
        from core.db_engine import alert_repository

        alert_id = await alert_repository.save(alert)
        _logger.info("Alert inserted, id=%s", alert_id)
        return alert_id
    except Exception as exc:
        _logger.error("Failed to insert alert: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Alert storage failure")


def _create_verify_record(**kwargs) -> int:
    """
    写入 VerifyRecord 表，返回生成的 id。
    """
    try:
        verify_id = insert_verify_record(**kwargs)
        _logger.info("Verify record inserted, id=%s", verify_id)
        return verify_id
    except Exception as exc:
        _logger.error("Failed to insert verify record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Verify storage failure")


def _create_pending_approval(alert_id: int, rule_name: str, script_key: str, proposal: str) -> None:
    """
    将待审批的维修建议写入 PendingApproval 表。
    """
    try:
        upsert_pending_approval(
            alert_id=str(alert_id),
            rule_name=rule_name,
            script_key=script_key,
            proposal=proposal,
            alert_json=json.dumps({"alert_id": alert_id, "rule_name": rule_name}),
        )
        _logger.info("Pending approval created for alert_id=%s", alert_id)
    except Exception as exc:
        _logger.error("Failed to upsert pending approval: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Approval storage failure")


def _finalize_approval(alert_id: int, status: str) -> None:
    """
    更新审批状态（approved / rejected），并记录审计日志。
    """
    try:
        update_approval_status(alert_id=str(alert_id), status=status)
        _logger.info("Approval status updated: alert_id=%s, status=%s", alert_id, status)
    except Exception as exc:
        _logger.error("Failed to update approval status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Approval update failure")


# ----------------------------------------------------------------------
# 主业务入口
# ----------------------------------------------------------------------
def handle_alert(alert_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    接收原始告警（JSON），执行以下流程：

    1. 将告警写入数据库（AlertHistory）。
    2. 根据告警关联的规则（rule_name）检索对应的修复脚本（script_key）。
    3. 调用修复脚本（此处使用占位函数 simulate_repair）。
    4. 将修复结果写入 RepairRecord 表。
    5. 触发验证（verify）步骤，写入 VerifyRecord。
    6. 如验证需要人工介入，生成 Runbook（RAG + LLM）并写入 PendingApproval。
    7. 返回统一的响应结构。

    参数
    ----
    alert_payload : dict
        完整的告警 JSON（来自监控系统）。

    返回
    ----
    dict
        包含 `alert_id`, `repair_id`, `verify_id`, `runbook`（若有） 等关键信息。
    """
    # ------------------------------------------------------------------
    # 1️⃣ 记录告警
    # ------------------------------------------------------------------
    alert_id = asyncio.run(_create_alert_record(alert_payload))

    # ------------------------------------------------------------------
    # 2️⃣ 根据告警获取修复脚本（这里用 placeholder 实现）
    # ------------------------------------------------------------------
    rule_name = alert_payload.get("rule_name", "default_rule")
    script_key = f"{rule_name}_script"

    # ------------------------------------------------------------------
    # 3️⃣ 执行修复（模拟）
    # ------------------------------------------------------------------
    repair_result = simulate_repair(alert_payload, script_key)

    # ------------------------------------------------------------------
    # 4️⃣ 写入 RepairRecord
    # ------------------------------------------------------------------
    repair_id = insert_repair_record(
        success=repair_result["success"],
        alert_time=alert_payload.get("detected_at", datetime.now(timezone.utc).isoformat()),
        repair_time=datetime.now(timezone.utc).isoformat(),
        repair_duration_sec=repair_result["duration"],
        rule_name=rule_name,
        script_key=script_key,
        platform=alert_payload.get("platform", "windows"),
        output=repair_result["output"],
    )
    _logger.info("Repair record inserted, id=%s", repair_id)

    # ------------------------------------------------------------------
    # 5️⃣ 验证（使用占位 verify_result）
    # ------------------------------------------------------------------
    verify_result = simulate_verify(alert_payload, repair_result)

    # ------------------------------------------------------------------
    # 6️⃣ 记录 VerifyRecord
    # ------------------------------------------------------------------
    verify_id = _create_verify_record(
        repair_id=repair_id,
        alert_id=str(alert_id),
        script_key=script_key,
        host=alert_payload.get("host", "unknown"),
        platform=alert_payload.get("platform", "windows"),
        verified=verify_result.get("verified"),
        strategy=verify_result.get("strategy", "auto"),
        confidence=verify_result.get("confidence", 0.0),
        evidence_json=verify_result.get("evidence", {}),
        duration_sec=verify_result.get("duration_sec", 0.0),
        error_msg=verify_result.get("error_msg", ""),
    )

    # ------------------------------------------------------------------
    # 7️⃣ 如需要人工确认，生成 Runbook（RAG + LLM）
    # ------------------------------------------------------------------
    runbook_text = ""
    if verify_result.get("needs_human"):
        # 使用 RAG 检索相关文档并让 LLM 生成 Runbook
        rag_context = search_similar(
            query=alert_payload.get("title", ""),
            top_k=5,
        )
        # 把检索到的文档拼接成一个长文本（payload 内容）
        context_text = "\n\n".join([hit["payload"].get("content", "") for hit in rag_context])
        prompt = (
            "You are an AI Ops assistant. Generate a concise Runbook to address the following alert:\n"  # noqa: E501
            f"Alert Title: {alert_payload.get('title')}\n"
            f"Alert Details: {json.dumps(alert_payload, ensure_ascii=False)}\n"
            f"Relevant Context:\n{context_text}\n"
        )
        runbook_text = analyze(prompt, rich_context=context_text)

        # 写入 PendingApproval（待人工审核）
        _create_pending_approval(
            alert_id=(
                int(alert_id) if alert_id.isdigit() else hash(alert_id) % (10**6)
            ),  # Convert to int
            rule_name=rule_name,
            script_key=script_key,
            proposal=runbook_text,
        )

    # ------------------------------------------------------------------
    # 8️⃣ 返回统一响应
    # ------------------------------------------------------------------
    response = {
        "alert_id": alert_id,
        "repair_id": repair_id,
        "verify_id": verify_id,
        "runbook": runbook_text,
    }
    _logger.info("Auto‑heal flow completed: %s", response)
    return response


# ----------------------------------------------------------------------
# 模拟修复、验证函数（占位实现，仅用于演示）
# ----------------------------------------------------------------------
def simulate_repair(alert: Dict[str, Any], script_key: str) -> Dict[str, Any]:
    """
    占位修复函数，实际项目中应调用对应平台的修复脚本。

    返回示例：
    {
        "success": True,
        "duration": 12.3,
        "output": "修复成功，已重启服务。"
    }
    """
    _logger.debug("Simulating repair for script_key=%s", script_key)
    # 简单模拟耗时与输出
    return {
        "success": True,
        "duration": 5.0,
        "output": f"Executed script {script_key} successfully.",
    }


def simulate_verify(alert: Dict[str, Any], repair_result: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate verification after repair (for testing)."""
    return {"passed": True, "message": "Verification passed"}


# Stub functions for test compatibility
def trigger_auto_heal(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger auto-heal process."""
    return handle_alert(alert)


async def try_auto_heal(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Async wrapper used by core.alert_engine."""
    return trigger_auto_heal(alert)


def approve_repair(alert_id: int) -> Dict[str, Any]:
    """Approve a pending repair."""
    return {"status": "approved", "alert_id": alert_id}


def reject_repair(alert_id: int | str, reason: str = "") -> Dict[str, Any]:
    """Reject a pending repair."""
    return {"status": "rejected", "alert_id": alert_id, "reason": reason}


def get_pending_approvals() -> List[Dict[str, Any]]:
    """Get all pending approvals."""
    return []
