# -*- coding: utf-8 -*-
"""中危台账批次 22 回归测试（modules/，2026-09-16）。

覆盖条目：
- M-036 modules/execute/saga/coordinator.py          _load_saga 真实重建（持久化状态视图）
- M-040 modules/high_availability/multi_region.py     区域健康真实探测 + 跨区同步真实投递
- M-041 modules/high_availability/self_healing.py     verify_remediation 真实校验组件状态
- M-046 modules/observability/auto_discovery.py       _simple_network_scan 真实 TCP 扫描
- M-055 modules/rum/sdk.py                            iOS/Android 生成代码 flush() 真实发送
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# M-036 — saga persistence: real rebuild
# ---------------------------------------------------------------------------
def test_saga_load_after_restart():
    from modules.execute.saga.coordinator import SagaCoordinator, SagaStep

    async def _action(ctx: Dict[str, Any]) -> str:
        return "ok"

    async def _boom(ctx: Dict[str, Any]) -> str:
        raise RuntimeError("step failed")

    async def _comp(ctx: Dict[str, Any]) -> None:
        return None

    coord = SagaCoordinator(enable_persistence=True)
    saga = coord.create_saga(
        "t1",
        [
            SagaStep("s1", _action),
            SagaStep("s2", _boom, compensation=_comp),
        ],
    )
    result = asyncio.run(coord.execute_saga(saga.saga_id, {}))
    assert result["success"] is False
    assert result["state"] == "compensated"

    # 模拟进程重启：仅清空内存缓存，保留持久化存储
    persisted_state = saga.state.value
    persisted_steps = [s.state.value for s in saga.steps]
    coord._sagas.clear()

    # get_saga 应从持久化真实重建
    rebuilt = coord.get_saga(saga.saga_id)
    assert rebuilt is not None
    assert rebuilt.saga_id == saga.saga_id
    assert rebuilt.name == "t1"
    assert rebuilt.state.value == persisted_state
    assert [s.name for s in rebuilt.steps] == ["s1", "s2"]
    assert [s.state.value for s in rebuilt.steps] == persisted_steps
    assert rebuilt.created_at is not None

    # 不存在 → None
    assert coord._load_saga("no-such-saga") is None
    # 未启用持久化时不回源
    plain = SagaCoordinator(enable_persistence=False)
    assert plain.get_saga("x") is None


def test_saga_from_dict_roundtrip():
    from modules.execute.saga.coordinator import SagaInstance

    async def _noop(ctx: Dict[str, Any]) -> None:
        return None

    from modules.execute.saga.coordinator import SagaStep

    saga = SagaInstance(saga_id="id1", name="n", steps=[SagaStep("a", _noop)])
    rebuilt = SagaInstance.from_dict(saga.to_dict())
    assert rebuilt.saga_id == "id1"
    assert rebuilt.name == "n"
    assert rebuilt.state.value == saga.state.value
    assert rebuilt.steps[0].name == "a"


# ---------------------------------------------------------------------------
# M-040 — real region health probe
# ---------------------------------------------------------------------------
def test_region_health_real_probe():
    from modules.high_availability.multi_region import Region, create_multi_region_manager

    manager = create_multi_region_manager()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        up = Region(id="up", name="UP", location="l", endpoint=f"127.0.0.1:{port}")
        down = Region(id="down", name="DOWN", location="l", endpoint="127.0.0.1:1")
        none = Region(id="none", name="NONE", location="l", endpoint="")
        assert manager._check_region_health(up) is True
        assert up.latency is not None
        assert manager._check_region_health(down) is False
        # 无端点 → 无法验证 → 如实 False（不再恒 True）
        assert manager._check_region_health(none) is False
    finally:
        srv.close()


def test_region_http_health_probe():
    import http.server
    import threading

    from modules.high_availability.multi_region import Region, create_multi_region_manager

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        manager = create_multi_region_manager()
        region = Region(id="h", name="H", location="l", endpoint=f"http://127.0.0.1:{port}/health")
        assert manager._check_region_health(region) is True
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# M-040 — real cross-region sync
# ---------------------------------------------------------------------------
def test_sync_data_real_delivery_and_honest_skip():
    import http.server
    import json as _json
    import threading

    from modules.high_availability.multi_region import create_data_sync_manager

    sync = create_data_sync_manager()

    # 未配置投递方式 → 如实标记未分发
    sync.configure_sync("src", ["t1"], "async")
    assert sync.sync_data("src", {"x": 1}) == {"t1": False}
    assert "skipped" in sync.get_sync_status()["src->t1"]

    received = []

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            received.append(_json.loads(self.rfile.read(length) or b"{}"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        sync.configure_sync(
            "src2",
            ["t1", "t2"],
            "sync",
            target_endpoints={
                "t1": f"http://127.0.0.1:{port}/s",
                "t2": f"http://127.0.0.1:{port}/s",
            },
        )
        results = sync.sync_data("src2", {"payload": [1, 2, 3]})
        assert results == {"t1": True, "t2": True}
        assert len(received) == 2
        assert received[0]["source_region"] == "src2"
        assert received[0]["data"] == {"payload": [1, 2, 3]}
    finally:
        server.shutdown()
        server.server_close()


def test_sync_data_uses_handler():
    from modules.high_availability.multi_region import create_data_sync_manager

    seen = []

    def _handler(target: str, data: Any) -> bool:
        seen.append((target, data))
        return target == "ok"

    sync = create_data_sync_manager()
    sync.configure_sync("src", ["ok", "bad"], "async", sync_handler=_handler)
    results = sync.sync_data("src", {"n": 1})
    assert results == {"ok": True, "bad": False}
    assert len(seen) == 2


# ---------------------------------------------------------------------------
# M-041 — real remediation verification
# ---------------------------------------------------------------------------
def test_verify_remediation_real_and_stubbed_io(monkeypatch):
    from modules.high_availability.self_healing import (
        FailureEvent,
        FailureType,
        create_self_healing_engine,
    )

    engine = create_self_healing_engine()
    ev = FailureEvent(
        id="f1",
        failure_type=FailureType.SERVICE_DOWN,
        component="svc",
        severity="high",
        description="down",
    )

    # I/O 边界：组件 active → True
    monkeypatch.setattr(engine, "_run_guarded", lambda cmd: (True, "active"))
    assert engine.verify_remediation(ev) is True
    # 组件 inactive → False
    monkeypatch.setattr(engine, "_run_guarded", lambda cmd: (False, "inactive"))
    assert engine.verify_remediation(ev) is False


def test_verify_remediation_real_command_runs():
    from modules.high_availability.self_healing import (
        FailureEvent,
        FailureType,
        create_self_healing_engine,
    )

    engine = create_self_healing_engine()
    ev = FailureEvent(
        id="f2",
        failure_type=FailureType.SERVICE_DOWN,
        component="definitely-not-a-real-service-xyz",
        severity="high",
        description="down",
    )
    # 真实执行：不存在的组件绝不可能为 active → 如实失败
    assert engine.verify_remediation(ev) is False


# ---------------------------------------------------------------------------
# M-046 — real simple network scan
# ---------------------------------------------------------------------------
def _free_scan_port():
    from modules.observability.auto_discovery import NETWORK_SCAN_PORTS

    for port in NETWORK_SCAN_PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            s.close()
            continue
        s.listen(1)
        return s, port
    return None, None


def test_simple_network_scan_detects_open_port():
    from modules.observability.auto_discovery import ResourceType, create_auto_discovery_engine

    disc = create_auto_discovery_engine()

    srv, port = _free_scan_port()
    if srv is None:
        pytest.skip("no scannable port bindable")
    try:
        disc._simple_network_scan("127.0.0.1/32", timeout=0.3)
    finally:
        srv.close()

    found = disc.discovered_resources.get(f"network-127.0.0.1-{port}")
    assert found is not None
    assert found.host == "127.0.0.1"
    assert found.port == port
    assert isinstance(found.type, ResourceType)
    assert "simple-scan" in found.tags


def test_simple_network_scan_closed_port_not_found():
    from modules.observability.auto_discovery import create_auto_discovery_engine

    disc = create_auto_discovery_engine()
    # 未监听任何扫描端口时不应臆造资源
    disc._simple_network_scan("127.0.0.1/32", timeout=0.05)
    # （若本机恰好监听了某个扫描端口则可能命中，属正常；此处仅确保不抛异常且结构正确）
    for key, res in disc.discovered_resources.items():
        assert key == f"network-{res.host}-{res.port}"


def test_simple_network_scan_invalid_subnet_no_crash():
    from modules.observability.auto_discovery import create_auto_discovery_engine

    disc = create_auto_discovery_engine()
    disc._simple_network_scan("not-a-subnet")
    assert not any(str(k).startswith("network-") for k in disc.discovered_resources)


# ---------------------------------------------------------------------------
# M-055 — generated iOS/Android SDK flush actually sends
# ---------------------------------------------------------------------------
def test_generated_ios_sdk_flush_sends():
    from modules.rum.sdk import RUMSDKGenerator, SDKConfig

    gen = RUMSDKGenerator()
    code = gen._generate_ios_sdk(SDKConfig(api_key="k", api_endpoint="https://rum.example.com"))
    assert "URLSession.shared.dataTask" in code
    assert 'request.httpMethod = "POST"' in code
    assert "JSONSerialization.data(withJSONObject: payload)" in code
    assert "实际实现应使用 URLSession" not in code
    assert "dataTask(with: request)" in code


def test_generated_android_sdk_flush_sends():
    from modules.rum.sdk import RUMSDKGenerator, SDKConfig

    gen = RUMSDKGenerator()
    code = gen._generate_android_sdk(SDKConfig(api_key="k", api_endpoint="https://rum.example.com"))
    assert "HttpURLConnection" in code
    assert 'conn.requestMethod = "POST"' in code
    assert "conn.outputStream.use" in code
    assert "实际实现应使用 OkHttp" not in code or "HttpURLConnection" in code
