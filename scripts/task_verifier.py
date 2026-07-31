# -*- coding: utf-8 -*-
"""用于 SubAgent 并行执行的任务验证器。

每个 14.1-17.8 子任务对应一个命令；SubAgent 通过 bash 调用
  python scripts/task_verifier.py --task <14.1>
验证任务是否实现，返回 stdout 与 exit code。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from core.security import subprocess_runner

ROOT = Path(__file__).resolve().parent.parent


def _python_c(code: str) -> List[str]:
    """返回 python -c 命令列表。"""
    return ["python", "-c", code]


def pytest(*files: str) -> List[str]:
    """运行 pytest 指定测试文件。"""
    return ["python", "-m", "pytest", *files, "-q", "--no-cov"]


def check_file(*paths: str) -> List[str]:
    """检查文件是否存在。"""
    return _python_c(
        "import pathlib; missing=[p for p in "
        + str(list(paths))
        + " if not pathlib.Path(p).exists()]; "
        "assert not missing, 'missing: ' + str(missing); "
        "print('OK')"
    )


def check_source(path: str, *keywords: str) -> List[str]:
    """检查源码文件中是否包含任意关键字。"""
    return _python_c(
        "import pathlib; src=pathlib.Path('"
        + path
        + "').read_text(encoding='utf-8').lower(); ok=[k for k in "
        + str(list(keywords))
        + " if k.lower() in src]; assert ok, 'missing: ' + str(ok); print('OK')"
    )


def check_workflow(*keywords: str) -> List[str]:
    """检查 .github/workflows 工作流内容是否包含关键字。"""
    return _python_c(
        "import pathlib; "
        "files=list(pathlib.Path('.github/workflows').glob('*.yml')); "
        "assert files, 'no workflows'; "
        "text=' '.join([f.read_text(encoding='utf-8').lower() for f in files]); "
        "ok=[k for k in "
        + str(list(keywords))
        + " if k.lower() in text]; assert ok, 'missing: ' + str(ok); print('OK')"
    )


def check_workflow_count(n: int) -> List[str]:
    """检查 .github/workflows 工作流数量。"""
    return _python_c(
        "import pathlib; "
        "files=list(pathlib.Path('.github/workflows').glob('*.yml')); "
        "assert len(files) >= " + str(n) + ", 'only ' + str(len(files)); print('OK')"
    )


# 14.1-17.8 每个子任务的验证命令
TASK_COMMANDS: Dict[str, List[str]] = {
    "14.1": pytest("tests/core/test_unified_config.py", "tests/core/test_unified_config_basic.py"),
    "14.2": pytest("tests/core/test_config_manager.py"),
    "14.3": check_source("core/config_manager.py", "watchdog", "FileSystemEventHandler"),
    "14.4": pytest("tests/core/test_environment_config.py"),
    "14.5": pytest("tests/core/test_security_config.py"),
    "14.6": check_source("core/config_manager.py", "audit", "Audit"),
    "14.7": check_source("core/config_manager.py", "rollback", "Rollback"),
    "14.8": check_file("docs/configuration/README.md"),
    "15.1": check_file(".env.example"),
    "15.2": check_source("core/config_manager.py", "dotenv", "load_dotenv"),
    "15.3": pytest("tests/core/test_environment_config.py"),
    "15.4": check_file("docs/environment/README.md"),
    "15.5": check_source("core/config_models.py", "Field(default", "default_factory"),
    "15.6": check_source("core/config_manager.py", "split", "_safe_bool", "CORS"),
    "15.7": pytest("tests/core/test_security_config.py"),
    "15.8": check_file("docs/environment/usage.md"),
    "16.1": check_file("requirements.txt"),
    "16.2": check_file("requirements.txt"),
    "16.3": check_file("requirements.txt"),
    "16.4": check_workflow("safety", "bandit", "security"),
    "16.5": check_file("pyproject.toml", "poetry.lock"),
    "16.6": check_file("docs/dependencies/README.md"),
    "16.7": check_file("docs/dependencies/README.md"),
    "16.8": pytest("tests/core/test_dependency_injection.py"),
    "17.1": check_workflow_count(5),
    "17.2": check_workflow("pytest", "test"),
    "17.3": check_workflow("black", "isort", "mypy", "flake8"),
    "17.4": check_workflow("bandit", "safety", "security"),
    "17.5": check_file("Dockerfile"),
    "17.6": check_workflow("env", "secrets", "environment"),
    "17.7": check_workflow("slack", "email", "notify"),
    "17.8": check_file("docs/ci-cd/README.md"),
}


def run(task_id: str) -> Dict[str, Any]:
    """执行指定任务验证命令。"""
    cmd = TASK_COMMANDS.get(task_id)
    if not cmd:
        return {"status": "skipped", "error": f"unknown task {task_id}"}

    result = subprocess_runner.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        shell=False,
    )

    return {
        "status": "ok" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 task_list.md 子任务")
    parser.add_argument("--task", required=True, help="任务编号，如 14.1")
    args = parser.parse_args()

    outcome = run(args.task)
    print(outcome["status"].upper())
    if outcome.get("stdout"):
        print(outcome["stdout"])
    if outcome.get("stderr"):
        print(outcome["stderr"], file=sys.stderr)

    return 0 if outcome["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
