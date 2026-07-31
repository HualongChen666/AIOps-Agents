# -*- coding: utf-8 -*-
"""
coding_tools.py
---------------
扩展的代码/文件操作工具集，供 CodingSubAgent 使用。

功能：
- bash：执行 shell 命令
- read_file：读取文件内容
- write_to_file：写入/创建文件
- edit：替换文件内容
"""

from __future__ import annotations

import logging
import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.security import subprocess_runner

from .tools import Tool, ToolCategory, ToolExecutor, ToolRegistry

try:
    from core.command_guard import RiskLevel
    from core.command_guard import analyze_command as _analyze_command

    COMMAND_GUARD_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    COMMAND_GUARD_AVAILABLE = False
    RiskLevel = None  # type: ignore[misc,assignment]
    _analyze_command = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 沙箱/路径安全
# ----------------------------------------------------------------------


def _get_workspace_root() -> Path:
    """获取允许读写的 workspace 根目录。"""
    raw = os.environ.get("AIOPS_AGENT_WORKSPACE", os.getcwd())
    return Path(raw).resolve()


def _resolve_allowed_path(file_path: str, cwd: Optional[str] = None) -> Path:
    """将路径解析为绝对路径，并确保它位于 workspace 根目录下。

    规则：
    - 相对路径基于 cwd（如提供）或 workspace 根目录解析。
    - 绝对路径必须位于 workspace 根目录内。
    - 禁止包含 ``..`` 的路径穿越。
    - 路径解析后通过 `is_relative_to` 做 containment 校验。
    """
    workspace = _get_workspace_root()
    if cwd is not None:
        base = Path(cwd)
        if not base.is_absolute():
            base = workspace / base
        base = base.resolve()
    else:
        base = workspace

    raw_path = Path(file_path)
    if not raw_path.is_absolute():
        path = (base / raw_path).resolve()
    else:
        path = raw_path.resolve()

    if not path.is_relative_to(workspace):
        raise ValueError(
            f"Path '{file_path}' is outside workspace '{workspace}'. "
            "Only paths within the workspace are allowed."
        )
    return path


# 允许 CodeTool 处理的文件大小上限
_MAX_FILE_READ_BYTES = 1_000_000  # 1 MB
_MAX_FILE_WRITE_BYTES = 10_000_000  # 10 MB
_MAX_BASH_TIMEOUT = 300  # 5 minutes ceiling

# 默认 bash 超时（秒）
_DEFAULT_BASH_TIMEOUT = 30

# 当 command_guard 不可用时，bash 基本黑名单
_BASH_METACHAR_PATTERN = re.compile(r"[;|&$`\\<>{}\n\r]")  # type: ignore[name-defined]


# 禁止在 bash 工具中使用的网络/外联/安装工具
_DISALLOWED_BASH_BASE_COMMANDS = {
    "curl",
    "wget",
    "nc",
    "ncat",
    "netcat",
    "telnet",
    "ftp",
    "sftp",
    "scp",
    "ssh",
    "rsync",
    "lftp",
    "tftp",
    "pip",
    "pip3",
}


def _validate_command_args(args: List[str]) -> None:
    """在 command_guard 放行后，对参数做更细粒度的限制。"""
    if not args:
        raise ValueError("empty command")

    base = args[0].lower().lstrip("\\./")
    if base in _DISALLOWED_BASH_BASE_COMMANDS:
        raise ValueError(f"Command '{base}' is not allowed in the bash tool")

    recursive_flags = {"-R", "--recursive"}
    find_destructive = {"-delete", "-exec", "-execdir", "-ok", "-okdir"}
    interpreter_forbidden = {
        ("bash", "-c"),
        ("sh", "-c"),
        ("zsh", "-c"),
        ("dash", "-c"),
        ("ksh", "-c"),
        ("csh", "-c"),
        ("tcsh", "-c"),
        ("python", "-c"),
        ("python2", "-c"),
        ("python3", "-c"),
        ("node", "-e"),
        ("nodejs", "-e"),
        ("ruby", "-e"),
        ("perl", "-e"),
    }
    powershell_flags = {"-command", "-c", "-encodedcommand", "-ec"}

    for arg in args[1:]:
        arg_lower = arg.lower()

        # 禁止解释器参数形式（防御 command_guard 遗漏或 list 形式绕过）
        if (base, arg_lower) in interpreter_forbidden:
            raise ValueError(f"Interpreter flag '{arg}' is not allowed for '{base}'")
        if base in ("cmd", "cmd.exe") and arg_lower in ("/c", "/k"):
            raise ValueError("cmd /c or /k is not allowed")
        if (
            base in ("powershell", "pwsh", "powershell.exe", "pwsh.exe")
            and arg_lower in powershell_flags
        ):
            raise ValueError("PowerShell -Command is not allowed")

        # 禁止路径穿越和绝对路径参数（避免 ls /root、find /、cat /etc/passwd 等）
        if (
            re.search(r"(^|[/\\])\.\.($|[/\\])", arg)
            or arg.startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:", arg)
        ):
            raise ValueError(f"Argument contains path traversal or absolute path: {arg}")

        # 禁止明显的 shell 元字符
        if re.search(r"[;|`$()<>\n\r]", arg):
            raise ValueError(f"Argument contains dangerous characters: {arg}")

        # 禁止递归标志（ls -R /，grep -r /etc 等）
        if arg in recursive_flags:
            raise ValueError(f"Recursive flag '{arg}' is not allowed")
        if base == "grep" and arg_lower in ("-r", "--recursive"):
            raise ValueError("grep -r is not allowed")

        # 禁止 find 的 destructive/extraction 动作
        if base == "find" and arg_lower in find_destructive:
            raise ValueError(f"find action '{arg}' is not allowed")


