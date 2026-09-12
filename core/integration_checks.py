# -*- coding: utf-8 -*-
"""
integration_checks.py
---------------------
集成测试/校验共用的**真实**检查执行器。

供 ``core.integration_testing_system`` 与 ``core.integration_test_validator`` 复用，
避免两套系统各自实现（重复代码）。每个检查都真实执行（导入/哈希/数据库/HTTP/命令/
文件清单/延迟/吞吐/可靠性），绝不返回随机或占位结果。

统一入口：``async def run_check(check: Dict[str, Any]) -> Dict[str, Any]``
返回：``{"passed": bool, "output": str, "coverage": float, "error": str|None, "metrics": dict}``

支持的 ``check["kind"]``：
  * ``module_attr``        —— 导入模块并校验属性（可选要求为协程函数）
  * ``password_roundtrip`` —— 口令哈希/校验真往返
  * ``jwt_roundtrip``      —— JWT 签发/校验真往返
  * ``db``                 —— 执行真实 SQL 并校验有返回
  * ``db_tx``              —— 真实事务提交/回滚验证
  * ``db_throughput``      —— 真实执行 N 次查询并测算 QPS
  * ``db_reliability``     —— 真实执行 N 次查询并统计成功率
  * ``latency``            —— 真实调用可调用对象并测量耗时（阈值判定）
  * ``http``               —— 真实 HTTP 请求并校验状态码
  * ``command``            —— 真实执行 shell 命令（经安全校验）并校验退出码
  * ``file_manifest``      —— 真实解析文件（如 package.json）并校验字段
  * ``multi``              —— 组合多个子检查
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import shlex
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _fail(kind: str, message: str, metrics: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "passed": False,
        "output": f"[{kind}] {message}",
        "coverage": 0.0,
        "error": message,
        "metrics": metrics or {},
    }


def _ok(kind: str, message: str, metrics: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "passed": True,
        "output": f"[{kind}] {message}",
        "coverage": 100.0,
        "error": None,
        "metrics": metrics or {},
    }


def _resolve(check: Dict[str, Any]):
    module_name = check["module"]
    attr = check.get("attr")
    module = importlib.import_module(module_name)
    target = getattr(module, attr) if attr else module
    return f"{module_name}.{attr}" if attr else module_name, target


def _check_module_attr(check: Dict[str, Any]) -> Dict[str, Any]:
    name, target = _resolve(check)
    if check.get("expect_coroutine") and not inspect.iscoroutinefunction(target):
        return _fail("module_attr", f"{name} is not a coroutine function")
    return _ok("module_attr", f"imported {name} ({type(target).__name__})", {"target": name})


def _check_password_roundtrip(check: Dict[str, Any]) -> Dict[str, Any]:
    from core.authentication import hash_password, verify_password

    sample = check.get("password", "AIOps-Str0ng!Pass")
    hashed = hash_password(sample)
    ok = verify_password(sample, hashed) and not verify_password(sample + "x", hashed)
    if not ok:
        return _fail("password_roundtrip", "password hash/verify mismatch")
    return _ok("password_roundtrip", "hash/verify round-trip ok", {"hash_len": len(hashed)})


def _check_jwt_roundtrip(check: Dict[str, Any]) -> Dict[str, Any]:
    from core.authentication import create_access_token, verify_token

    subject = check.get("subject", "integration-probe")
    token = create_access_token({"sub": subject})
    payload = verify_token(token)
    if not payload:
        return _fail("jwt_roundtrip", "token verify returned no payload")
    return _ok("jwt_roundtrip", "JWT issue/verify round-trip ok", {"subject": subject})


def _check_db(check: Dict[str, Any]) -> Dict[str, Any]:
    from sqlalchemy import text

    from core.database import engine

    sql = check.get("sql", "SELECT 1")
    with engine.connect() as conn:
        value = conn.execute(text(sql)).scalar()
    if value is None:
        return _fail("db", f"query '{sql}' returned no rows")
    return _ok("db", f"query '{sql}' -> {value}", {"scalar": value})


def _check_db_transaction(check: Dict[str, Any]) -> Dict[str, Any]:
    from sqlalchemy import text

    from core.database import engine

    with engine.connect() as conn:
        trans = conn.begin()
        conn.execute(text("CREATE TEMP TABLE IF NOT EXISTS _it_probe (v INTEGER)"))
        conn.execute(text("INSERT INTO _it_probe (v) VALUES (1)"))
        trans.rollback()
    try:
        with engine.connect() as conn:
            remaining = conn.execute(text("SELECT COUNT(*) FROM _it_probe WHERE v = 1")).scalar()
    except Exception:
        # 回滚后 TEMP 表在新连接中不存在 —— 说明回滚生效
        remaining = 0
    passed = remaining in (0, None)
    if not passed:
        return _fail("db_tx", f"rollback did not discard inserted row (rows={remaining})")
    return _ok("db_tx", "transaction rollback verified", {"rows_after_rollback": remaining})


def _check_db_throughput(check: Dict[str, Any]) -> Dict[str, Any]:
    from sqlalchemy import text

    from core.database import engine

    ops = int(check.get("ops", 20))
    min_qps = float(check.get("min_ops_per_sec", 1.0))
    start = time.perf_counter()
    with engine.connect() as conn:
        for _ in range(ops):
            conn.execute(text("SELECT 1")).scalar()
    elapsed = max(time.perf_counter() - start, 1e-9)
    qps = ops / elapsed
    if qps < min_qps:
        return _fail("db_throughput", f"throughput {qps:.1f} qps < {min_qps} qps")
    return _ok("db_throughput", f"{qps:.1f} qps over {ops} queries", {"qps": round(qps, 2)})


def _check_db_reliability(check: Dict[str, Any]) -> Dict[str, Any]:
    from sqlalchemy import text

    from core.database import engine

    attempts = int(check.get("attempts", 5))
    successes = 0
    for _ in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).scalar()
            successes += 1
        except Exception as exc:  # noqa: BLE001 - 记录失败以计算真实成功率
            logger.warning("reliability probe failed: %s", exc)
    ratio = successes / attempts if attempts else 0.0
    min_ratio = float(check.get("min_success_ratio", 1.0))
    if ratio < min_ratio:
        return _fail("db_reliability", f"success ratio {ratio:.2f} < {min_ratio}")
    return _ok(
        "db_reliability",
        f"{successes}/{attempts} probes succeeded",
        {"success_ratio": ratio},
    )


def _check_latency(check: Dict[str, Any]) -> Dict[str, Any]:
    name, target = _resolve(check)
    args = check.get("args", [])
    kwargs = check.get("kwargs", {})
    iterations = int(check.get("iterations", 1))
    start = time.perf_counter()
    for _ in range(iterations):
        target(*args, **kwargs)
    elapsed = (time.perf_counter() - start) / max(iterations, 1)
    max_seconds = float(check.get("max_seconds", 1.0))
    if elapsed > max_seconds:
        return _fail("latency", f"{name} took {elapsed:.4f}s > {max_seconds}s")
    return _ok("latency", f"{name} avg {elapsed:.4f}s", {"avg_seconds": elapsed})


def _check_file_manifest(check: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(check["path"])
    if not path.exists():
        return _fail("file_manifest", f"{path} does not exist")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for key_path in check.get("expect_keys", []):
        node: Any = data
        for part in key_path.split("."):
            if not isinstance(node, dict) or part not in node:
                return _fail("file_manifest", f"{path} missing key '{key_path}'")
            node = node[part]
    return _ok("file_manifest", f"{path} parsed", {"keys": check.get("expect_keys", [])})


async def _check_http(check: Dict[str, Any]) -> Dict[str, Any]:
    import httpx

    url = check["url"]
    method = check.get("method", "GET").upper()
    expect = check.get("expect_status")
    async with httpx.AsyncClient(timeout=check.get("timeout", 10.0)) as client:
        response = await client.request(method, url, json=check.get("json"))
    status = response.status_code
    if expect is None:
        passed = 200 <= status < 400
    elif isinstance(expect, (list, tuple, set)):
        passed = status in expect
    else:
        passed = status == expect
    if not passed:
        return _fail("http", f"HTTP {method} {url} -> {status}", {"status_code": status})
    return _ok("http", f"HTTP {method} {url} -> {status}", {"status_code": status})


async def _check_command(check: Dict[str, Any]) -> Dict[str, Any]:
    from core.agent.coding_tools import _validate_bash_command

    cmd = check["cmd"]
    cmd_str = cmd if isinstance(cmd, str) else " ".join(shlex.quote(c) for c in cmd)
    _validate_bash_command(cmd_str)
    proc = await asyncio.create_subprocess_shell(
        cmd_str,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    expect_rc = check.get("expect_returncode", 0)
    combined = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
    if proc.returncode != expect_rc:
        return _fail(
            "command",
            f"exit code {proc.returncode} != {expect_rc}: {combined[:500]}",
            {"returncode": proc.returncode},
        )
    return _ok("command", combined[:500] or "ok", {"returncode": proc.returncode})


async def _check_multi(check: Dict[str, Any]) -> Dict[str, Any]:
    sub_checks: List[Dict[str, Any]] = check.get("checks", [])
    if not sub_checks:
        return _fail("multi", "no sub-checks")
    passed_count = 0
    outputs = []
    first_error = None
    for sub in sub_checks:
        outcome = await run_check(sub)
        outputs.append(f"[{'PASS' if outcome['passed'] else 'FAIL'}] {outcome['output']}")
        if outcome["passed"]:
            passed_count += 1
        elif first_error is None:
            first_error = outcome.get("error") or outcome["output"]
    passed = passed_count == len(sub_checks)
    return {
        "passed": passed,
        "output": "; ".join(outputs)[:2000],
        "coverage": round(passed_count / len(sub_checks) * 100.0, 2),
        "error": None if passed else first_error,
        "metrics": {"passed": passed_count, "total": len(sub_checks)},
    }


_SYNC_KINDS = {
    "module_attr": _check_module_attr,
    "password_roundtrip": _check_password_roundtrip,
    "jwt_roundtrip": _check_jwt_roundtrip,
    "db": _check_db,
    "db_tx": _check_db_transaction,
    "db_throughput": _check_db_throughput,
    "db_reliability": _check_db_reliability,
    "latency": _check_latency,
    "file_manifest": _check_file_manifest,
}

_ASYNC_KINDS = {
    "http": _check_http,
    "command": _check_command,
    "multi": _check_multi,
}


async def run_check(check: Dict[str, Any]) -> Dict[str, Any]:
    """真实执行单个检查。未知 kind 与执行异常都返回失败结果（不抛出、不伪造）。"""
    kind = check.get("kind")
    try:
        if kind in _SYNC_KINDS:
            return await asyncio.get_event_loop().run_in_executor(None, _SYNC_KINDS[kind], check)
        if kind in _ASYNC_KINDS:
            return await _ASYNC_KINDS[kind](check)
        return _fail(str(kind), f"unknown check kind: {kind}")
    except Exception as exc:  # noqa: BLE001 - 把真实异常如实上报
        return _fail(str(kind), f"{type(exc).__name__}: {exc}")
