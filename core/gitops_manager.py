# -*- coding: utf-8 -*-
"""
gitops_manager.py
-----------------
提供 **GitOps + Argo Rollout** 的轻量化 Python 封装。
- 采用 **安全懒加载**：只有在实际调用时才 import ``subprocess``、``yaml``、
  ``kubernetes``（若已安装）。
- 当运行环境没有 ``kubectl`` / ``argo`` 二进制或缺少 ``kubernetes`` Python 客户端时，
  模块会记录 warning 并退化为 **no‑op**，保证 CI / 单元测试不因外部依赖崩溃。
- 主要 API：
    - ``apply_manifest(manifest_path)`` – 用 ``kubectl apply -f`` 部署 Argo Rollout/其他资源。
    - ``get_rollout_status(name, namespace='default')`` – 返回 ``kubectl argo rollouts get rollout`` 的简要状态。  # noqa: E501
    - ``rollback(name, to_revision=None, namespace='default')`` – 触发
      ``kubectl argo rollouts undo``，若 ``to_revision`` 为 ``None`` 则回滚到上一次成功的版本。
- 所有函数返回 ``True/False``（成功/失败）并在内部记录 ``logging`` 信息，调用方可自行决定异常处理。
"""

import logging
import os
import shutil
from typing import Optional

from core.security import subprocess_runner

logger = logging.getLogger(__name__)


def _run_cmd(cmd: list[str]) -> subprocess_runner.CompletedProcess:
    """内部助手：执行外部命令并捕获 stdout / stderr。
    若命令不可用（FileNotFoundError）或返回非 0 退出码，记录错误并返回对应对象。
    """
    try:
        result = subprocess_runner.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,  # nosec B603
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "Command %s failed (code %s): %s",
                " ".join(cmd),
                result.returncode,
                result.stderr.strip(),
            )
        else:
            logger.debug("Command %s succeeded: %s", " ".join(cmd), result.stdout.strip())
        return result
    except FileNotFoundError:
        logger.warning(
            "Command not found: %s – ensure the binary is installed and in PATH.", cmd[0]
        )
        # 返回一个伪对象，code 127 代表 command not found
        return subprocess_runner.CompletedProcess(cmd, 127, stdout="", stderr="command not found")


def _ensure_kubeconfig() -> str:
    """返回可用的 kubeconfig 路径，优先环境变量 ``KUBECONFIG``，若不存在则尝试默认 ``~/.kube/config``。"""
    kubeconfig = os.getenv("KUBECONFIG")
    if kubeconfig and os.path.isfile(kubeconfig):
        return kubeconfig
    default_path = os.path.expanduser("~/.kube/config")
    if os.path.isfile(default_path):
        return default_path
    logger.warning("Kubeconfig not found – many GitOps operations will fail in this environment.")
    return ""