def _validate_bash_command(command: Any) -> List[str]:
    """校验 bash 命令，返回安全的参数列表。

    优先使用 `command_guard.analyze_command` 做命令级风险评估；
    当不可用或无法解析时，回退到基本黑白名单校验。
    """
    if isinstance(command, str):
        cmd_str = command
    elif isinstance(command, (list, tuple)):
        # 将参数列表安全地拼回字符串供 command_guard 分析
        cmd_str = " ".join(shlex.quote(str(arg)) for arg in command)
    else:
        raise ValueError("command must be a string or list of strings")

    if not cmd_str or not cmd_str.strip():
        raise ValueError("empty command")

    if COMMAND_GUARD_AVAILABLE and callable(_analyze_command):
        result = _analyze_command(cmd_str)
        level = result.get("risk_level")
        if level in (RiskLevel.BLOCKED, RiskLevel.HIGH):
            raise ValueError(
                f"Command blocked by command_guard (risk={level.value}): "
                f"{result.get('reason', 'unknown')}"
            )
    else:
        # fallback：拒绝明显的 shell 元字符和路径穿越
        if _BASH_METACHAR_PATTERN.search(cmd_str):
            raise ValueError("Command contains disallowed shell metacharacters")
        if "../" in cmd_str or "..\\" in cmd_str:
            raise ValueError("Command contains path traversal attempt")

    # 最终使用 shlex 拆分执行；保持 shell=False
    if isinstance(command, str):
        args = shlex.split(command, posix=False)
    else:
        args = [str(arg) for arg in command]

    if not args:
        raise ValueError("empty command after splitting")
    _validate_command_args(args)
    return args


class CodeTool(Tool):
    """用于代码/文件操作的专用 Tool。

    与通用 Tool 不同，CodeTool 允许参数中包含代码字符（如 `;`、`:` 等），
    但仍然强制：
    - 参数名必须声明（required/optional/defaults/函数签名）。
    - `file_path`/`cwd` 必须位于 workspace 沙箱内。
    - `command` 必须过 `command_guard`（或 fallback 黑名单）。
    - `content`/`old_string`/`new_string` 受大小限制。
    """

    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """为代码/文件操作工具做安全校验。"""
        allowed = (
            set(self.required_params) | set(self.optional_params) | set(self.parameters.keys())
        )
        # 允许函数签名中显式声明的参数名（含 **kwargs 时放行所有 key）
        try:
            import inspect

            sig = inspect.signature(self.function)
            for param in sig.parameters.values():
                if param.kind == param.VAR_KEYWORD:
                    allowed = set(params.keys())
                    break
                allowed.add(param.name)
        except (TypeError, ValueError):
            pass

        for key, value in params.items():
            if key not in allowed:
                raise ValueError(
                    f"Parameter '{key}' is not allowed for tool '{self.name}'; "
                    f"allowed parameters are: {sorted(allowed)}"
                )

            if key in ("file_path", "cwd") and isinstance(value, str):
                _resolve_allowed_path(value)

            if key == "command":
                _validate_bash_command(value)

            if key == "content" and isinstance(value, str):
                if len(value.encode("utf-8")) > _MAX_FILE_WRITE_BYTES:
                    raise ValueError(
                        f"Parameter '{key}' exceeds maximum size of {_MAX_FILE_WRITE_BYTES} bytes"
                    )

            if key in ("old_string", "new_string") and isinstance(value, str):
                if len(value.encode("utf-8")) > _MAX_FILE_WRITE_BYTES:
                    raise ValueError(
                        f"Parameter '{key}' exceeds maximum size of {_MAX_FILE_WRITE_BYTES} bytes"
                    )

            if key in ("timeout",) and value is not None:
                try:
                    t = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Parameter '{key}' must be an integer") from exc
                if t < 1 or t > _MAX_BASH_TIMEOUT:
                    raise ValueError(f"Parameter '{key}' must be between 1 and {_MAX_BASH_TIMEOUT}")


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------


