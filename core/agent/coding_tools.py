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

import shlex
import subprocess  # nosec B404
from pathlib import Path
from typing import Any, Dict, Optional

from .tools import Tool, ToolCategory, ToolExecutor, ToolRegistry


class CodeTool(Tool):
    r"""禁用参数字符验证的工具，用于代码/文件操作。

    默认的 Tool 会拒绝包含 `;`、`|`、``\`` 等字符的字符串参数，
    这对 Windows 路径和代码编辑不友好。CodeTool 跳过这类通用验证，
    由具体工具函数自行负责安全。
    """

    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """跳过危险字符验证，信任上层调用。"""
        return


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------


def _bash(command: Any, cwd: Optional[str] = None) -> Dict[str, Any]:
    """执行 shell 命令。

    Parameters
    ----------
    command: str | list
        命令字符串或参数列表。
    cwd: str, optional
        工作目录。
    """
    if isinstance(command, str):
        args = shlex.split(command, posix=False)
    elif isinstance(command, (list, tuple)):
        args = list(command)
    else:
        raise ValueError("command must be a string or list")

    if not args:
        raise ValueError("empty command")

    result = subprocess.run(  # nosec B603
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=False,
    )

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
    """读取文件内容。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text(encoding="utf-8")


def _write_to_file(file_path: str, content: str) -> Dict[str, Any]:
    """写入文件，必要时创建父目录。"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"status": "success", "file_path": str(path)}


def _edit(file_path: str, old_string: str, new_string: str) -> Dict[str, Any]:
    """替换文件中的字符串。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

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
                optional_params=["cwd"],
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