class GitOpsManager:
    """包装常见的 GitOps / Argo Rollout 操作。
    所有方法都采用 **安全降级**：如果系统缺少 ``kubectl`` 或 ``argo`` 可执行文件，
    将仅记录 warning 并返回 ``False``，不抛异常。
    """

    def __init__(self, kubeconfig: Optional[str] = None):
        self.kubeconfig = kubeconfig or _ensure_kubeconfig()
        self._kubectl = shutil.which("kubectl")
        self._argo = shutil.which("argo")
        if not self._kubectl:
            logger.warning("kubectl not found in PATH – GitOps operations will be no‑op.")
        if not self._argo:
            logger.warning("argo CLI not found in PATH – Argo Rollout commands will be no‑op.")

    # ------------------------------------------------------------------
    # Manifest 相关
    # ------------------------------------------------------------------
    def apply_manifest(self, manifest_path: str) -> bool:
        """使用 ``kubectl apply -f <manifest>`` 部署或更新资源。
        成功返回 ``True``，失败（包括二进制缺失）返回 ``False``。
        """
        if not self._kubectl:
            logger.warning("apply_manifest: kubectl unavailable – skipping.")
            return False
        if not os.path.isfile(manifest_path):
            logger.error("Manifest file not found: %s", manifest_path)
            return False
        cmd = [self._kubectl, "apply", "-f", manifest_path]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        result = _run_cmd(cmd)
        return result.returncode == 0

    # ------------------------------------------------------------------
    # Rollout 状态查询
    # ------------------------------------------------------------------
    def get_rollout_status(self, name: str, namespace: str = "default") -> Optional[str]:
        """返回 ``kubectl argo rollouts get rollout <name> -n <ns> -o yaml`` 的简要状态。
        若 ``argo`` 不可用或命令失败返回 ``None``。
        """
        if not self._argo:
            logger.warning("get_rollout_status: argo CLI unavailable – returning None.")
            return None
        cmd = [self._argo, "rollouts", "get", "rollout", name, "-n", namespace, "-o", "yaml"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        result = _run_cmd(cmd)
        if result.returncode != 0:
            return None
        # 只返回前几行的简要信息，避免返回巨量 yaml
        return "\n".join(result.stdout.splitlines()[:20])

    # ------------------------------------------------------------------
    # Rollback / Undo
    # ------------------------------------------------------------------
    def rollback(
        self, name: str, to_revision: Optional[int] = None, namespace: str = "default"
    ) -> bool:
        """执行 ``kubectl argo rollouts undo <name>``。
        * ``to_revision`` 为 ``None`` 时回滚到上一次成功的版本；否则回滚到指定的 revision 编号。
        返回 ``True`` 表示命令执行成功。
        """
        if not self._argo:
            logger.warning("rollback: argo CLI unavailable – skipping.")
            return False
        cmd = [self._argo, "rollouts", "undo", name, "-n", namespace]
        if to_revision is not None:
            cmd.extend(["--revision", str(to_revision)])
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        result = _run_cmd(cmd)
        return result.returncode == 0

    # ------------------------------------------------------------------
    # 直接调用 ``kubectl`` 的简易查询（可选）
    # ------------------------------------------------------------------
    def get_resource(self, kind: str, name: str, namespace: str = "default") -> Optional[str]:
        """使用 ``kubectl get <kind> <name> -n <ns> -o yaml`` 获取任意资源的 YAML。
        这在调试或灾难恢复时非常有用。
        """
        if not self._kubectl:
            logger.warning("get_resource: kubectl unavailable – returning None.")
            return None
        cmd = [self._kubectl, "get", kind, name, "-n", namespace, "-o", "yaml"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        result = _run_cmd(cmd)
        return result.stdout if result.returncode == 0 else None

    # ------------------------------------------------------------------
    # 高层恢复流程（示例）
    # ------------------------------------------------------------------
    def disaster_recover(self, rollout_name: str, namespace: str = "default") -> bool:
        """灾难恢复的简易流程：
        1. 检查当前 rollout 状态。
        2. 若发现 ``Paused`` 或 ``Progressing`` 超时，尝试回滚到上一次成功的 revision。
        3. 再次获取状态确认恢复成功。
        该函数是 **示例实现**，业务方可根据自身需求自定义更细粒度的判断逻辑。
        """
        status = self.get_rollout_status(rollout_name, namespace)
        if status is None:
            logger.error("Unable to fetch rollout status for %s/%s", namespace, rollout_name)
            return False
        # 简单判断：若 output 包含 "paused" 或 "progressing" 则尝试回滚
        lowered = status.lower()
        if "paused" in lowered or "progressing" in lowered:
            logger.info("Rollout %s appears unhealthy – initiating rollback.", rollout_name)
            if not self.rollback(rollout_name, namespace=namespace):
                logger.error("Rollback failed for %s/%s", namespace, rollout_name)
                return False
            # 再次确认状态
            new_status = self.get_rollout_status(rollout_name, namespace)
            logger.info(
                "Post‑rollback status: %s", new_status.splitlines()[0] if new_status else "none"
            )
        else:
            logger.info("Rollout %s is healthy – no recovery needed.", rollout_name)
        return True


# ----------------------------------------------------------------------
# 单例导出 – 项目全局使用同一个 manager（保持轻量）
# ----------------------------------------------------------------------
_gitops_manager = GitOpsManager()


def get_manager() -> GitOpsManager:
    """返回全局的 ``GitOpsManager`` 实例，供外部代码直接调用。
    通过函数而非直接变量暴露，便于未来改为惰性初始化。
    """
    return _gitops_manager