def _bash(command: Any, cwd: Optional[str] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    """执行 shell 命令。

    Parameters
    ----------
    command: str | list
        命令字符串或参数列表。
    cwd: str, optional
        工作目录，必须位于 workspace 沙箱内。
    timeout: int, optional
        命令最大执行秒数，默认 30，最大 300。
    """
    args = _validate_bash_command(command)
    resolved_cwd = _resolve_allowed_path(cwd) if cwd else _get_workspace_root()

    if timeout is None:
        timeout = _DEFAULT_BASH_TIMEOUT
    else:
        timeout = max(1, min(int(timeout), _MAX_BASH_TIMEOUT))

    try:
        result = subprocess_runner.run(  # nosec B603
            args,
            cwd=str(resolved_cwd),
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
    except subprocess_runner.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        raise RuntimeError(
            f"Command timed out after {timeout}s: {args}\n" f"stdout:\n{stdout}\nstderr:\n{stderr}"
        ) from exc

    output = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {args}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    return output


def _read_file(file_path: str) -> str:
    """读取文件内容。文件必须位于 workspace 沙箱内，且大小不超过 1 MB。"""
    if len(file_path) > 4096:
        raise ValueError("file_path exceeds maximum length of 4096")
    if "\x00" in file_path:
        raise ValueError("file_path contains null bytes")
    path = _resolve_allowed_path(file_path)
    if not path.is_file():
        raise ValueError(f"Path '{file_path}' is not a regular file")
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size = path.stat().st_size
    if size > _MAX_FILE_READ_BYTES:
        raise ValueError(
            f"File '{file_path}' is {size} bytes, exceeding maximum {_MAX_FILE_READ_BYTES}"
        )

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File '{file_path}' is not valid UTF-8 text: {exc}") from exc


def _write_to_file(file_path: str, content: str) -> Dict[str, Any]:
    """写入文件，必要时创建父目录。路径受 workspace 沙箱限制。"""
    if len(file_path) > 4096:
        raise ValueError("file_path exceeds maximum length of 4096")
    if "\x00" in file_path:
        raise ValueError("file_path contains null bytes")
    path = _resolve_allowed_path(file_path)
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > _MAX_FILE_WRITE_BYTES:
        raise ValueError(f"Content exceeds maximum size of {_MAX_FILE_WRITE_BYTES} bytes")

    # 仅允许在 workspace 内创建目录
    workspace = _get_workspace_root()
    resolved_parent = path.parent.resolve()
    if not resolved_parent.is_relative_to(workspace):
        raise ValueError(f"Parent directory of '{file_path}' is outside workspace")
    resolved_parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"status": "success", "file_path": str(path)}


def _edit(file_path: str, old_string: str, new_string: str) -> Dict[str, Any]:
    """替换文件中的字符串。路径受 workspace 沙箱限制。"""
    if len(file_path) > 4096:
        raise ValueError("file_path exceeds maximum length of 4096")
    if "\x00" in file_path:
        raise ValueError("file_path contains null bytes")
    if old_string == "":
        raise ValueError(
            "old_string cannot be empty (would insert new_string between every character)"
        )

    if len(old_string.encode("utf-8")) > _MAX_FILE_WRITE_BYTES:
        raise ValueError("old_string exceeds maximum size")
    if len(new_string.encode("utf-8")) > _MAX_FILE_WRITE_BYTES:
        raise ValueError("new_string exceeds maximum size")

    path = _resolve_allowed_path(file_path)
    if not path.is_file():
        raise ValueError(f"Path '{file_path}' is not a regular file")

    content = path.read_text(encoding="utf-8")
    if old_string not in content:
        raise ValueError(f"old_string not found in {file_path}")

    content = content.replace(old_string, new_string)
    path.write_text(content, encoding="utf-8")
    return {
        "status": "success",
        "file_path": str(path),
        "replacements": content.count(new_string),
    }


# ----------------------------------------------------------------------
# 工具注册表
# ----------------------------------------------------------------------
class CodingToolRegistry(ToolRegistry):
    """包含代码/文件操作工具的注册表。"""

    def _initialize_default_tools(self) -> None:
        """加载基础工具 + 代码/文件操作工具。"""
        super()._initialize_default_tools()

        self.register(
            CodeTool(
                name="bash",
                description="执行 shell 命令（如 pytest、python 脚本）",
                category=ToolCategory.EXECUTION,
                function=_bash,
                required_params=["command"],
                optional_params=["cwd", "timeout"],
            )
        )

        self.register(
            CodeTool(
                name="read_file",
                description="读取文件内容",
                category=ToolCategory.DIAGNOSTIC,
                function=_read_file,
                required_params=["file_path"],
            )
        )

        self.register(
            CodeTool(
                name="write_to_file",
                description="写入或创建文件",
                category=ToolCategory.EXECUTION,
                function=_write_to_file,
                required_params=["file_path", "content"],
            )
        )

        self.register(
            CodeTool(
                name="edit",
                description="替换文件中的字符串",
                category=ToolCategory.EXECUTION,
                function=_edit,
                required_params=["file_path", "old_string", "new_string"],
            )
        )


def create_coding_tool_executor() -> ToolExecutor:
    """创建包含代码/文件操作工具的执行器。"""
    return ToolExecutor(CodingToolRegistry())
